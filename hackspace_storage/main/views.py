from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from hackspace_storage.booking_rules import BookingError, try_make_booking, extend_booking

from .forms import BookingForm, DeleteConfirmForm
from hackspace_storage.extensions import db
from hackspace_storage.login import login_required
from hackspace_storage.models import Area, Slot, User, Booking

bp = Blueprint("main", __name__, url_prefix="/")


@bp.route("/")
def index():
    area_query = sa.select(Area).join(Area.slots).order_by(Area.name, Slot.name)
    areas = db.session.scalars(area_query).unique().all()

    return render_template("main/index.html", areas=areas)

@bp.route("/slots/<int:slot_id>/book", methods=["GET", "POST"])
@login_required
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

@bp.route("/bookings/<int:booking_id>/free", methods=["GET", "POST"])
@login_required
def free_booking(booking_id: int):
    booking = db.get_or_404(Booking, booking_id)
    if booking.user != g.user:
        abort(403)

    form = DeleteConfirmForm()

    if form.validate_on_submit():
        db.session.delete(booking)
        db.session.commit()
        flash("Booking deleted", "success")
        return redirect(url_for(".index"))

    return render_template("main/delete_booking.html", form=form, booking=booking)


@bp.route("/bookings/<int:booking_id>/extend")
@login_required
def extend(booking_id: int):
    booking = db.get_or_404(Booking, booking_id)
    if booking.user != g.user:
        abort(403)
    
    try:
        extend_booking(booking)
        flash("Extension success", 'success')
    except BookingError as ex:
        flash(ex.reason, 'error')
    return redirect(url_for('main.index'))


# This is just temporary to create a login session
@bp.route("/fake-login")
def fake_login():
    user = db.get_or_404(User, 1)
    session["_user_id"] = user.id
    g.user = user
    return redirect(url_for(".index"))