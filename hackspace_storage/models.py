
import datetime
from typing import Any, Optional
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


from hackspace_storage.database import PkModel
from hackspace_storage.extensions import db

class User(PkModel):
    sub: Mapped[str] = mapped_column(unique=True, index=True) # ID will be obtained from the subject claim in the login token
    email: Mapped[str]
    name: Mapped[str]

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")

class Area(PkModel):
    name: Mapped[str]

    slots: Mapped[list["Slot"]] = relationship(back_populates="area")

class Slot(PkModel):
    name: Mapped[str]
    area_id: Mapped[int] = mapped_column(ForeignKey("area.id"))

    area: Mapped["Area"] = relationship(back_populates="slots")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="slot")

class Booking(PkModel):
    slot_id: Mapped[int] = mapped_column(ForeignKey("slot.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    expiry: Mapped[datetime.date]
    description: Mapped[str]

    slot: Mapped["Slot"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship(back_populates="bookings")