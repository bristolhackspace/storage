from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any
import jwt
from flask import Flask, Request, Response, abort, after_this_request, current_app, g, request, session

def init_app(app: Flask):
    @app.before_request
    def login_from_request() -> dict[str, Any] | None:
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
            return

        session["sub"] = decoded_token["sub"]
        session["name"] = decoded_token["name"]
        session["email"] = decoded_token["email"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "sub" not in session:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function