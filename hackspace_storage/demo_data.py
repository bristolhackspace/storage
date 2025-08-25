from flask import Blueprint

from hackspace_storage.extensions import db
from hackspace_storage.models import Area, Slot

bp = Blueprint('demo', __name__, cli_group=None)


@bp.cli.command("make-demo-data")
def make_demo_data():
    db.drop_all()
    db.create_all()

    left_area = Area(name="Left")
    right_area = Area(name="Right")
    back_area = Area(name="Back")
    areas = [left_area, right_area, back_area]

    db.session.add_all(areas)

    for area in areas:
        for i in range(5):
            area.slots.append(Slot(
                name=f"{area.name[0]}{i:03}"
            ))

    db.session.commit()
