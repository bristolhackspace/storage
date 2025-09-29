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

from hackspace_storage.extensions import db
from hackspace_storage.models import User, Session
from hackspace_storage.token import generate_token, token_to_id


def create_session(user: User, sid: str|None):
    now = datetime.now(timezone.utc)
    idle_session_lifetime = timedelta(seconds=current_app.config["IDLE_SESSION_LIFETIME"])
    expiry = now + idle_session_lifetime
    secret = generate_token()
    stmt = insert(Session).values(
        id=uuid.uuid4(),
        secret=token_to_id(secret),
        external_id=sid,
        user_id=user.id,
        created=now,
        expiry=expiry
    ).on_conflict_do_update(
        index_elements=[Session.external_id],
        set_=dict(
            secret=token_to_id(secret),
            user_id=user.id,
            created=now,
            expiry=expiry,
        )
    ).returning(Session)

    orm_stmt = sa.select(Session).from_statement(stmt).execution_options(populate_existing=True)
    session: Session = db.session.execute(orm_stmt).scalar_one()
    db.session.commit()

    g.session = session
    g.user = session.user

    @after_this_request
    def update_session(response: Response):
        session_value = f"{session.id.hex}:{secret}"
        response.set_cookie(
            "id",
            session_value,
            max_age=idle_session_lifetime,
            secure=current_app.config["SESSION_COOKIE_SECURE"],
            httponly=current_app.config["SESSION_COOKIE_HTTPONLY"]
        )



def init_app(app: Flask):
    @app.before_request
    def login_from_request() -> None:
        login_token = request.args.get('login_token')
        if login_token is None:
            return None

        start_secret = current_app.config["LOGIN_START_SECRET"]
        try:
            decoded_token = jwt.decode(
                login_token,
                start_secret,
                algorithms="HS256",
                options=dict(require=["exp"])
            )
        except jwt.PyJWTError as ex:
            current_app.logger.warning(f"Error decoding login token {ex}")
            return None

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

        create_session(user, decoded_token.get("sid"))

        return None

    @app.before_request
    def login_from_session() -> None:
        if 'session' in g:
            return

        session_value = request.cookies.get("id", "").split(":")
        if len(session_value) != 2:
            return
        session_id, secret = session_value

        session = db.session.get(Session, session_id)
        if not session:
            return
        
        if not secrets.compare_digest(session.secret, token_to_id(secret)):
            return
        
        now = datetime.now(timezone.utc)
        if now > session.expiry:
            return
        
        g.session = session
        g.user = session.user

        session.expiry = now + current_app.permanent_session_lifetime
        db.session.commit()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in g:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function