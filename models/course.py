from datetime import datetime
from models.user import db


class Course(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), unique=True, nullable=False)

    description = db.Column(db.Text, nullable=False)

    duration = db.Column(db.String(50), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Course {self.name}>"