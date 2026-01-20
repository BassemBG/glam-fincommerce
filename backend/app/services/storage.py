import os
import logging

class StorageService:
    def __init__(self):
        # Create uploads directory if it doesn't exist
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # S3 client (optional)
        self.s3_client = None
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
        except Exception as e:
            logging.warning(f"S3 not configured: {e}")

    async def upload_file(self, file_content: bytes, file_name: str, content_type: str) -> str:
        """Uploads a file to S3 or saves locally."""
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
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
            except Exception as e:
                logging.error(f"S3 Upload error: {e}")
                # Fall through to local storage
        
        # Local storage fallback
        file_path = os.path.join(self.upload_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(file_content)
        logging.info(f"File saved locally: {file_path}")
        
        # Return URL that will be served by FastAPI
        return f"http://localhost:8000/uploads/{file_name}"

storage_service = StorageService()
