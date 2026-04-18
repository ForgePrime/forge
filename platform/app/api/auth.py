"""Auth routes + current-user dependency.

POST /auth/register — create user + optional org + owner membership
POST /auth/login    — email+password → JWT access token
GET  /auth/me       — current user + memberships
POST /auth/logout   — client-side (JWT stateless); endpoint for symmetry only

Dependency `get_current_user` reads Authorization: Bearer <token> OR `forge_token` cookie.
Used by future endpoint protection (next session).
"""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Organization, Membership
from app.services.auth import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# --- Schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10)
    full_name: str | None = None
    org_slug: str | None = Field(None, description="If set, creates org and makes user owner. If null, user joins default org as editor.")
    org_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool


class MembershipResponse(BaseModel):
    organization_id: int
    organization_slug: str
    organization_name: str
    role: str


class MeResponse(BaseModel):
    user: UserResponse
    memberships: list[MembershipResponse]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserResponse


# --- Dependency ---

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Extract user from Authorization: Bearer OR 'forge_token' cookie.
    Raises 401 if missing/invalid/expired/inactive.
    """
    token: str | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("forge_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    try:
        uid = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is inactive")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Same as get_current_user but returns None instead of 401. Use for public pages that render differently when logged in."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


# --- Routes ---

@router.post("/register", response_model=MeResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create user. If `org_slug` given, create new org + owner. Else join default org as editor."""
    from sqlalchemy.exc import IntegrityError
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        # Concurrent race — other request won
        db.rollback()
        raise HTTPException(409, "Email already registered")

    # Determine org
    if body.org_slug:
        if db.query(Organization).filter(Organization.slug == body.org_slug).first():
            raise HTTPException(409, f"Organization slug '{body.org_slug}' already taken")
        org = Organization(
            slug=body.org_slug,
            name=body.org_name or body.org_slug,
        )
        db.add(org)
        db.flush()
        role = "owner"
    else:
        org = db.query(Organization).filter(Organization.slug == settings.default_org_slug).first()
        if not org:
            raise HTTPException(500, "Default organization missing — server bootstrap broken")
        role = "editor"

    db.add(Membership(user_id=user.id, organization_id=org.id, role=role))
    db.commit()
    db.refresh(user)

    return MeResponse(
        user=UserResponse(
            id=user.id, email=user.email, full_name=user.full_name,
            is_active=user.is_active, is_superuser=user.is_superuser,
        ),
        memberships=[MembershipResponse(
            organization_id=org.id, organization_slug=org.slug,
            organization_name=org.name, role=role,
        )],
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # Constant-time verify: always run bcrypt even if user not found (prevents enumeration)
    DUMMY = "$2b$12$CwTycUXWue0Thq9StjUM0uJ8W9Xd3nRkJ1oUN/NqVe.q6yGGi5GZS"
    stored = user.hashed_password if user else DUMMY
    ok = verify_password(body.password, stored)
    if not user or not ok or not user.is_active:
        raise HTTPException(401, "Invalid credentials")

    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    db.commit()

    token = create_access_token(user.id, user.email)
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.jwt_access_ttl_minutes)

    # Also set HttpOnly cookie for UI usage
    response.set_cookie(
        key="forge_token",
        value=token,
        max_age=settings.jwt_access_ttl_minutes * 60,
        httponly=True,
        samesite="lax",
    )

    return LoginResponse(
        access_token=token,
        expires_at=expires.isoformat(),
        user=UserResponse(
            id=user.id, email=user.email, full_name=user.full_name,
            is_active=user.is_active, is_superuser=user.is_superuser,
        ),
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("forge_token")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(Membership).filter(Membership.user_id == user.id).all()
    return MeResponse(
        user=UserResponse(
            id=user.id, email=user.email, full_name=user.full_name,
            is_active=user.is_active, is_superuser=user.is_superuser,
        ),
        memberships=[
            MembershipResponse(
                organization_id=m.organization_id,
                organization_slug=m.organization.slug,
                organization_name=m.organization.name,
                role=m.role,
            )
            for m in memberships
        ],
    )
