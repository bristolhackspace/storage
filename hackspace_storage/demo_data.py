from flask import Blueprint
import random 
import datetime

from hackspace_storage.extensions import db
from hackspace_storage.models import Area, Slot, Booking, User

bp = Blueprint('demo', __name__, cli_group=None)


@bp.cli.command("make-demo-data")
def make_demo_data():
    db.drop_all()
    db.create_all()

    left_area = Area(name="Left")
    right_area = Area(name="Right")
    back_area = Area(name="Back")
    areas = [left_area, right_area, back_area]

    db.session.add_all(areas)

    demoUser = User(
        sub="demo",
        email="example@demo.com",
        name="Marsh"
    )

    db.session.add(demoUser)

    for area in areas:
        for i in range(5):
            area.slots.append(Slot(
                name=f"{area.name[0]}{i:03}"
            ))
            if i % 2 == 0:
                month = random.randrange(1,12)
                area.slots[i].bookings.append(Booking(
                    user_id=1,
                    expiry=datetime.datetime(2025, month, 17),
                    description=f"Booking made for month {month}"
                ))
    db.session.commit()
