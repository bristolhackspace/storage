from datetime import date, timedelta
from flask import Blueprint
import sqlalchemy as sa

from hackspace_storage.database import db
from hackspace_storage.models import Area, Category, Slot, Booking, User

bp = Blueprint('nightly', __name__, cli_group=None)


@bp.cli.command("nightly")
def nightly():
    query = sa.select(Booking)
    bookings = db.session.get(query).all()

    today = date.today()

    for booking in bookings:
        if today > booking.expiry:
            db.session.delete(booking)
    db.session.commit()