from langchain_core.tools import tool
from typing import Optional
import httpx
import json
from app.db.session import SessionLocal
from app.models.models import User

@tool
def manage_wallet(user_id: str, action: str, amount: Optional[float] = None, item_name: Optional[str] = None) -> str:
    """
    Manage the user's fashion wallet.
    - action='check': Check the current balance.
    - action='propose_purchase': Suggest buying an item. This WILL NOT subtract money, 
      but will trigger a confirmation modal on the frontend.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return "User not found."
        if action == "check": return f"Balance: {user.wallet_balance} {user.currency}."
        if action == "propose_purchase":
            if amount is None or item_name is None: return "Missing amount/item."
            if user.wallet_balance < amount: 
                return f"[BUDGET_EXCEEDED] item='{item_name}' price={amount} balance={user.wallet_balance} currency='{user.currency}'"
            return f"[WALLET_CONFIRMATION_REQUIRED] item='{item_name}' price={amount} currency='{user.currency}'"
        return "Invalid action."
    finally: db.close()
@tool
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Convert a price from one currency to another using real-time market rates.
    Use this before manage_wallet if the item's price is not in the user's base currency.
    """
    try:
        from_cur = from_currency.upper()
        to_cur = to_currency.upper()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Using the free ExchangeRate-API (no key required for public latest rates)
            url = f"https://api.exchangerate-api.com/v4/latest/{from_cur}"
            response = await client.get(url)
            
            if response.status_code != 200:
                return f"Error fetching rates for {from_cur}. Status: {response.status_code}"
                
            data = response.json()
            rates = data.get("rates", {})
            
            if to_cur not in rates:
                return f"Unable to find rate for {to_cur} in {from_cur} data."
                
            rate = rates[to_cur]
            converted = amount * rate
            
            return f"{amount} {from_cur} is {round(converted, 2)} {to_cur} (Rate: {rate})."
            
    except Exception as e:
        return f"Real-time conversion error: {str(e)}"
