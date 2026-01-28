import os
from dotenv import load_dotenv

load_dotenv()

# ===========================
# QDRANT CLOUD CONFIG
# ===========================
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_COLLECTION_NAME = "clothing"

# ===========================
# EMBEDDING CONFIG
# ===========================
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # sentence-transformers model
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 produces 384-dim vectors

# ===========================
# API KEYS
# ===========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

