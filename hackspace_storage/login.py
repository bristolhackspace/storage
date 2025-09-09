from datetime import datetime, timedelta, timezone
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from typing import Any
import jwt
from flask import Flask, Request, Response, abort, after_this_request, current_app, g, request, session

from hackspace_storage.extensions import db
from hackspace_storage.models import User

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

        try:
            user = User(
                sub=sub,
                email=email,
                name=name,
            )
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            query = sa.select(User).where(User.sub==decoded_token["sub"])
            user = db.session.execute(query).scalar_one()
            if user.email != email or user.name != name:
                user.email = email
                user.name = name
                db.session.commit()

        session["_user_id"] = user.id
        g.user = user

        return None

    @app.before_request
    def login_from_session() -> None:
        user_id = session.get("_user_id", None)
        if (user_id is not None) and ('user' not in g):
            user = db.session.get(User, user_id)
            if user is None:
                session.pop("_user_id")
            else:
                g.user = user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in g:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function