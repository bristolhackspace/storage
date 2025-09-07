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


def try_make_booking(user: User, slot: Slot, description: str):
    can_book, reason = can_make_booking(user, slot)
    if not can_book:
        raise BookingError(reason)

    today = date.today()

    slot.bookings.append(Booking(
        user=user,
        expiry=today + timedelta(days=slot.area.category.initial_duration_days),
        description=description,
    ))

    db.session.commit()