from datetime import datetime
from models.user import db


class Event(db.Model):

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    location = db.Column(
        db.String(200),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Event {self.name}>"