import os
from fastapi import Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi import status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


def create_default_user(db: Session):
    existing = db.query(User).filter_by(username=DEFAULT_USERNAME).first()
    if not existing:
        user = User(username=DEFAULT_USERNAME, password_hash=pwd_context.hash(DEFAULT_PASSWORD))
        db.add(user)
        db.commit()


def verify_user(username: str, password: str, db: Session) -> bool:
    user = db.query(User).filter_by(username=username).first()
    if not user:
        return False
    return pwd_context.verify(password, user.password_hash)


def get_current_user(request: Request):
    return request.session.get("user")


def require_login(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return None


def login_action(request: Request, db: Session, username: str, password: str):
    if verify_user(username, password, db):
        request.session["user"] = username
        return True
    return False


def logout_action(request: Request):
    request.session.clear()