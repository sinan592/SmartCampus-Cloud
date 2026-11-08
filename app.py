from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)

from models.user import db, User
from models.course import Course
from models.enrollment import Enrollment
from models.lesson import Lesson
from models.event import Event
from models.document import Document
from models.notification import Notification
from models.complaint import Complaint
from models.complaint_notification import ComplaintNotification

app = Flask(__name__)

# ---------------- CONFIGURATION ----------------
app.config["SECRET_KEY"] = "smartcampus-study-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smartcampus.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path, "static", "uploads", "documents"
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx"}

db.init_app(app)

# Create missing database tables
with app.app_context():
    db.create_all()


# ---------------- LOGIN MANAGER ----------------
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------- ADMIN ACCESS CONTROL ----------------
def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):

        if current_user.role != "admin":
            flash("Access denied! Admin only.", "error")
            return redirect(url_for("dashboard"))

        return func(*args, **kwargs)

    return wrapper


# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER PAGE ----------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash(
                "Enter your name and email. "
                "Password must be at least 8 characters."
            )
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("This email is already registered. Please sign in.")
            return redirect(url_for("login"))

        user = User(name=name, email=email)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Account created successfully!")

            return redirect(url_for("dashboard"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Registration failed")
            flash("Registration failed. Please try again.")
            return redirect(url_for("register"))

    return render_template("register.html")


# ---------------- SIGN IN PAGE ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            login_user(user)
            flash("Sign in successful!")

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        flash("Email or password is incorrect.")
        return redirect(url_for("login"))

    return render_template("login.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    # Get student's enrolled courses
    enrollments = Enrollment.query.filter_by(
        user_id=current_user.id
    ).all()

    enrolled_names = [
        enrollment.course_name
        for enrollment in enrollments
    ]

    # Find matching courses
    enrolled_courses = Course.query.filter(
        Course.name.in_(enrolled_names)
    ).all() if enrolled_names else []

    # Count lessons
    course_ids = [
        course.id for course in enrolled_courses
    ]

    total_lessons = Lesson.query.filter(
        Lesson.course_id.in_(course_ids)
    ).count() if course_ids else 0

    # Count uploaded documents
    total_documents = Document.query.count()

    # Count campus events
    total_events = Event.query.count()

    return render_template(
        "dashboard.html",
        user=current_user,
        total_courses=len(enrollments),
        total_lessons=total_lessons,
        total_events=total_events,
        total_documents=total_documents,
        total_notifications=Notification.query.count()
    )


# ---------------- STUDENT COURSES PAGE ----------------
@app.route("/courses")
@login_required
def courses():

    # Get all courses added by Admin from database
    course_list = Course.query.order_by(
        Course.created_at.desc()
    ).all()

    return render_template(
        "courses.html",
        courses=course_list,
        user=current_user
    )



# ---------------- ENROLL IN A COURSE ----------------
@app.route("/enroll/<course_name>", methods=["POST"])
@login_required
def enroll(course_name):

    existing = Enrollment.query.filter_by(
        user_id=current_user.id,
        course_name=course_name
    ).first()

    if existing:
        flash("You are already enrolled in this course.")

    else:
        try:
            enrollment = Enrollment(
                user_id=current_user.id,
                course_name=course_name
            )

            db.session.add(enrollment)
            db.session.commit()

            flash(f"Successfully enrolled in {course_name}!")

        except Exception:
            db.session.rollback()
            app.logger.exception("Enrollment failed")
            flash("Enrollment failed. Please try again.")

    return redirect(url_for("my_courses"))


# ---------------- MY ENROLLED COURSES ----------------
@app.route("/my-courses")
@login_required
def my_courses():

    enrolled_courses = Enrollment.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Enrollment.enrolled_at.desc()
    ).all()

    course_list = Course.query.all()

    return render_template(
        "my_courses.html",
        enrollments=enrolled_courses,
        courses=course_list,
        user=current_user
    )


# ---------------- STUDENT COURSE LESSONS ----------------
@app.route("/my-courses/<int:course_id>/lessons")
@login_required
def student_lessons(course_id):

    course = Course.query.get_or_404(course_id)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        course_name=course.name
    ).first()

    if not enrollment:
        flash("You are not enrolled in this course.", "error")
        return redirect(url_for("my_courses"))

    lessons = Lesson.query.filter_by(
        course_id=course.id
    ).order_by(
        Lesson.lesson_order.asc()
    ).all()

    return render_template(
        "student_lessons.html",
        course=course,
        lessons=lessons,
        user=current_user
    )


# ---------------- UNENROLL FROM A COURSE ----------------
@app.route("/unenroll/<int:enrollment_id>", methods=["POST"])
@login_required
def unenroll(enrollment_id):

    enrollment = Enrollment.query.filter_by(
        id=enrollment_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(enrollment)
    db.session.commit()

    flash(f"You have unenrolled from {enrollment.course_name}.")

    return redirect(url_for("my_courses"))

# ---------------- STUDENT CAMPUS EVENTS ----------------

@app.route("/events")
@login_required
def events():

    event_list = Event.query.order_by(
        Event.date.asc()
    ).all()

    return render_template(
        "events.html",
        events=event_list,
        user=current_user
    )


# ---------------- STUDENT DOCUMENTS PAGE ----------------

@app.route("/documents")
@login_required
def documents():

    documents_list = Document.query.order_by(
        Document.uploaded_at.desc()
    ).all()

    return render_template(
        "documents.html",
        user=current_user,
        documents=documents_list
    )


# ---------------- DOWNLOAD DOCUMENT ----------------

@app.route("/documents/download/<int:document_id>")
@login_required
def download_document(document_id):

    document = Document.query.get_or_404(document_id)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        document.filename,
        as_attachment=True
    )



# ---------------- NOTIFICATIONS PAGE ----------------

@app.route("/notifications")
@login_required
def notifications():

    notification_list = Notification.query.order_by(
        Notification.created_at.desc()
    ).all()

    return render_template(
        "notifications.html",
        notifications=notification_list,
        user=current_user
    )

    # ---------------- STUDENT COMPLAINTS ----------------

@app.route("/complaints", methods=["GET", "POST"])
@login_required
def complaints():

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not subject or not category or not description:
            flash("Please fill in all complaint details.", "error")
            return redirect(url_for("complaints"))

        try:
            complaint = Complaint(
                student_id=current_user.id,
                subject=subject,
                category=category,
                description=description
            )

            db.session.add(complaint)
            db.session.commit()

            flash("Complaint submitted successfully!", "success")

        except Exception:
            db.session.rollback()
            app.logger.exception("Complaint submission failed")
            flash("Complaint could not be submitted.", "error")

        return redirect(url_for("complaints"))

    # Get complaints submitted by the logged-in student
    complaint_list = Complaint.query.filter_by(
        student_id=current_user.id
    ).order_by(
        Complaint.created_at.desc()
    ).all()

    return render_template(
        "complaints.html",
        complaints=complaint_list
    )


# ---------------- STUDENT COMPLAINT NOTIFICATIONS ----------------

@app.route("/complaint-notifications")
@login_required
def complaint_notifications():

    notifications = ComplaintNotification.query.filter_by(
        student_id=current_user.id
    ).order_by(
        ComplaintNotification.created_at.desc()
    ).all()

    return render_template(
        "complaint_notifications.html",
        notifications=notifications
    )

# ---------------- STUDENT PROFILE PAGE ----------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        roll_number = request.form.get("roll_number", "").strip()

        if not name:
            flash("Name cannot be empty.")
            return redirect(url_for("profile"))

        try:
            current_user.name = name
            current_user.phone = phone or None
            current_user.department = department or None
            current_user.roll_number = roll_number or None

            db.session.commit()

            flash("Profile updated successfully!", "success")

        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to update profile")
            flash("Profile could not be saved. Check the Flask terminal.", "error")

        return redirect(url_for("profile"))

    return render_template(
        "profile.html",
        user=current_user
    )

# ---------------- ADMIN COMPLAINT MANAGEMENT ----------------

@app.route("/admin/complaints")
@admin_required
def admin_complaints():

    complaint_list = Complaint.query.order_by(
        Complaint.created_at.desc()
    ).all()

    return render_template(
        "admin_complaints.html",
        complaints=complaint_list
    )



@app.route("/admin/complaints/update/<int:complaint_id>",
           methods=["POST"])
@admin_required
def update_complaint(complaint_id):

    complaint = Complaint.query.get_or_404(complaint_id)

    old_status = complaint.status
    status = request.form.get("status", "").strip()
    response = request.form.get("admin_response", "").strip()

    allowed_statuses = ["Pending", "In Progress", "Resolved"]

    if status not in allowed_statuses:
        flash("Invalid complaint status.", "error")
        return redirect(url_for("admin_complaints"))

    try:
        complaint.status = status
        complaint.admin_response = response or None

        # Create notification only when status changes
        if old_status != status:
            notification = ComplaintNotification(
                student_id=complaint.student_id,
                complaint_id=complaint.id,
                title="Complaint Status Updated",
                message=(
                    f"Your complaint '{complaint.subject}' "
                    f"status changed from {old_status} to {status}."
                )
            )
            db.session.add(notification)

        db.session.commit()
        flash("Complaint updated successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Complaint update failed")
        flash("Could not update complaint.", "error")

    return redirect(url_for("admin_complaints"))




# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@admin_required
def admin_dashboard():

    total_students = User.query.filter_by(
        role="student"
    ).count()

    total_enrollments = Enrollment.query.count()

    course_list = Course.query.order_by(
        Course.created_at.desc()
    ).all()

    total_courses = len(course_list)

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_enrollments=total_enrollments,
        total_courses=total_courses,
        courses=course_list
    )


# ---------------- ADMIN STUDENT MANAGEMENT ----------------
@app.route("/admin/students")
@admin_required
def admin_students():

    students = User.query.filter_by(role="student").all()

    return render_template(
        "admin_students.html",
        students=students
    )

# ---------------- DELETE STUDENT ----------------

@app.route("/admin/students/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):

    student = User.query.filter_by(
        id=student_id,
        role="student"
    ).first_or_404()

    try:
        # Delete the student's enrollment records first
        Enrollment.query.filter_by(
            user_id=student.id
        ).delete(synchronize_session=False)

        # Delete the student account
        db.session.delete(student)
        db.session.commit()

        flash("Student account deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Student deletion failed")
        flash("Student could not be deleted. Please try again.", "error")

    return redirect(url_for("admin_students"))


# ---------------- ADD NEW COURSE ----------------
@app.route("/admin/courses/add", methods=["GET", "POST"])
@admin_required
def add_course():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        duration = request.form.get("duration", "").strip()

        if not name or not description or not duration:
            flash("All fields are required!", "error")
            return redirect(url_for("add_course"))

        existing_course = Course.query.filter_by(
            name=name
        ).first()

        if existing_course:
            flash("Course already exists!", "error")
            return redirect(url_for("add_course"))

        try:
            new_course = Course(
                name=name,
                description=description,
                duration=duration
            )

            db.session.add(new_course)
            db.session.commit()

            flash("Course added successfully!", "success")

            return redirect(url_for("admin_courses"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Course creation failed")

            flash(
                "Course could not be saved. Check the Flask terminal.",
                "error"
            )

            return redirect(url_for("add_course"))

    return render_template("add_course.html")

# ---------------- EDIT COURSE ----------------
@app.route("/admin/courses/edit/<int:course_id>", methods=["GET", "POST"])
@admin_required
def edit_course(course_id):

    course = Course.query.get_or_404(course_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        duration = request.form.get("duration", "").strip()

        if not name or not description or not duration:
            flash("All fields are required!", "error")
            return redirect(url_for("edit_course", course_id=course.id))

        existing_course = Course.query.filter(
            Course.name == name,
            Course.id != course.id
        ).first()

        if existing_course:
            flash("Another course already uses this name.", "error")
            return redirect(url_for("edit_course", course_id=course.id))

        try:
            course.name = name
            course.description = description
            course.duration = duration

            db.session.commit()

            flash("Course updated successfully!", "success")
            return redirect(url_for("admin_courses"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Course update failed")
            flash("Course update failed. Please try again.", "error")
            return redirect(url_for("edit_course", course_id=course.id))

    return render_template(
        "edit_course.html",
        course=course
    )


# ---------------- DELETE COURSE ----------------
@app.route("/admin/courses/delete/<int:course_id>", methods=["POST"])
@admin_required
def delete_course(course_id):

    course = Course.query.get_or_404(course_id)

    try:
        db.session.delete(course)
        db.session.commit()

        flash("Course deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Course deletion failed")
        flash("Cannot delete this course. Check its enrollment records.", "error")

    return redirect(url_for("admin_courses"))


# ---------------- ADMIN LESSON MANAGEMENT ----------------

@app.route("/admin/lessons")
@admin_required
def admin_lessons():

    lessons = Lesson.query.order_by(
        Lesson.created_at.desc()
    ).all()

    courses = Course.query.order_by(
        Course.name.asc()
    ).all()

    return render_template(
        "admin_lessons.html",
        lessons=lessons,
        courses=courses
    )


# ---------------- ADD LESSON ----------------

@app.route("/admin/lessons/add", methods=["GET", "POST"])
@admin_required
def add_lesson():

    courses = Course.query.order_by(Course.name.asc()).all()

    if request.method == "POST":

        course_id = request.form.get("course_id", type=int)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        video_url = request.form.get("video_url", "").strip()
        lesson_order = request.form.get("lesson_order", 1, type=int)

        course = db.session.get(Course, course_id) if course_id else None

        if not course or not title:
            flash("Please select a course and enter a lesson title.", "error")
            return redirect(url_for("add_lesson"))

        if lesson_order < 1:
            flash("Lesson order must be at least 1.", "error")
            return redirect(url_for("add_lesson"))

        try:
            lesson = Lesson(
                course_id=course.id,
                title=title,
                description=description,
                video_url=video_url,
                lesson_order=lesson_order
            )

            db.session.add(lesson)
            db.session.commit()

            flash("Lesson added successfully!", "success")
            return redirect(url_for("admin_lessons"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Lesson creation failed")
            flash("Lesson could not be added.", "error")
            return redirect(url_for("add_lesson"))

    return render_template(
        "add_lesson.html",
        courses=courses
    )


# ---------------- EDIT LESSON ----------------

@app.route("/admin/lessons/edit/<int:lesson_id>", methods=["GET", "POST"])
@admin_required
def edit_lesson(lesson_id):

    lesson = Lesson.query.get_or_404(lesson_id)

    courses = Course.query.order_by(Course.name.asc()).all()

    if request.method == "POST":

        course_id = request.form.get("course_id", type=int)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        video_url = request.form.get("video_url", "").strip()
        lesson_order = request.form.get("lesson_order", 1, type=int)

        course = db.session.get(Course, course_id) if course_id else None

        if not course or not title or lesson_order < 1:
            flash("Please enter valid lesson details.", "error")
            return redirect(url_for("edit_lesson", lesson_id=lesson.id))

        try:
            lesson.course_id = course.id
            lesson.title = title
            lesson.description = description
            lesson.video_url = video_url
            lesson.lesson_order = lesson_order

            db.session.commit()

            flash("Lesson updated successfully!", "success")
            return redirect(url_for("admin_lessons"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Lesson update failed")
            flash("Lesson update failed.", "error")
            return redirect(url_for("edit_lesson", lesson_id=lesson.id))

    return render_template(
        "edit_lesson.html",
        lesson=lesson,
        courses=courses
    )


# ---------------- DELETE LESSON ----------------

@app.route("/admin/lessons/delete/<int:lesson_id>", methods=["POST"])
@admin_required
def delete_lesson(lesson_id):

    lesson = Lesson.query.get_or_404(lesson_id)

    try:
        db.session.delete(lesson)
        db.session.commit()

        flash("Lesson deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Lesson deletion failed")
        flash("Lesson could not be deleted.", "error")

    return redirect(url_for("admin_lessons"))




# ---------------- ADMIN COURSE MANAGEMENT ----------------
@app.route("/admin/courses")
@admin_required
def admin_courses():

    # Get courses from SQLite database
    course_list = Course.query.order_by(
        Course.created_at.desc()
    ).all()

    return render_template(
        "admin_courses.html",
        courses=course_list
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been signed out.")

    return redirect(url_for("home"))



# ---------------- ADMIN NOTIFICATION MANAGEMENT ----------------

# ADD AND VIEW NOTIFICATIONS
@app.route("/admin/notifications", methods=["GET", "POST"])
@admin_required
def admin_notifications():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()

        if not title or not message:
            flash("Please enter notification title and message.", "error")
            return redirect(url_for("admin_notifications"))

        try:
            new_notification = Notification(
                title=title,
                message=message
            )

            db.session.add(new_notification)
            db.session.commit()

            flash("Notification added successfully!", "success")

        except Exception:
            db.session.rollback()
            app.logger.exception("Notification creation failed")
            flash("Notification could not be added.", "error")

        return redirect(url_for("admin_notifications"))

    notifications = Notification.query.order_by(
        Notification.created_at.desc()
    ).all()

    return render_template(
        "admin_notifications.html",
        notifications=notifications
    )


# EDIT NOTIFICATION
@app.route("/admin/notifications/edit/<int:notification_id>",
           methods=["GET", "POST"])
@admin_required
def edit_notification(notification_id):

    notification = Notification.query.get_or_404(notification_id)

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()

        if not title or not message:
            flash("Title and message are required.", "error")
            return redirect(
                url_for("edit_notification",
                        notification_id=notification.id)
            )

        try:
            notification.title = title
            notification.message = message

            db.session.commit()

            flash("Notification updated successfully!", "success")
            return redirect(url_for("admin_notifications"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Notification update failed")
            flash("Notification update failed.", "error")

    return render_template(
        "edit_notification.html",
        notification=notification
    )


# DELETE NOTIFICATION
@app.route("/admin/notifications/delete/<int:notification_id>",
           methods=["POST"])
@admin_required
def delete_notification(notification_id):

    notification = Notification.query.get_or_404(notification_id)

    try:
        db.session.delete(notification)
        db.session.commit()

        flash("Notification deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Notification deletion failed")
        flash("Notification could not be deleted.", "error")

    return redirect(url_for("admin_notifications"))


# ---------------- ADMIN DOCUMENT UPLOAD ----------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/admin/documents", methods=["GET", "POST"])
@admin_required
def admin_documents():

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("document")

        if not title or not file or not file.filename:
            flash("Please enter a title and select a document.", "error")
            return redirect(url_for("admin_documents"))

        if not allowed_file(file.filename):
            flash("Only PDF, DOC, DOCX, PPT and PPTX files are allowed.", "error")
            return redirect(url_for("admin_documents"))

        filename = secure_filename(file.filename)

        # Avoid overwriting an existing file
        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))

        try:
            new_document = Document(
                title=title,
                description=description,
                filename=unique_filename
            )

            db.session.add(new_document)
            db.session.commit()

            flash("Document uploaded successfully!", "success")

        except Exception:
            db.session.rollback()
            app.logger.exception("Document upload failed")
            flash("Document could not be uploaded.", "error")

        return redirect(url_for("admin_documents"))

    documents = Document.query.order_by(
        Document.uploaded_at.desc()
    ).all()

    return render_template(
        "admin_documents.html",
        documents=documents
    )


# ---------------- EDIT DOCUMENT ----------------


@app.route("/admin/documents/edit/<int:document_id>",
           methods=["GET", "POST"])
@admin_required
def edit_document(document_id):

    document = Document.query.get_or_404(document_id)

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("document")

        if not title:
            flash("Document title is required.", "error")
            return redirect(url_for("edit_document", document_id=document.id))

        try:
            document.title = title
            document.description = description

            # Replace file only if a new file is selected
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash("Invalid file type.", "error")
                    return redirect(url_for(
                        "edit_document",
                        document_id=document.id
                    ))

                filename = secure_filename(file.filename)
                unique_filename = (
                    f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
                )

                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

                file.save(os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    unique_filename
                ))

                old_file_path = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    document.filename
                )

                document.filename = unique_filename

            db.session.commit()

            if file and file.filename and os.path.isfile(old_file_path):
                os.remove(old_file_path)

            flash("Document updated successfully!", "success")
            return redirect(url_for("admin_documents"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Document update failed")
            flash("Document update failed.", "error")

    return render_template("edit_document.html", document=document)



# ---------------- DELETE DOCUMENT ----------------

@app.route("/admin/documents/delete/<int:document_id>",
           methods=["POST"])
@admin_required
def delete_document(document_id):

    document = Document.query.get_or_404(document_id)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        document.filename
    )

    try:
        if os.path.isfile(file_path):
            os.remove(file_path)

        db.session.delete(document)
        db.session.commit()

        flash("Document deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Document deletion failed")
        flash("Document could not be deleted.", "error")

    return redirect(url_for("admin_documents"))




# ---------------- ADMIN EVENT MANAGEMENT ----------------

@app.route("/admin/events")
@admin_required
def admin_events():

    events = Event.query.order_by(
        Event.date.asc()
    ).all()

    return render_template(
        "admin_events.html",
        events=events
    )


# ---------------- ADD NEW EVENT ----------------

@app.route("/admin/events/add", methods=["GET", "POST"])
@admin_required
def add_event():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        date_value = request.form.get("date", "").strip()
        location = request.form.get("location", "").strip()

        if not name or not description or not date_value or not location:
            flash("Please fill in all event details.", "error")
            return redirect(url_for("add_event"))

        try:
            event_date = datetime.strptime(
                date_value, "%Y-%m-%d"
            ).date()

            new_event = Event(
                name=name,
                description=description,
                date=event_date,
                location=location
            )

            db.session.add(new_event)
            db.session.commit()

            flash("Event added successfully!", "success")
            return redirect(url_for("admin_events"))

        except ValueError:
            flash("Invalid event date.", "error")
            return redirect(url_for("add_event"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Event creation failed")
            flash("Event could not be added.", "error")
            return redirect(url_for("add_event"))

    return render_template("add_event.html")

# ---------------- EDIT CAMPUS EVENT ----------------

@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):

    event = Event.query.get_or_404(event_id)

    if request.method == "POST":

        event.name = request.form.get("name", "").strip()
        event.description = request.form.get("description", "").strip()
        event.location = request.form.get("location", "").strip()

        date_value = request.form.get("date", "").strip()

        if not event.name or not event.description or not event.location or not date_value:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("edit_event", event_id=event.id))

        try:
            event.date = datetime.strptime(
                date_value, "%Y-%m-%d"
            ).date()

            db.session.commit()

            flash("Event updated successfully!", "success")
            return redirect(url_for("admin_events"))

        except ValueError:
            flash("Invalid date.", "error")
            return redirect(url_for("edit_event", event_id=event.id))

    return render_template("edit_event.html", event=event)


# ---------------- DELETE CAMPUS EVENT ----------------

@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):

    event = Event.query.get_or_404(event_id)

    db.session.delete(event)
    db.session.commit()

    flash("Event deleted successfully!", "success")

    return redirect(url_for("admin_events"))


# ---------------- RUN APPLICATION ----------------
if __name__ == "__main__":
    app.run(debug=True)
