import json
from langchain_core.tools import tool
from app.db.session import SessionLocal
from app.models.models import User

@tool
def get_user_vitals(user_id: str) -> str:
    """
    Retrieve user preferences, budget constraints, and current style profile.
    Always call this when a user asks for recommendations to ensure budget/style constraints are met.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return "User not found."
        vitals = {
            "full_name": user.full_name,
            "budget_limit": user.budget_limit or "Not set",
            "style_profile": user.style_profile,
            "currency": user.currency
        }
        return json.dumps(vitals, indent=2)
    finally: db.close()
