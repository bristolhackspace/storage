from flask import Blueprint, render_template
import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from hackspace_storage.extensions import db
from hackspace_storage.models import Area

bp = Blueprint("main", __name__, url_prefix="/")

@bp.route("/")
def index():
    query = sa.select(Area).options(joinedload(Area.slots)).order_by(Area.name)

    areas = db.session.scalars(query).unique().all()
    return render_template("main/index.html", areas=areas)