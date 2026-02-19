"""NVIDIA RAG HTTP API client."""

import json
import logging
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


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
        """Create a collection using POST /v1/collections.
        
        Args:
            collection_name: Name of the collection
            embedding_dimension: Dimension of embeddings
            metadata_schema: Optional metadata schema definition
            
        Returns:
            Response JSON from API
            
        Raises:
            IngestionError: If collection creation fails
        """
        url = f"{self.base_url}/v1/collections"
        
        # Default metadata schema with ACL support
        if metadata_schema is None:
            metadata_schema = [
                {
                    "name": "allowed_sids",
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "SIDs with access to this document",
                    "support_dynamic_filtering": True,
                }
            ]
        
        payload = {
            "collection_name": collection_name,
            "embedding_dimension": embedding_dimension,
            "metadata_schema": metadata_schema,
        }
        
        try:
            self.logger.debug(f"Creating collection: {collection_name}")
            resp = requests.post(url, json=payload, timeout=60, proxies=self.proxies)
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.json()
                except:
                    error_detail = resp.text
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
    
    def delete_collection(self, collection_name: str) -> dict:
        """Delete a collection using DELETE /v1/collections.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            Response JSON from API
            
        Raises:
            IngestionError: If deletion fails
        """
        url = f"{self.base_url}/v1/collections"
        
        try:
            self.logger.debug(f"Deleting collection: {collection_name}")
            resp = requests.delete(
                url,
                json={"collection_names": [collection_name]},
                timeout=60,
                proxies=self.proxies
            )
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.json()
                except:
                    error_detail = resp.text
                self.logger.error(
                    f"Delete collection failed [{resp.status_code}]: {error_detail}"
                )
                raise IngestionError(
                    f"Delete collection failed [{resp.status_code}]: {error_detail}"
                )
            
            self.logger.info(f"Collection deleted successfully: {collection_name}")
            return resp.json() if resp.text else {"status": "ok"}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to delete collection: {e}")
            raise IngestionError(f"Failed to delete collection: {e}") from e
    
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
            Response JSON from API
            
        Raises:
            IngestionError: If upload fails
        """
        url = f"{self.base_url}/v1/documents"
        
        opened_files = []
        files_form = []
        
        try:
            # Build multipart form data with files
            for file_path in files:
                content_type = self._guess_content_type(file_path)
                f = open(file_path, "rb")
                opened_files.append(f)
                files_form.append(
                    ("files", (file_path.name, f, content_type))
                )
            
            # Add JSON payload as multipart field named "data"
            files_form.append(
                (
                    "data",
                    (
                        "payload.json",
                        json.dumps(payload).encode("utf-8"),
                        "application/json",
                    ),
                )
            )
            
            self.logger.debug(f"Uploading {len(files)} documents")
            resp = requests.post(url, files=files_form, timeout=timeout, proxies=self.proxies)
            
            if resp.status_code >= 400:
                try:
                    error_detail = resp.json()
                except:
                    error_detail = resp.text
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
            # Close all opened files
            for f in opened_files:
                f.close()
    
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
            ".html": "text/html",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        return mapping.get(ext, "application/octet-stream")
