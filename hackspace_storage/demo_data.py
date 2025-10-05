import click
from flask import Blueprint, current_app
import random
from datetime import datetime, timezone, timedelta
import secrets
import jwt

from hackspace_storage.database import db
from hackspace_storage.models import Area, Category, Slot, Booking, User

bp = Blueprint('demo', __name__, cli_group=None)


@bp.cli.command("make-demo-data")
def make_demo_data():
    db.drop_all()
    db.create_all()

    material_category = Category(
        name="material",
        max_bookings=2,
        initial_duration_days=7,
        extension_duration_days=14,
        extension_period_days=10,
        max_extensions=2
    )

    left_area = Area(name="Left", column_count=3, category=material_category)
    right_area = Area(name="Right", column_count=4, category=material_category)
    back_area = Area(name="Back", column_count=2, category=material_category)
    areas = [left_area, right_area, back_area]

    db.session.add_all(areas)

    demo_user = User(
        sub="demo",
        email="example@demo.com",
        name="Demo McDemoFace"
    )

    db.session.add(demo_user)

    for area in areas:
        for i in range(5):
            area.slots.append(Slot(
                name=f"{area.name[0]}{i:03}"
            ))
        month = random.randrange(1,12)
        area.slots[0].bookings.append(Booking(
            user=demo_user,
            expiry=datetime(2025, month, 17),
            description=f"Cool thingy"
        ))
    db.session.commit()

@bp.cli.command("make-login")
@click.argument("name")
@click.argument("email")
@click.option('--sid', prompt='Session ID', help='External session ID (used to logout session externally)')
def make_login(name, email, sid):
    sub = f"demouser {email}"
    # Longer expiry than we'd usually use, but easier for testing
    expiry = datetime.now(timezone.utc) + timedelta(days=1)

    payload = {
        "exp": int(expiry.timestamp()),
        "sub": sub,
        "name": name,
        "email": email,
        "nonce": secrets.token_urlsafe()
    }

    if sid:
        payload["sid"] = sid

    token = jwt.encode(payload, current_app.config["LOGIN_START_SECRET"], "HS256")
    print(f"Copy this onto the end of the URL to login: ?login_token={token}")


@bp.cli.command("make-logout")
@click.argument("sid")
def make_logout_token(sid):
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=30)

    payload = {
        "exp": int(expiry.timestamp()),
        "iat": int(now.timestamp()),
        "sid": sid,
        "events": {
            "http://schemas.openid.net/event/backchannel-logout": {}
        }
    }

    token = jwt.encode(payload, current_app.config["LOGIN_START_SECRET"], "HS256")
    print(f"Send a POST request with logout_token={token} to /backchannel-logout")