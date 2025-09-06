from flask import Blueprint, render_template, request
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from hackspace_storage.extensions import db
from hackspace_storage.models import Area, User

bp = Blueprint("main", __name__, url_prefix="/")
user_id = 1

@bp.route("/")
def index():
    areaQuery = sa.select(Area).options(joinedload(Area.slots)).order_by(Area.name)
    areas = db.session.scalars(areaQuery).unique().all()

    loggedInUser = db.session.get(User, user_id)

    return render_template("main/index.html", areas=areas, loggedInUser=loggedInUser)

@bp.route("/new-booking")
def new_booking():
    slotID = request.args.get('bookslot', None)