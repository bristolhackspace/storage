from datetime import date, timedelta
from flask import Blueprint, current_app
import sqlalchemy as sa

from hackspace_storage.extensions import db
from hackspace_storage.mailer import send_email
from hackspace_storage.models import Area, Category, Slot, Booking, User

bp = Blueprint("nightly", __name__, cli_group=None)


@bp.cli.command("nightly")
def nightly():
    query = sa.select(Booking)
    bookings = db.session.execute(query).scalars()

    today = date.today()

    for booking in bookings:
        remaining_days = (booking.expiry - today).days
        if remaining_days < 0:
            current_app.logger.info(f"Deleting booking for slot {booking.slot.name}")
            send_email(booking.user, "email/expired", booking=booking)
            db.session.delete(booking)
        elif (
            booking.remind_me
            and not booking.reminder_sent
            and remaining_days < booking.slot.area.category.extension_period_days
        ):
            current_app.logger.info(
                f"Sending expiry reminder for slot {booking.slot.name} booked by {booking.user.name}"
            )
            booking.reminder_sent = True
            send_email(booking.user, "email/expiry_reminder", booking=booking)
    db.session.commit()
