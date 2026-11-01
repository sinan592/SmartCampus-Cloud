
from datetime import datetime

from models.user import db


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    course_name = db.Column(
        db.String(150),
        nullable=False
    )

    enrolled_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "course_name",
            name="unique_user_course"
        ),
    )
