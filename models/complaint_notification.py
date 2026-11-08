
from datetime import datetime
from models.user import db


class ComplaintNotification(db.Model):
    __tablename__ = "complaint_notifications"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    complaint_id = db.Column(
        db.Integer,
        db.ForeignKey("complaints.id"),
        nullable=False
    )

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
