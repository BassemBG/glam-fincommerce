import sqlite3

conn = sqlite3.connect('virtual_closet.db')
cursor = conn.cursor()

# Check which columns already exist
cursor.execute("PRAGMA table_info(outfits)")
existing_columns = [col[1] for col in cursor.fetchall()]
print(f"Existing columns: {existing_columns}")

# Add missing columns
columns_to_add = [
    ("description", "TEXT"),
    ("style_tags", "TEXT DEFAULT '[]'"),
    ("qdrant_vector_id", "TEXT"),
    ("qdrant_payload", "TEXT DEFAULT '{}'")
]

for col_name, col_type in columns_to_add:
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE outfits ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except Exception as e:
            print(f"Failed to add {col_name}: {e}")
    else:
        print(f"Column {col_name} already exists")

conn.commit()
conn.close()
print("Migration complete!")
