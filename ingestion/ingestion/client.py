"""NVIDIA RAG HTTP API client."""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds


class IngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


class IngestionClient:
    """HTTP client for NVIDIA RAG ingestion API."""
    
    def __init__(
        self,
        base_url: str,
        logger: logging.Logger | None = None,
        poll_timeout: int = 3600,
        proxies: dict[str, str] | None = None,
    ):
        """Initialize ingestion client.
        
        Args:
            base_url: Base URL for ingestor API (e.g., http://localhost:8082)
            logger: Optional logger instance
            poll_timeout: Timeout for polling operations
            proxies: Optional proxy configuration dict
        """
        self.base_url = base_url.rstrip("/")
        self.logger = logger or logging.getLogger(__name__)
        self.poll_timeout = poll_timeout
        self.proxies = proxies
    
    def create_collection(
        self,
        collection_name: str,
        embedding_dimension: int = 2048,
        metadata_schema: list[dict] | None = None,
    ) -> dict:
        """Create a collection using POST /v1/collection (singular).
        
        Args:
            collection_name: Name of the collection
            embedding_dimension: Dimension of embeddings
            metadata_schema: Optional metadata schema definition (default: empty list)
            
        Returns:
            Response JSON from API
            
        Raises:
            IngestionError: If collection creation fails
        """
        url = f"{self.base_url}/v1/collection"
        
        payload = {
            "collection_name": collection_name,
            "embedding_dimension": embedding_dimension,
            "metadata_schema": metadata_schema if metadata_schema is not None else [],
        }
        
        try:
            self.logger.debug(f"Creating collection: {collection_name}")
            resp = requests.post(url, json=payload, timeout=60, proxies=self.proxies)
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.text
                except:
                    error_detail = "<no response text>"
                self.logger.error(
                    f"Create collection failed [{resp.status_code}]: {error_detail}"
                )
                raise IngestionError(
                    f"Create collection failed [{resp.status_code}]: {error_detail}"
                )
            
            self.logger.info(f"Collection created successfully: {collection_name}")
            return resp.json() if resp.text else {"status": "ok"}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create collection: {e}")
            raise IngestionError(f"Failed to create collection: {e}") from e
    
    def delete_collections(self, collection_names: list[str]) -> dict:
        """Delete collections using DELETE /v1/collections with JSON body [names].
        
        Args:
            collection_names: List of collection names to delete
            
        Returns:
            Response JSON from API
            
        Raises:
            IngestionError: If deletion fails
        """
        url = f"{self.base_url}/v1/collections"
        
        try:
            self.logger.debug(f"Deleting collections: {collection_names}")
            resp = requests.delete(
                url,
                json=collection_names,
                timeout=60,
                proxies=self.proxies
            )
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.text
                except:
                    error_detail = "<no response text>"
                self.logger.error(
                    f"Delete collections failed [{resp.status_code}]: {error_detail}"
                )
                raise IngestionError(
                    f"Delete collections failed [{resp.status_code}]: {error_detail}"
                )
            
            self.logger.info(f"Collections deleted successfully: {collection_names}")
            return resp.json() if resp.text else {"status": "ok"}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to delete collections: {e}")
            raise IngestionError(f"Failed to delete collections: {e}") from e
    
    def list_documents(self, collection_name: str) -> list[str]:
        """Return list of existing document names (filenames) for the collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List of document filenames
            
        Raises:
            IngestionError: If listing fails
        """
        url = f"{self.base_url}/v1/documents"
        params = {"collection_name": collection_name}
        
        try:
            resp = requests.get(url, params=params, timeout=60, proxies=self.proxies)
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.text
                except:
                    error_detail = "<no response text>"
                self.logger.error(
                    f"List documents failed [{resp.status_code}]: {error_detail}"
                )
                raise IngestionError(
                    f"List documents failed [{resp.status_code}]: {error_detail}"
                )
            
            data = resp.json() or {}
            docs = data.get("documents", [])
            names = []
            for d in docs:
                meta = d.get("metadata") or {}
                filename = meta.get("filename") or d.get("document_name")
                if filename:
                    names.append(filename)
            
            return names
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to list documents: {e}")
            raise IngestionError(f"Failed to list documents: {e}") from e
    
    def upload_documents(
        self,
        files: list[Path],
        payload: dict,
        timeout: int = 300,
    ) -> dict:
        """Upload documents with ACL metadata.
        
        Args:
            files: List of file paths to upload
            payload: Document payload with collection and processing options
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON from API (contains task_id for async processing)
            
        Raises:
            IngestionError: If upload fails
        """
        url = f"{self.base_url}/v1/documents"
        
        files_form = []
        opened_files = []
        
        try:
            for file_path in files:
                content_type = self._guess_content_type(file_path)
                f = open(file_path, "rb")
                opened_files.append(f)
                files_form.append(
                    ("documents", (file_path.name, f, content_type))
                )
            
            files_form.append(
                (
                    "data",
                    (None, json.dumps(payload), "application/json"),
                )
            )
            
            self.logger.debug(f"Uploading {len(files)} documents")
            resp = requests.post(url, files=files_form, timeout=timeout, proxies=self.proxies)
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.text
                except:
                    error_detail = "<no response text>"
                self.logger.error(
                    f"Upload failed [{resp.status_code}]: {error_detail}"
                )
                raise IngestionError(
                    f"Upload failed [{resp.status_code}]: {error_detail}"
                )
            
            self.logger.debug(f"Upload successful: {len(files)} files")
            return resp.json() if resp.text else {"status": "ok"}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Upload request failed: {e}")
            raise IngestionError(f"Upload request failed: {e}") from e
            
        finally:
            for f in opened_files:
                try:
                    f.close()
                except:
                    pass
    
    def poll_task_status(self, task_id: str) -> dict:
        """Poll ingestion task status until completion.
        
        Args:
            task_id: Task ID returned from upload
            
        Returns:
            Final status JSON
            
        Raises:
            IngestionError: If task fails or times out
        """
        url = f"{self.base_url}/v1/status"
        params = {"task_id": task_id}
        start_time = time.time()
        
        self.logger.info(f"Polling task status for task_id: {task_id}")
        
        spinner_frames = ["|", "/", "-", "\\"]
        spinner_idx = 0
        spinner_enabled = sys.stdout.isatty()
        last_spinner_len = 0
        
        def draw_spinner():
            nonlocal spinner_idx, last_spinner_len
            if not spinner_enabled:
                return
            frame = spinner_frames[spinner_idx]
            spinner_idx = (spinner_idx + 1) % len(spinner_frames)
            msg = f"  Polling task {task_id} {frame}"
            last_spinner_len = len(msg)
            try:
                sys.stdout.write("\r" + msg)
                sys.stdout.flush()
            except:
                pass
        
        def clear_spinner():
            nonlocal last_spinner_len
            if not spinner_enabled or last_spinner_len == 0:
                return
            try:
                sys.stdout.write("\r" + (" " * last_spinner_len) + "\r")
                sys.stdout.flush()
            except:
                pass
        
        def sleep_with_spinner(seconds: float):
            if not spinner_enabled:
                time.sleep(seconds)
                return
            step = 0.2
            remaining = float(seconds)
            while remaining > 0:
                draw_spinner()
                t = step if remaining > step else remaining
                time.sleep(t)
                remaining -= t
        
        retries = 1
        while True:
            try:
                draw_spinner()
                response = requests.get(url, params=params, timeout=60, proxies=self.proxies)
            except Exception as e:
                clear_spinner()
                self.logger.warning(
                    f"Error polling task status (retry #{retries}): {e}"
                )
                if retries > 10:
                    raise IngestionError(f"Status polling retries exceeded: {e}") from e
                retries += 1
                sleep_with_spinner(POLL_INTERVAL)
                continue
            
            elapsed = time.time() - start_time
            try:
                status_json = response.json()
            except Exception:
                status_json = {"state": "UNKNOWN", "raw": response.text or ""}
            
            state = (status_json or {}).get("state")
            
            if int(elapsed) % 600 < POLL_INTERVAL:
                clear_spinner()
                self.logger.info(f"Task status after {elapsed:.0f}s: {state}")
            
            if state == "FINISHED":
                clear_spinner()
                self.logger.info(f"Task {task_id} finished successfully")
                result = status_json.get("result") if isinstance(status_json, dict) else {}
                failed_docs = result.get("failed_documents", []) if isinstance(result, dict) else []
                if failed_docs:
                    self.logger.error(
                        f"Task failed for {len(failed_docs)} documents: {failed_docs}"
                    )
                return status_json
            
            if state == "FAILED":
                clear_spinner()
                self.logger.error(f"Task {task_id} failed: {status_json}")
                raise IngestionError(f"Task failed: {status_json}")
            
            if state == "UNKNOWN":
                clear_spinner()
                self.logger.error(
                    f"Task {task_id} unknown (server may have restarted): {status_json}"
                )
                raise IngestionError(f"Task unknown: {status_json}")
            
            if time.time() - start_time > self.poll_timeout:
                clear_spinner()
                self.logger.error(f"Task {task_id} timed out after {self.poll_timeout}s")
                raise IngestionError(f"Status polling timed out after {self.poll_timeout}s")
            
            sleep_with_spinner(POLL_INTERVAL)
    
    def _guess_content_type(self, file_path: Path) -> str:
        """Guess content type based on file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string
        """
        ext = file_path.suffix.lower()
        mapping = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".html": "text/html",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        return mapping.get(ext, "application/octet-stream")
