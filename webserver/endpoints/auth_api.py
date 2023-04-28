import logging
import os
import random
import re
import string

from datetime import datetime, timedelta
from typing import Union, Optional, Annotated

from fastapi import Depends, HTTPException, status, Cookie, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import RedirectResponse

from utils import db, db_models
from utils.rabbitmq import AdminMessage, EmailNotification

# TODO: merge this into utils

# openssl rand -hex 32
SECRET_KEY = os.getenv("ACCESS_SECRET_KEY", "this_is_not_a_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 24 * 60 * 7))

if SECRET_KEY == "this_is_not_a_secret":
    logging.warning("SECRET_KEY is NOT SET")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def add_user(username: str, password: str) -> bool:
    if int(db_models.Config.get(db_models.Config.key == "account_registration_enabled").value) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Registrierung ist zurzeit deaktiviert",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if len(username) <= 5 or len(password) <= 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passwort muss mindestens 8 Zeichen lang sein und der Benutzername mindestens 5 Zeichen",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not db_models.Account.select().where(db_models.Account.username == username).exists():
        db.create_account(username, get_password_hash(password))
        return True
    return False


def authenticate_user(username: str, password: str) -> Optional[db_models.Account]:
    user = db_models.Account.select().where(db_models.Account.username == username).get_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password):
        return None
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


def get_current_user(request: Request,
                     access_token: Union[str, None] = Cookie(default=None)) -> db_models.Account:
    access_token_header = request.headers.get("Authorization", None)

    if access_token is None:
        access_token = access_token_header

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"location": "/public/"},
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

    user: Union[None, db_models.Account] = db_models.Account.select().where(
        db_models.Account.username == token_data.username).get_or_none()

    if user is None:
        raise credentials_exception

    if user.verified == 0:
        raise HTTPException(status_code=302,
                            detail="E-Mail des Accounts wurde noch nicht verifiziert! Bitte überprüfe deine E-Mails und klicke auf den Verifizierungslink.",
                            headers={"location": "/auth/verify_mail"})

    return user


def is_user_logged_in(request: Request, access_token: Union[str, None] = Cookie(default=None)) -> bool:
    return (get_current_user_if_logged_in(request, access_token)) is not None


def get_admin_user(request: Request, access_token: Union[str, None] = Cookie(default=None)) -> db_models.Account:
    user = get_current_user(request, access_token)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return user


def is_admin_user(request: Request, access_token: Union[str, None] = Cookie(default=None)) -> bool:
    user = get_current_user_if_logged_in(request, access_token)
    if user is None:
        return False
    return user.role == "admin"


def get_current_user_if_logged_in(request: Request, access_token: Union[str, None] = Cookie(default=None)) -> \
        Optional[db_models.Account]:
    access_token_header = request.headers.get("Authorization", None)

    if access_token is None:
        access_token = access_token_header

    if access_token is None:
        return None

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except JWTError:
        return None

    return db_models.Account.select().where(db_models.Account.username == token_data.username).get_or_none()


regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'


def check_email_format(email: str) -> bool:
    return re.fullmatch(regex, email) is not None


def set_api_routes(app, templates):
    @app.get("/login", dependencies=[Depends(db.get_db)])
    def serve_login_site(request: Request, logged_in: db_models.Account = Depends(get_current_user_if_logged_in)):
        if logged_in is not None:
            return RedirectResponse("/public/team/")
        return templates.TemplateResponse("login/login.html", {"request": request})

    @app.get("/register", dependencies=[Depends(db.get_db)])
    def server_register_site(request: Request,
                             logged_in: db_models.Account = Depends(get_current_user_if_logged_in)):
        if logged_in is not None:
            return RedirectResponse("/public/team/")
        return templates.TemplateResponse("login/register.html", {"request": request})

    @app.post("/new_token", response_model=Token, dependencies=[Depends(db.get_db)])
    @app.state.limiter.limit("20/minute")
    def register_new_account(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
        if not check_email_format(form_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ungültige Email-Adresse",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not add_user(form_data.username, form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"E-Mail-Addresse '{form_data.username}' wird bereits verwendet",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return login(form_data.username, form_data.password)

    @app.post("/token", response_model=Token, dependencies=[Depends(db.get_db)])
    @app.state.limiter.limit("200/minute")
    def get_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
        return login(form_data.username, form_data.password)

    def login(username: str, password: str) -> RedirectResponse:
        user = authenticate_user(username, password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        response = RedirectResponse(url="/public/team/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=f"{access_token}", httponly=True)

        account = db_models.Account.select().where(db_models.Account.username == username).get_or_none()

        if account is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        account.password_reset_token = None
        account.save()

        return response

    @app.get("/me", dependencies=[Depends(db.get_db)])
    @app.state.limiter.limit("20/minute")
    def read_user(request: Request, current_user: db_models.Account = Depends(get_current_user)):
        return current_user.username

    @app.get("/logout", dependencies=[Depends(db.get_db)])
    def logout():
        response = RedirectResponse("/")
        response.delete_cookie("access_token")
        return response

    @app.get("/verify/{token}", dependencies=[Depends(db.get_db)])
    @app.state.limiter.limit("20/minute")
    def verify_email(request: Request, token: str,
                     logged_in: db_models.Account = Depends(get_current_user_if_logged_in)):
        account: Union[None, db_models.Account] = db_models.Account.select().where(
            db_models.Account.verification_code == token).get_or_none()

        if account is None:
            raise HTTPException(detail="Unable to verify account", status_code=status.HTTP_401_UNAUTHORIZED)

        if account.verified == 1:
            AdminMessage(message=f"User clicked verification link again: {account.username}").send()

        account.verified = 1
        account.save()

        AdminMessage(message=f"Account E-Mail verified: {account.username}").send()

        return templates.TemplateResponse("login/verify_email_success.html", {"request": request, "logged_in": True})

    @app.get("/verify_mail", dependencies=[Depends(db.get_db)])
    def verify_mail(request: Request, logged_in: db_models.Account = Depends(get_current_user_if_logged_in)):
        if logged_in is None:
            return RedirectResponse("/auth/login")

        if logged_in.verified == 1:
            return RedirectResponse("/public/team/")

        return templates.TemplateResponse("login/verify_email.html",
                                          {"request": request, "email": logged_in.username, "logged_in": True})

    @app.get("/r/reset/password/request", dependencies=[Depends(db.get_db)])
    def reset_password(request: Request):
        return templates.TemplateResponse("login/reset_password_request.html",
                                          {"request": request})

    @app.get("/r/reset/password/{token}", dependencies=[Depends(db.get_db)])
    def reset_password(request: Request, token: str):
        return templates.TemplateResponse("login/reset_password.html",
                                          {"request": request, "reset_token": token})

    @app.post("/reset/password/request", dependencies=[Depends(db.get_db)])
    @app.state.limiter.limit("20/minute")
    def reset_request(request: Request, username: Annotated[str, Form()]):
        account: Union[None, db_models.Account] = db_models.Account.select().where(
            db_models.Account.username == username).get_or_none()

        if account is None:
            raise HTTPException(detail="Account existiert nicht", status_code=status.HTTP_401_UNAUTHORIZED)

        account.password_reset_token = "".join(random.choices(string.ascii_letters + string.digits, k=60))
        account.save()

        EmailNotification().manual_message(subject="Passwort zurücksetzen",
                                           message=f"Um dein Passwort zurückzusetzen, klicke auf folgenden Link: {os.getenv('WEB_SERVER_URL', 'https://airlan.comp-air.at')}/auth/r/reset/password/{account.password_reset_token}",
                                           email=account.username).send()

        return RedirectResponse(url="/auth/r/reset/password/token", status_code=status.HTTP_302_FOUND)

    @app.post("/reset/password/", dependencies=[Depends(db.get_db)])
    @app.state.limiter.limit("20/minute")
    def reset_password(request: Request, token: Annotated[str, Form()], password: Annotated[str, Form()]):
        account: Union[None, db_models.Account] = db_models.Account.select().where(
            db_models.Account.password_reset_token == token).get_or_none()

        if account is None:
            raise HTTPException(detail="Account existiert nicht", status_code=status.HTTP_401_UNAUTHORIZED)

        if len(password) < 8:
            raise HTTPException(detail="Passwort muss mindestens 8 Zeichen lang sein",
                                status_code=status.HTTP_401_UNAUTHORIZED)

        account.password = get_password_hash(password)
        account.password_reset_token = None
        account.save()

        return login(account.username, password)
