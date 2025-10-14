from datetime import date, timedelta
from flask import Flask
import sqlalchemy as sa
from typing import Tuple

from hackspace_storage.database import db
from hackspace_storage.models import User, Slot
from hackspace_storage.token import generate_token


def init_app(app: Flask):
    @app.context_processor
    def booking_helpers():
        return dict(
            can_make_booking=can_make_booking,
            can_extend_booking=can_extend_booking,
        )

class BookingError(Exception):
    def __init__(self, reason):
        self.reason = reason


def can_make_booking(user: User, slot: Slot) -> Tuple[bool, str]:
    if slot.has_booking:
        return False, "slot already booked"
    category = slot.area.category
    if user.bookings_per_category()[category] >= category.max_bookings:
        return False, "Maximum allowed bookings used"
    #TODO: Add check for re-booking within cool-off period
    return True, ""


def try_make_booking(user: User, slot: Slot, description: str, expiry: date):
    can_book, reason = can_make_booking(user, slot)
    if not can_book:
        raise BookingError(reason)
    
    now = date.today()

    booking_secret = generate_token()

    # We do an extra has_booking check to avoid any theoretical race conditions if somebody else booked in the meantime
    stmt = sa.update(Slot).where(Slot.id==slot.id, Slot.has_booking==False).values(
        booked_by=user,
        booking_secret=booking_secret,
        booked_at=now,
        booking_expiry=expiry,
        contents_description=description,
        reminder_email_sent=False,
        expiry_email_sent=False,
    )

    db.session.execute(stmt)
    db.session.commit()

    # If a race condition happened then the slot won't get updated
    if slot.booking_secret != booking_secret:
        raise BookingError("slot already booked")


def can_extend_booking(slot: Slot):
    category = slot.area.category

    today = date.today()
    delta = slot.booking_expiry - today

    extension_period = category.extension_period_days

    if delta.days >= extension_period:
        return False, f"Can only extend within the last {extension_period} days"
    return True, ""


def extend_booking(booking: Booking):
    can_extend, reason = can_extend_booking(booking)
    if not can_extend:
        raise BookingError(reason)

    category = booking.slot.area.category

    booking.expiry += timedelta(days=category.extension_duration_days)
    booking.extensions += 1
    db.session.commit()