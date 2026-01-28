"""
Add missing columns to existing users and outfits tables without dropping data
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, JSON, text
from sqlalchemy.exc import OperationalError
import os

# Database URL
DATABASE_URL = "sqlite:///./virtual_closet.db"
engine = create_engine(DATABASE_URL, echo=True)

def migrate_database():
    """Add missing columns to users and outfits tables"""
    with engine.connect() as conn:
        # Migrate users table
        print("\n=== MIGRATING USERS TABLE ===")
        cursor = conn.execute(text("PRAGMA table_info(users)"))
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        print(f"Existing users columns: {existing_columns}")
        
        # Define columns to add to users
        users_columns_to_add = {
            'zep_thread_id': 'TEXT',
            'gender': 'TEXT',
            'age': 'INTEGER',
            'education': 'TEXT',
            'country': 'TEXT',
            'daily_style': 'TEXT',
            'color_preferences': 'JSON',
            'fit_preference': 'TEXT',
            'price_comfort': 'TEXT',
            'buying_priorities': 'JSON',
            'clothing_description': 'TEXT',
            'styled_combinations': 'TEXT',
            'onboarding_completed': 'BOOLEAN DEFAULT 0',
            'budget_limit': 'REAL',
            'min_budget': 'REAL',
            'max_budget': 'REAL',
            'currency': 'TEXT DEFAULT "TND"',
            'wallet_balance': 'REAL DEFAULT 0.0',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
        }
        
        # Add missing columns to users
        for col_name, col_type in users_columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(alter_sql))
                    print(f"✓ Added users.{col_name}")
                except OperationalError as e:
                    print(f"✗ Could not add users.{col_name}: {e}")
        
        # Migrate outfits table
        print("\n=== MIGRATING OUTFITS TABLE ===")
        cursor = conn.execute(text("PRAGMA table_info(outfits)"))
        outfits_columns = {row[1] for row in cursor.fetchall()}
        
        print(f"Existing outfits columns: {outfits_columns}")
        
        # Define columns to add to outfits
        outfits_columns_to_add = {
            'description': 'TEXT',
            'style_tags': 'JSON',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
        }
        
        # Add missing columns to outfits
        for col_name, col_type in outfits_columns_to_add.items():
            if col_name not in outfits_columns:
                try:
                    alter_sql = f"ALTER TABLE outfits ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(alter_sql))
                    print(f"✓ Added outfits.{col_name}")
                except OperationalError as e:
                    print(f"✗ Could not add outfits.{col_name}: {e}")
        
        conn.commit()
        print("\n✅ Database migration complete!")

if __name__ == "__main__":
    migrate_database()
