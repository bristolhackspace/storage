
from collections import defaultdict
import datetime
from typing import Any, Optional
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, expression
from uuid import UUID

from hackspace_storage.database import PkModel, Model, UTCDateTime
from hackspace_storage.database import db

class User(PkModel):
    sub: Mapped[str] = mapped_column(unique=True, index=True) # ID will be obtained from the subject claim in the login token
    email: Mapped[str]
    name: Mapped[str]

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    logins: Mapped[list["Login"]] = relationship(back_populates="user")

    def bookings_per_category(self) -> defaultdict["Category", int]:
        counts = defaultdict(int)
        for booking in self.bookings:
            counts[booking.slot.area.category] += 1
        return counts
    
# Calling this a Login instead of Session to avoid confusion with Flask's own session API
class Login(Model):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    external_id: Mapped[Optional[str]] = mapped_column(unique=True, index=True) # Obtained from the sid claim in the login token
    # We don't just rely on the id as UUID generation isn't guaranteed to use a CSPRNG
    secret: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created: Mapped[datetime.datetime] = mapped_column(UTCDateTime())
    expiry: Mapped[datetime.datetime] = mapped_column(UTCDateTime())

    user: Mapped["User"] = relationship(back_populates="logins")

class Category(PkModel):
    name: Mapped[str]
    max_bookings: Mapped[int]
    initial_duration_days: Mapped[int]
    extension_duration_days: Mapped[int]
    extension_period_days: Mapped[int]
    max_extensions: Mapped[int]

    areas: Mapped[list["Area"]] = relationship(back_populates="category")

class Area(PkModel):
    name: Mapped[str]
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    column_count: Mapped[int]

    slots: Mapped[list["Slot"]] = relationship(back_populates="area", order_by="Slot.name")
    category: Mapped["Category"] = relationship(back_populates="areas")

class Slot(PkModel):
    name: Mapped[str]
    area_id: Mapped[int] = mapped_column(ForeignKey("area.id"))

    area: Mapped["Area"] = relationship(back_populates="slots")
    # Data model allows multiple bookings, howeve application will restrict this
    bookings: Mapped[list["Booking"]] = relationship(back_populates="slot")

class Booking(PkModel):
    slot_id: Mapped[int] = mapped_column(ForeignKey("slot.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    expiry: Mapped[datetime.date]
    extensions: Mapped[int] = mapped_column(server_default="0")
    description: Mapped[str]
    reminder_sent: Mapped[bool] = mapped_column(server_default=expression.false())
    secret: Mapped[Optional[str]]

    slot: Mapped["Slot"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship(back_populates="bookings")