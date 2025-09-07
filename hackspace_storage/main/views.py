from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from hackspace_storage.booking_rules import BookingError, try_make_booking

from .forms import BookingForm
from hackspace_storage.extensions import db
from hackspace_storage.models import Area, Slot, User

bp = Blueprint("main", __name__, url_prefix="/")
user_id = 1

@bp.route("/")
def index():
    area_query = sa.select(Area).options(joinedload(Area.slots)).order_by(Area.name)
    areas = db.session.scalars(area_query).unique().all()

    return render_template("main/index.html", areas=areas)

@bp.route("/slots/<int:slot_id>/book", methods=["GET", "POST"])
def book_slot(slot_id: int):
    slot = db.get_or_404(Slot, slot_id)

    form = BookingForm()

    if form.validate_on_submit():
        try:
            try_make_booking(g.user, slot, form.description.data) # pyright: ignore[reportArgumentType]
            flash(f"Booking success", 'success')
            return redirect(url_for('.index'))
        except BookingError as ex:
            flash(f"Unable to make booking: {ex.reason}", 'error')

    return render_template("main/book_slot.html", form=form, slot=slot)

# This is just temporary to create a login session
@bp.route("/fake-login")
def fake_login():
    user = db.get_or_404(User, 1)
    session["_user_id"] = user.id
    g.user = user
    return redirect(url_for(".index"))