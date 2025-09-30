from datetime import datetime, timedelta, timezone
from functools import wraps
import secrets
import sqlalchemy as sa
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.dialects.postgresql import insert
from typing import Any
import uuid
import jwt
from flask import Flask, Request, Response, abort, after_this_request, current_app, g, request, session
from flask_sqlalchemy import SQLAlchemy

from hackspace_storage.models import User, Login


def _make_timedelta(value: timedelta | int) -> timedelta:
    if isinstance(value, timedelta):
        return value

    return timedelta(seconds=value)


class LoginManager:
    def __init__(self, db: SQLAlchemy):
        self.db = db

    def init_app(self, app: Flask):
        self.idle_timeout = _make_timedelta(current_app.config.get("LOGIN_IDLE_TIMEOUT", 60*10))
        self.absolute_timeout = _make_timedelta(current_app.config.get("LOGIN_ABSOLUTE_TIMEOUT", 60*60))
        self.cookie_name = current_app.config.get("LOGIN_COOKIE_NAME", "id")
        self.cookie_secure = current_app.config.get("LOGIN_COOKIE_SECURE", False)
        self.start_secret = current_app.config["LOGIN_START_SECRET"]

        @app.before_request
        def do_login():
            login_token = request.args.get('login_token')
            if login_token is not None:
                self.login_from_token(login_token)

            if 'user' not in g:
                self.login_from_cookie()

    def login_from_token(self, login_token: str):
        try:
            decoded_token: dict[str, Any] = jwt.decode(
                login_token,
                self.start_secret,
                algorithms="HS256",
                options=dict(require=["exp"])
            )
        except jwt.PyJWTError as ex:
            current_app.logger.warning(f"Error decoding login token {ex}")
            return None
        
        user = self.create_user_from_id_token(decoded_token)
        self.create_login(user, decoded_token.get("sid"))

    def create_user_from_id_token(self, decoded_token: dict[str, Any]) -> User:
        sub = decoded_token["sub"]
        email = decoded_token["email"]
        name = decoded_token["name"]

        stmt = insert(User).values(
            sub=sub,
            email=email,
            name=name
        ).on_conflict_do_update(
            index_elements=[User.sub],
            set_=dict(
                email=email,
                name=name
            )
        ).returning(User)

        orm_stmt = sa.select(User).from_statement(stmt).execution_options(populate_existing=True)

        user = db.session.execute(orm_stmt).scalar_one()
        db.session.commit()

        return user

    def create_login(self, user: User, sid: str|None):
        now = datetime.now(timezone.utc)
        expiry = now + self.idle_timeout
        secret = secrets.token_urlsafe()
        stmt = insert(Login).values(
            id=uuid.uuid4(),
            secret=secret,
            external_id=sid,
            user_id=user.id,
            created=now,
            expiry=expiry
        ).on_conflict_do_update(
            index_elements=[Login.external_id],
            set_=dict(
                secret=secret,
                user_id=user.id,
                created=now,
                expiry=expiry,
            )
        ).returning(Login)

        orm_stmt = sa.select(Login).from_statement(stmt).execution_options(populate_existing=True)
        login: Login = db.session.execute(orm_stmt).scalar_one()
        db.session.commit()

        g.user = user
        g.login = login

        @after_this_request
        def update_session(response: Response):
            session_value = f"{login.id.hex}:{secret}"
            response.set_cookie(
                self.cookie_name,
                session_value,
                secure=self.cookie_secure,
                httponly=True
            )

    def login_from_cookie(self):
        now = datetime.now(timezone.utc)

        login_cookie = request.cookies.get(self.cookie_name)
        if login_cookie is None:
            return
        
        login_cookie = login_cookie.split(":")
        if len(login_cookie) != 2:
            return
        
        login_id, secret = login_cookie
        login = db.session.get(Login, login_id)
        if login is None:
            return
        
        if now > login.expiry:
            db.session.delete(login)
            db.session.commit()
            return
        
        if not secrets.compare_digest(secret, login.secret):
            return

        g.user = login.user
        g.login = login

        login.expiry = now + self.idle_timeout
        db.session.commit()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in g:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function