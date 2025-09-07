from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField
from wtforms.validators import DataRequired

from hackspace_storage.models import Slot, User

class BookingForm(FlaskForm):
    description = TextAreaField(
        'Project description',
        validators=[DataRequired()],
        render_kw={"placeholder": "Brief description of project you are working on"}
    )
    remind_me = BooleanField("Send email reminders", default=True)

class DeleteConfirmForm(FlaskForm):
    pass