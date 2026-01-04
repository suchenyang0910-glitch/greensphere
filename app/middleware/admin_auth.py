import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


def admin_auth(x_admin_key: str = Header(None)):
    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")