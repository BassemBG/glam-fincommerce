"""
Initialize the SQLite database with tables and a demo user.
Run this once: python init_db.py
"""
from app.db.session import engine
from app.models.models import SQLModel, User
from app.core.security import get_password_hash
from app.services.zep_service import create_zep_user
from sqlmodel import Session

def init_database():
    # Create all tables
    SQLModel.metadata.create_all(engine)
    print("Database tables created!")
    
    # Create a demo user if none exists
    with Session(engine) as session:
        existing_user = session.query(User).first()
        if not existing_user:
            # Use proper bcrypt hashing for demo user
            demo_user = User(
                email="demo@example.com",
                hashed_password=get_password_hash("demo123"),
                full_name="Demo User",
                full_body_image=None
            )
            session.add(demo_user)
            session.commit()
            session.refresh(demo_user)
            print("Demo user created! (email: demo@example.com, password: demo123)")
            
            # Create user in Zep Cloud
            create_zep_user(
                user_id=demo_user.id,
                email=demo_user.email,
                full_name=demo_user.full_name
            )
        else:
            print("User already exists, skipping demo user creation.")
    
    print("\nDatabase is ready! You can now start the server.")

if __name__ == "__main__":
    init_database()
