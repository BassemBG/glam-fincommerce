"""
Initialize the SQLite database with tables and a demo user.
Run this once: python init_db.py
"""
from app.db.session import engine
from app.models.models import SQLModel, User
from sqlmodel import Session

def init_database():
    # Create all tables
    SQLModel.metadata.create_all(engine)
    print("Database tables created!")
    
    # Create a demo user if none exists
    with Session(engine) as session:
        existing_user = session.query(User).first()
        if not existing_user:
            # Simple hash for demo purposes (in production use proper bcrypt)
            demo_user = User(
                email="demo@example.com",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.RBnSdwUDljC4e.",  # demo123
                full_name="Demo User",
                full_body_image=None
            )
            session.add(demo_user)
            session.commit()
            print("Demo user created! (email: demo@example.com, password: demo123)")
        else:
            print("User already exists, skipping demo user creation.")
    
    print("\nDatabase is ready! You can now start the server.")

if __name__ == "__main__":
    init_database()
