import os

from dotenv import load_dotenv
from zep_cloud.client import Zep


# Load environment variables from a .env file if present.
load_dotenv()

API_KEY = os.environ.get("ZEP_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "ZEP_API_KEY is missing. Set it in your environment or backend/.env before running this script."
    )

client = Zep(api_key=API_KEY)

print("Zep client initialized.")
