"""ACL extraction with timeout and fallback handling."""

import asyncio
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class ACLResult:
    """Result of ACL extraction attempt."""
    raw_acl: str | None = None
    captured: bool = False
    method: str = "unknown"
    error: str | None = None


async def extract_acl(
    file_path: Path,
    timeout_seconds: float = 300.0,
) -> ACLResult:
    """Extract ACL from file with timeout and fallback.
    
    Tries getfacl first (for CIFS/NTFS), falls back to stat-based info.
    Never raises - always returns an ACLResult.
    
    Args:
        file_path: Path to file
        timeout_seconds: Timeout for ACL extraction
        
    Returns:
        ACLResult with extracted ACL or error info
    """
    # Try getfacl first (best for CIFS/NTFS mounts)
    result = await _try_getfacl(file_path, timeout_seconds)
    if result.captured:
        return result
    
    # Fall back to stat-based info
    return await _try_stat_acl(file_path, timeout_seconds)


async def _try_getfacl(
    file_path: Path,
    timeout_seconds: float,
) -> ACLResult:
    """Try to get ACL using getfacl command."""
    system = platform.system()
    
    # getfacl is primarily available on Linux
    if system != "Linux":
        return ACLResult(
            captured=False,
            method="getfacl",
            error=f"getfacl not available on {system}",
        )
    
    try:
        # Run getfacl with timeout
        proc = await asyncio.create_subprocess_exec(
            "getfacl",
            "-c",  # Commentary mode (more compact)
            str(file_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning(
                "acl_extraction_timeout",
                path=str(file_path),
                method="getfacl",
                timeout_seconds=timeout_seconds,
            )
            return ACLResult(
                captured=False,
                method="getfacl",
                error=f"Timeout after {timeout_seconds}s",
            )
        
        if proc.returncode == 0:
            acl_text = stdout.decode("utf-8", errors="replace").strip()
            return ACLResult(
                raw_acl=acl_text,
                captured=True,
                method="getfacl",
            )
        else:
            error_text = stderr.decode("utf-8", errors="replace").strip()
            return ACLResult(
                captured=False,
                method="getfacl",
                error=error_text or f"Exit code {proc.returncode}",
            )
            
    except FileNotFoundError:
        # getfacl not installed
        return ACLResult(
            captured=False,
            method="getfacl",
            error="getfacl command not found",
        )
    except Exception as e:
        logger.warning(
            "acl_extraction_error",
            path=str(file_path),
            method="getfacl",
            error=str(e),
        )
        return ACLResult(
            captured=False,
            method="getfacl",
            error=str(e),
        )


async def _try_stat_acl(
    file_path: Path,
    timeout_seconds: float,
) -> ACLResult:
    """Fallback: Get basic ACL info from stat."""
    try:
        # Use asyncio to run in thread pool with timeout
        loop = asyncio.get_event_loop()
        
        def _get_stat_info() -> dict[str, Any]:
            """Get stat info in thread."""
            try:
                stat_info = os.stat(file_path)
                return {
                    "mode": oct(stat_info.st_mode),
                    "uid": stat_info.st_uid,
                    "gid": stat_info.st_gid,
                    "size": stat_info.st_size,
                    "mtime": stat_info.st_mtime,
                    "atime": stat_info.st_atime,
                    "ctime": stat_info.st_ctime,
                }
            except (OSError, IOError) as e:
                return {"error": str(e)}
        
        # Run with timeout using asyncio.wait_for
        try:
            stat_info = await asyncio.wait_for(
                loop.run_in_executor(None, _get_stat_info),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "stat_timeout",
                path=str(file_path),
                timeout_seconds=timeout_seconds,
            )
            return ACLResult(
                captured=False,
                method="stat",
                error=f"Stat timeout after {timeout_seconds}s",
            )
        
        if "error" in stat_info:
            return ACLResult(
                captured=False,
                method="stat",
                error=stat_info["error"],
            )
        
        # Format as JSON for storage
        acl_text = json.dumps(stat_info, indent=2)
        
        return ACLResult(
            raw_acl=acl_text,
            captured=True,
            method="stat",
        )
        
    except Exception as e:
        logger.warning(
            "stat_acl_error",
            path=str(file_path),
            error=str(e),
        )
        return ACLResult(
            captured=False,
            method="stat",
            error=str(e),
        )