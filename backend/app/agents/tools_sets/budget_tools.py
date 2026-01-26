from langchain_core.tools import tool
from typing import Optional
import json
from app.db.session import SessionLocal
from app.models.models import User

@tool
def manage_wallet(user_id: str, action: str, amount: Optional[float] = None, item_name: Optional[str] = None) -> str:
    """
    Manage the user's fashion wallet. 
    - action='check': Current balance.
    - action='propose_purchase': Marks an item for purchase confirmation.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return "User not found."
        if action == "check": return f"Balance: {user.wallet_balance} {user.currency}."
        if action == "propose_purchase":
            if amount is None or item_name is None: return "Missing amount/item."
            if user.wallet_balance < amount: return "Insufficient funds."
            return f"[WALLET_CONFIRMATION_REQUIRED] item='{item_name}' price={amount} currency='{user.currency}'"
        return "Invalid action."
    finally: db.close()
