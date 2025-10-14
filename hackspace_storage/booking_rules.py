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
    """Try to book a slot. The slot must be obtained using the with_for_update option"""
    can_book, reason = can_make_booking(user, slot)
    if not can_book:
        raise BookingError(reason)
    
    now = date.today()

    booking_secret = generate_token()

    slot.booked_by=user
    slot.booking_secret=booking_secret
    slot.booked_at=now
    slot.booking_expiry=expiry
    slot.contents_description=description
    slot.reminder_email_sent=False
    slot.expiry_email_sent=False


def can_extend_booking(slot: Slot, user: User):
    if slot.booked_by != user:
        return False, "Cannot extend booking. Slot is now booked by someone else."

    category = slot.area.category

    today = date.today()
    delta = slot.booking_expiry - today

    extension_period = category.extension_period_days

    if delta.days >= extension_period:
        return False, f"Can only extend within the last {extension_period} days"
    return True, ""


def extend_booking(slot: Slot, user: User):
    """Try to extend a booking. The slot must be obtained using the with_for_update option"""
    can_extend, reason = can_extend_booking(slot, user)
    if not can_extend:
        raise BookingError(reason)
    
    category = slot.area.category

    slot.booking_expiry += timedelta(days=category.extension_duration_days)