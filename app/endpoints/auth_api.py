import logging
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Union

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import RedirectResponse

# openssl rand -hex 32
SECRET_KEY = os.getenv("ACCESS_SECRET_KEY", "this_is_not_a_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 2))

if SECRET_KEY == "this_is_not_a_secret":
    logging.warning("SECRET_KEY is NOT SET")
    # time.sleep(2)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

users = {
    "api_req": {
        "username": "api_req",
        "hashed_password": pwd_context.hash(os.getenv("API_PASSWORD", "admin"))
    },
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash(os.getenv("ADMIN_PASSWORD", "admin"))
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None


class User(BaseModel):
    username: str


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, access_token: Union[str, None] = Cookie(default=None)):
    access_token_header = request.headers.get("Authorization", None)

    if access_token is None:
        access_token = access_token_header

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if access_token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


def login_to_master() -> str:
    if str(os.getenv("MASTER", 1)) == "0":
        logging.info(f"Logging in to master -> {os.getenv('MASTER_URL')}")
        session = requests.Session()
        res = session.post(f"http://{os.getenv('MASTER_IP')}/auth/token",
                           data={"username": "api_req", "password": os.getenv("API_PASSWORD", "admin")})
        return session.cookies.get("access_token")
    else:
        return create_access_token(data={"sub": "api_req"},
                                   expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def login_to_master_headers() -> dict:
    return {"Authorization": login_to_master()}


def set_api_routes(app, templates):
    @app.get("/login")
    async def login_for_access_token(request: Request):
        return templates.TemplateResponse("login.html", {"request": request})

    @app.post("/token", response_model=Token)
    async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
        user = authenticate_user(users, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        response = RedirectResponse(url="/status", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=f"{access_token}", httponly=True)
        return response

    @app.get("/me", response_model=User)
    async def read_users_me(current_user: User = Depends(get_current_user)):
        return current_user
