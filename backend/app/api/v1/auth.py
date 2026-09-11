from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.entities import User
from app.schemas.common import LoginIn, LogoutIn, RefreshIn, RegisterIn
from app.services.auth import authenticate, logout, register_citizen, rotate_refresh, user_payload

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterIn, request: Request, db: Annotated[Session, Depends(get_db)]):
    user = register_citizen(db, body.full_name, str(body.email), body.password, body.mobile, request)
    return {"user": user_payload(db, user), "message": "Registered as CITIZEN. Government roles require Admin assignment."}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Annotated[Session, Depends(get_db)]):
    user, access, refresh = authenticate(db, body.identifier, body.password, request)
    return {"accessToken": access, "refreshToken": refresh, "tokenType": "bearer", "user": user_payload(db, user)}


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request, db: Annotated[Session, Depends(get_db)]):
    user, access, refresh_tok = rotate_refresh(db, body.refresh_token, request)
    return {"accessToken": access, "refreshToken": refresh_tok, "tokenType": "bearer", "user": user_payload(db, user)}


@router.post("/logout")
def do_logout(
    body: LogoutIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    logout(db, body.refresh_token, user, request)
    return {"ok": True}


@router.get("/me")
def me(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    return user_payload(db, user)
