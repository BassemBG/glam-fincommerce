import logging
from qdrant_client import QdrantClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manages Qdrant connection and client instance"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = None
        return cls._instance

    def __init__(self):
        if self.client is None:
            self._connect()

    def _connect(self):
        try:
            if settings.QDRANT_API_KEY:
                # Cloud connection
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=30
                )
                logger.info(f"✅ Connected to Qdrant Cloud at {settings.QDRANT_URL}")
            else:
                # Local connection
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    timeout=30
                )
                logger.info(f"✅ Connected to local Qdrant at {settings.QDRANT_URL}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {str(e)}")
            raise

    def get_client(self):
        if self.client is None:
            self._connect()
        return self.client

    @staticmethod
    def get_instance():
        return QdrantManager()
