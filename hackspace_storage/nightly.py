from datetime import date, timedelta
import click
from flask import Blueprint
import sqlalchemy as sa

from hackspace_storage.booking_rules import can_extend_booking
from hackspace_storage.database import db
from hackspace_storage.mailer import send_email
from hackspace_storage.models import Area, Category, Slot, Booking, User

bp = Blueprint('nightly', __name__, cli_group=None)


@bp.cli.command("nightly")
@click.option('--dry-run', is_flag=True)
def nightly(dry_run: bool):
    query = sa.select(Booking)
    bookings = db.session.execute(query).scalars()

    today = date.today()

    for booking in bookings:
        if can_extend_booking(booking) and booking.reminder_sent == False:
            if dry_run:
                print(f"Expiry reminder for booking {booking.description} with expiry {booking.expiry} from slot {booking.slot.name}. Booked by {booking.user.name}")
            else:
                pass
                # booking.reminder_sent = True
                # db.session.commit()

                # send_email(
                #     booking.user,
                #     "email/expiry_reminder",
                #     subject="Booking expiry reminder",
                #     slot=booking.slot,
                #     booking=booking,
                # )

        if today > booking.expiry:
            if dry_run:
                print(f"Delete booking {booking.description} with expiry {booking.expiry} from slot {booking.slot.name}. Booked by {booking.user.name}")
            else:
                pass
                # db.session.delete(booking)
                # db.session.commit()

                # send_email(
                #     booking.user,
                #     "email/expired",
                #     subject="Booking expired",
                #     slot=booking.slot,
                #     booking=booking
                # )