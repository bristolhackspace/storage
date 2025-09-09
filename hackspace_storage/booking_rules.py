from datetime import date, timedelta
from typing import Tuple

from hackspace_storage.extensions import db
from hackspace_storage.models import User, Slot, Booking

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


def try_make_booking(user: User, slot: Slot, description: str, remind_me: bool) -> Booking:
    can_book, reason = can_make_booking(user, slot)
    if not can_book:
        raise BookingError(reason)

    today = date.today()

    booking = Booking(
        user=user,
        expiry=today + timedelta(days=slot.area.category.initial_duration_days),
        description=description,
        remind_me=remind_me,
    )
    slot.bookings.append(booking)
    db.session.commit()

    return booking

def extend_booking(booking: Booking):
    category = booking.slot.area.category

    today = date.today()
    delta = booking.expiry - today

    extension_period = category.extension_period_days

    if delta.days >= extension_period:
        raise BookingError(f"Can only extend within the last {extension_period} days")

    booking.expiry += timedelta(days=category.extension_duration_days)
    booking.extensions += 1
    db.session.commit()