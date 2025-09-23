import click
from flask import Blueprint, current_app
import random
from datetime import datetime, timezone, timedelta
import secrets
import jwt

from hackspace_storage.extensions import db
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
def make_login(name, email):
    sub = f"demouser {email}"
    # Longer expiry than we'd usually use, but easier for testing
    expiry = datetime.now(timezone.utc) + timedelta(days=1)

    payload = {
        "exp": int(expiry.timestamp()),
        "sub": sub,
        "name": name,
        "email": email
    }

    token = jwt.encode(payload, current_app.config["LOGIN_START_SECRET"], "HS256")
    print(f"Copy this onto the end of the URL to login: ?login_token={token}")