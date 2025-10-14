
from collections import defaultdict
import datetime
from typing import Any, Optional
from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, expression
from sqlalchemy.sql.functions import current_date
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
    current_booking_id: Mapped[Optional[int]] = mapped_column(ForeignKey("booking.id"))

    area: Mapped["Area"] = relationship(back_populates="slots")

    current_booking: Mapped[Optional["Booking"]] = relationship(back_populates="slot")

    @hybrid_property
    def has_active_booking(self):
        return self.current_booking and self.current_booking.is_active
    
    @has_active_booking.inplace.expression
    def _has_active_booking(cls):
        return expression.and_(Slot.current_booking!=None, Slot.current_booking.is_active==True)

class Booking(PkModel):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created: Mapped[datetime.date] = mapped_column(server_default=current_date())
    expiry: Mapped[datetime.date]
    extensions: Mapped[int] = mapped_column(server_default="0")
    description: Mapped[str]
    reminder_sent: Mapped[bool] = mapped_column(server_default=expression.false())
    secret: Mapped[Optional[str]]

    slot: Mapped[Optional["Slot"]] = relationship(back_populates="current_booking", uselist=False)
    user: Mapped["User"] = relationship(back_populates="bookings")

    @hybrid_property
    def is_active(self):
        return datetime.date.today() < self.expiry
    
    @is_active.inplace.expression
    @classmethod
    def _is_active(cls):
        return current_date() < cls.expiry