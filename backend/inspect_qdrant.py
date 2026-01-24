"""
Script to inspect Qdrant data for outfit embeddings.
Run this while the backend server is NOT running, OR check the database directly.
"""
from qdrant_client import QdrantClient
import sqlite3
import os

print("=== Checking SQLite for Qdrant References ===")
try:
    conn = sqlite3.connect('virtual_closet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, qdrant_vector_id, qdrant_payload FROM outfits WHERE qdrant_vector_id IS NOT NULL")
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"\nOutfit ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"Qdrant Vector ID: {row[2]}")
            print(f"Qdrant Payload: {row[3]}")
    else:
        print("No outfits with Qdrant embeddings yet.")
    
    conn.close()
except Exception as e:
    print(f"SQLite Error: {e}")

print("\n=== Checking Qdrant Storage (requires server to be stopped) ===")
storage_path = os.path.join(os.getcwd(), "qdrant_storage")
try:
    client = QdrantClient(path=storage_path)
    collection = client.get_collection("outfits")
    print(f"Collection: outfits")
    print(f"Vector Size: {collection.config.params.vectors.size}")
    print(f"Points Count: {collection.points_count}")
    
    results = client.scroll(collection_name="outfits", limit=20, with_payload=True, with_vectors=False)
    for point in results[0]:
        print(f"\n--- Point ID: {point.id} ---")
        print(f"Payload: {point.payload}")
except RuntimeError as e:
    print(f"Qdrant storage is locked (server is running). Check SQLite output above.")
except Exception as e:
    print(f"Qdrant Error: {e}")

print("\n=== Done ===")
