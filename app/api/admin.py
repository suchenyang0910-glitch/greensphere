from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.admin_auth import admin_auth
from app.models.waitlist import WaitlistSubscriber
from app.models.telegram_user import TelegramUser
from datetime import date

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_auth)])