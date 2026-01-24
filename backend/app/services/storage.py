import os
import logging

class StorageService:
    def __init__(self):
        # Create uploads directory if it doesn't exist (for local fallback)
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Azure Blob client (preferred)
        self.blob_service_client = None
        self.container_name = None
        self._init_azure()
        
        # S3 client (fallback, deprecated)
        self.s3_client = None
        if not self.blob_service_client:
            self._init_s3()
    
    def _init_azure(self):
        """Initialize Azure Blob Storage client."""
        try:
            from azure.storage.blob import BlobServiceClient
            from app.core.config import settings
            
            if settings.AZURE_STORAGE_CONNECTION_STRING:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_STORAGE_CONNECTION_STRING
                )
                self.container_name = settings.AZURE_STORAGE_CONTAINER
                
                # Ensure container exists
                try:
                    container_client = self.blob_service_client.get_container_client(self.container_name)
                    if not container_client.exists():
                        container_client.create_container(public_access="blob")
                        logging.info(f"Created Azure blob container: {self.container_name}")
                except Exception as e:
                    logging.warning(f"Could not verify/create container: {e}")
                
                logging.info("Azure Blob Storage configured successfully")
        except ImportError:
            logging.warning("azure-storage-blob not installed")
        except Exception as e:
            logging.warning(f"Azure Blob Storage not configured: {e}")
    
    def _init_s3(self):
        """Initialize S3 client (deprecated fallback)."""
        try:
            import boto3
            from app.core.config import settings
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                self.bucket_name = settings.S3_BUCKET
                logging.info("S3 configured as fallback storage")
        except Exception as e:
            logging.warning(f"S3 not configured: {e}")

    async def upload_file(self, file_content: bytes, file_name: str, content_type: str) -> str:
        """Uploads a file to Azure Blob, S3, or saves locally."""
        
        # Try Azure Blob Storage first (preferred)
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=file_name
                )
                blob_client.upload_blob(
                    file_content,
                    content_type=content_type,
                    overwrite=True
                )
                
                blob_url = blob_client.url
                logging.info(f"File uploaded to Azure Blob: {blob_url}")
                return blob_url
            except Exception as e:
                logging.error(f"Azure Blob upload error: {e}")
                # Fall through to S3 or local storage
        
        # Try S3 (deprecated fallback)
        if self.s3_client:
            try:
                from app.core.config import settings
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file_content,
                    ContentType=content_type,
                    ACL='public-read'
                )
                s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
                logging.info(f"File uploaded to S3: {s3_url}")
                return s3_url
            except Exception as e:
                logging.error(f"S3 Upload error: {e}")
                # Fall through to local storage
        
        # Local storage fallback
        file_path = os.path.join(self.upload_dir, file_name)
        
        # Ensure parent directory exists (critical for nested paths like 'clothing/user_id/file.jpg')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        logging.info(f"File saved locally: {file_path}")
        
        # Return URL that will be served by FastAPI
        return f"http://localhost:8000/uploads/{file_name}"

storage_service = StorageService()
