from datetime import date, timedelta
from typing import Tuple

from flask import Flask

from hackspace_storage.extensions import db
from hackspace_storage.models import User, Slot, Booking
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
    if len(slot.bookings) > 0:
        return False, "slot already booked"
    category = slot.area.category
    if user.bookings_per_category()[category] >= category.max_bookings:
        return False, "Maximum allowed bookings used"
    return True, ""


def try_make_booking(user: User, slot: Slot, description: str, expiry: date) -> Booking:
    can_book, reason = can_make_booking(user, slot)
    if not can_book:
        raise BookingError(reason)

    booking = Booking(
        user=user,
        expiry=expiry,
        description=description,
        secret=generate_token()
    )
    slot.bookings.append(booking)
    db.session.commit()

    return booking

def can_extend_booking(booking: Booking):
    category = booking.slot.area.category

    today = date.today()
    delta = booking.expiry - today

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