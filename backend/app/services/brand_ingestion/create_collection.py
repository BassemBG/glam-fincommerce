from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(
    url="https://5e3f8a20-7c62-4eab-8f2c-6b2261318501.us-east4-0.gcp.cloud.qdrant.io",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.AKxEYsJW9f2r-63M_zdeyhSsHFM_XKKg0jShyap0vMY"
)

client.create_collection(
    collection_name="clothing",
    vectors_config=VectorParams(
        size=384,  # MUST match your embedding model
        distance=Distance.COSINE
    )
)
