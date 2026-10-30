"""Sign-up, sign-in and sessions.

Passwords are hashed with scrypt and a per-user salt. A session is a random token in an httpOnly cookie;
the database stores only the token's SHA-256, with an expiry.
"""

import hashlib
import hmac
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, StringConstraints

from app.db import get_db

SESSION_COOKIE = "prelegal_session"
SESSION_LIFETIME = timedelta(days=30)
# Shared by setting and deleting the cookie, which must match for the browser to remove it.
COOKIE_OPTIONS = {"httponly": True, "samesite": "lax"}

# scrypt cost parameters (about 16 MB of memory per hash), stored with each hash so they can change later.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1

router = APIRouter(prefix="/api/auth", tags=["auth"])

# scope="function" commits before the response is sent, so a follow-up request sees the change.
Db = Annotated[sqlite3.Connection, Depends(get_db, scope="function")]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# The minimum length is also checked in the sign-up form (MIN_PASSWORD_LENGTH in frontend/src/auth/api.ts).
Password = Annotated[str, StringConstraints(min_length=8, max_length=200)]


class SignUpRequest(BaseModel):
    email: EmailStr
    name: Name
    password: Password


class SignInRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(max_length=200)]


class User(BaseModel):
    id: int
    email: str
    name: str


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(candidate.hex(), digest)


# Checked against when the email is unknown, so a failed sign-in takes as long either way. Computed once at
# import, which costs one scrypt hash.
DUMMY_HASH = hash_password(secrets.token_hex(16))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def sign_up(body: SignUpRequest, db: Db) -> User:
    """Creates an account. It does not sign the user in: they go on to the sign-in screen."""
    try:
        row = db.execute(
            "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?) RETURNING id, email, name",
            (body.email.lower(), body.name, hash_password(body.password)),
        ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    return User(**row)


@router.post("/signin")
def sign_in(body: SignInRequest, response: Response, db: Db) -> User:
    row = db.execute(
        "SELECT id, email, name, password_hash FROM users WHERE email = ?", (body.email.lower(),)
    ).fetchone()
    # Always verify, even for an unknown email, so the response time does not reveal which emails exist.
    password_ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH)
    if row is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + SESSION_LIFETIME
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (token_hash(token), row["id"], expires.isoformat()),
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        **COOKIE_OPTIONS,
    )
    return User(id=row["id"], email=row["email"], name=row["name"])


def current_user(db: Db, session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> User:
    """FastAPI dependency: the signed-in user, or a 401."""
    row = None
    if session:
        row = db.execute(
            """
            SELECT users.id, users.email, users.name FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash(session), datetime.now(UTC).isoformat()),
        ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return User(**row)


CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/me")
def me(user: CurrentUser) -> User:
    return user


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(response: Response, db: Db, session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> None:
    if session:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(session),))
    response.delete_cookie(SESSION_COOKIE, **COOKIE_OPTIONS)
