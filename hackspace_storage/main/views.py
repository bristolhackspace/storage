from datetime import timedelta, date
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, abort, current_app
import secrets
from flask_wtf import FlaskForm
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from wtforms import BooleanField, DateField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, InputRequired

from hackspace_storage.booking_rules import BookingError, try_make_booking, extend_booking
from hackspace_storage.mailer import send_email

from .forms import DeleteConfirmForm
from hackspace_storage.extensions import db
from hackspace_storage.login import login_required
from hackspace_storage.models import Area, Slot, User, Booking

bp = Blueprint("main", __name__, url_prefix="/")


@bp.route("/")
def index():
    area_query = sa.select(Area).join(Area.slots).order_by(Area.name, Slot.name)
    areas = db.session.scalars(area_query).unique().all()

    return render_template("main/index.html", areas=areas)

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(current_app.config["PORTAL_URL"])

@bp.route("/finish")
def finish():
    return render_template("main/close_page_restricted.html")

@bp.route("/slots/<int:slot_id>/book", methods=["GET", "POST"])
@login_required
def book_slot(slot_id: int):
    slot = db.get_or_404(Slot, slot_id)

    today = date.today()
    max_booking= today+timedelta(days=slot.area.category.initial_duration_days)


    class BookingForm(FlaskForm):
        description = TextAreaField(
            'Project description',
            validators=[DataRequired()],
            render_kw={"placeholder": "Brief description of project you are working on"}
        )
        expiry_date = DateField(
            "Expiry date",
            validators=[InputRequired()],
            render_kw={
                'min': (today+timedelta(days=1)).strftime("%Y-%m-%d"),
                'max': (max_booking).strftime("%Y-%m-%d"),
            }
        )

        def validate_expiry_date(self, field: DateField):
            selected: date = field.data  # pyright: ignore[reportAssignmentType]
            if selected < today+timedelta(days=1) or selected > max_booking:
                raise ValidationError("Expiry outside allowable range")

    form = BookingForm(expiry_date=max_booking)

    if form.validate_on_submit():
        try:
            booking = try_make_booking(
                g.user,
                slot,
                form.description.data or "",
                form.expiry_date.data, # pyright: ignore[reportArgumentType]
            )
            flash(f"Booking success", 'success')

            reminder_date = booking.expiry - timedelta(days=slot.area.category.extension_period_days)
            if reminder_date <= date.today():
                # If reminder date is in the past or today then skip sending it
                reminder_date = None
                booking.reminder_sent = True
                db.session.commit()

            send_email(
                g.user,
                "email/slot_booked",
                subject="Booking created",
                slot=slot,
                booking=booking,
                reminder_date=reminder_date
            )

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


@bp.route("/bookings/<int:booking_id>/free-email", methods=["GET", "POST"])
def free_booking_email(booking_id: int):
    booking = db.session.get(Booking, booking_id)

    if (not booking
        or not booking.secret
        or not secrets.compare_digest(booking.secret, request.args.get("token", ""))
        ):
        abort(403, description="Booking link expired or invalid.")

    form = DeleteConfirmForm()

    if form.validate_on_submit():
        db.session.delete(booking)
        db.session.commit()
        flash("Booking deleted", "success")
        return redirect(url_for(".finish"))

    return render_template("main/delete_booking_restricted.html", form=form, booking=booking)


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
