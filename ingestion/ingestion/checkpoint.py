"""Checkpoint manager for resumable ingestion."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint files for resumable ingestion."""
    
    def __init__(self, checkpoint_file: Path):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Path to checkpoint file
        """
        self.checkpoint_file = checkpoint_file
    
    def load(self) -> dict[str, Any] | None:
        """Load checkpoint from file.
        
        Returns:
            Checkpoint data or None if file doesn't exist
        """
        try:
            if not self.checkpoint_file.exists():
                logger.debug(f"Checkpoint file not found: {self.checkpoint_file}")
                return None
            
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
            
            logger.info(f"Loaded checkpoint from {self.checkpoint_file}")
            logger.debug(f"Checkpoint data: offset={data.get('offset', 0)}, "
                        f"batch_num={data.get('batch_num', 0)}, "
                        f"total_processed={data.get('total_processed', 0)}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid checkpoint file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def save(
        self,
        offset: int,
        batch_num: int,
        total_processed: int,
        total_failed: int,
    ) -> None:
        """Save checkpoint to file.
        
        Args:
            offset: Current database offset
            batch_num: Current batch number
            total_processed: Total files processed
            total_failed: Total files failed
        """
        import datetime
        
        data = {
            "offset": offset,
            "batch_num": batch_num,
            "total_processed": total_processed,
            "total_failed": total_failed,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        
        try:
            # Ensure parent directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.checkpoint_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Checkpoint saved: offset={offset}, batch={batch_num}, "
                        f"processed={total_processed}, failed={total_failed}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def delete(self) -> None:
        """Delete checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info(f"Checkpoint file deleted: {self.checkpoint_file}")
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint file: {e}")
