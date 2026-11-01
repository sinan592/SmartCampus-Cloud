
from datetime import datetime
from models.user import db


class Lesson(db.Model):

    __tablename__ = "lessons"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False
    )

    # Connect Lesson with its Course
    course = db.relationship(
        "Course",
        backref="lessons"
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    video_url = db.Column(
        db.String(500),
        nullable=True
    )

    lesson_order = db.Column(
        db.Integer,
        default=1
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Lesson {self.title}>"
