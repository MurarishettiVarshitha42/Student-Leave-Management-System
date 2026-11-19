import os
import sqlite3
from datetime import date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-for-local-demo")
DATABASE = os.path.join(app.root_path, "leave_management.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'faculty', 'admin')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(status IN ('Pending', 'Approved', 'Rejected', 'Cancelled')),
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS leave_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leave_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('Approved', 'Rejected')),
            comments TEXT DEFAULT '',
            reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(leave_id) REFERENCES leave_requests(id),
            FOREIGN KEY(faculty_id) REFERENCES users(id)
        );
    """)

    demo_users = [
        ("Aarav Student", "student@example.com", "Student123!", "student"),
        ("Priya Faculty", "faculty@example.com", "Faculty123!", "faculty"),
        ("System Admin", "admin@example.com", "Admin123!", "admin"),
    ]
    for name, email, password, role in demo_users:
        exists = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role),
            )
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "info")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return view(**kwargs)
        return wrapped_view
    return decorator


@app.context_processor
def inject_current_year():
    return {"current_year": date.today().year}


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        flash("Email or password is incorrect.", "error")

    return render_template("login.html")


# Student Registration
@app.route("/register", methods=["GET", "POST"])
def register():

    # If already logged in, go to dashboard
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate name
        if len(name) < 2 or len(name) > 100:
            flash("Name must contain 2 to 100 characters.", "error")
            return render_template("register.html")

        # Validate email
        if not email or "@" not in email or len(email) > 150:
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        # Validate password
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("register.html")

        # Confirm password
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            db = get_db()

            # Always create a student account.
            # The user cannot select their own role.
            db.execute(
                """INSERT INTO users
                (name, email, password_hash, role)
                VALUES (?, ?, ?, 'student')""",
                (name, email, generate_password_hash(password))
            )

            db.commit()

            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("This email is already registered. Please use another email.", "error")

    return render_template("register.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    role = session["role"]

    if role == "student":
        requests_list = db.execute(
            """SELECT * FROM leave_requests
               WHERE student_id = ?
               ORDER BY applied_at DESC, id DESC""",
            (session["user_id"],)
        ).fetchall()
        counts = {
            "total": len(requests_list),
            "pending": sum(1 for item in requests_list if item["status"] == "Pending"),
            "approved": sum(1 for item in requests_list if item["status"] == "Approved"),
            "rejected": sum(1 for item in requests_list if item["status"] == "Rejected"),
        }
        return render_template("student_dashboard.html", requests=requests_list, counts=counts)

    if role == "faculty":
        requests_list = db.execute(
            """SELECT lr.*, u.name AS student_name, u.email AS student_email
               FROM leave_requests lr
               JOIN users u ON u.id = lr.student_id
               WHERE lr.status = 'Pending'
               ORDER BY lr.applied_at ASC"""
        ).fetchall()
        all_counts = db.execute(
            """SELECT status, COUNT(*) AS total
               FROM leave_requests GROUP BY status"""
        ).fetchall()
        counts = {row["status"].lower(): row["total"] for row in all_counts}
        counts["pending"] = counts.get("pending", 0)
        counts["approved"] = counts.get("approved", 0)
        counts["rejected"] = counts.get("rejected", 0)
        counts["total"] = sum(counts.values())
        return render_template("faculty_dashboard.html", requests=requests_list, counts=counts)

    users = db.execute(
        "SELECT id, name, email, role, created_at FROM users ORDER BY role, name"
    ).fetchall()
    all_requests = db.execute(
        """SELECT lr.*, u.name AS student_name
           FROM leave_requests lr JOIN users u ON u.id = lr.student_id
           ORDER BY lr.applied_at DESC, lr.id DESC"""
    ).fetchall()
    role_counts = db.execute(
        "SELECT role, COUNT(*) AS total FROM users GROUP BY role"
    ).fetchall()
    leave_counts = db.execute(
        "SELECT status, COUNT(*) AS total FROM leave_requests GROUP BY status"
    ).fetchall()
    user_stats = {row["role"]: row["total"] for row in role_counts}
    leave_stats = {row["status"].lower(): row["total"] for row in leave_counts}
    counts = {
        "students": user_stats.get("student", 0),
        "faculty": user_stats.get("faculty", 0),
        "total": sum(row["total"] for row in leave_counts),
        "pending": leave_stats.get("pending", 0),
        "approved": leave_stats.get("approved", 0),
        "rejected": leave_stats.get("rejected", 0),
    }
    return render_template(
        "admin_dashboard.html", users=users, requests=all_requests, counts=counts
    )


@app.route("/apply", methods=["GET", "POST"])
@role_required("student")
def apply_leave():
    if request.method == "POST":
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        reason = request.form.get("reason", "").strip()

        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError:
            flash("Please enter valid start and end dates.", "error")
            return render_template("apply_leave.html")

        if end < start:
            flash("The end date cannot be before the start date.", "error")
            return render_template("apply_leave.html")
        if start < date.today():
            flash("The start date cannot be in the past.", "error")
            return render_template("apply_leave.html")
        if not reason or len(reason) < 5:
            flash("Please enter a reason with at least 5 characters.", "error")
            return render_template("apply_leave.html")
        if len(reason) > 500:
            flash("The reason must be 500 characters or fewer.", "error")
            return render_template("apply_leave.html")

        db = get_db()
        overlap = db.execute(
            """SELECT id FROM leave_requests
               WHERE student_id = ?
                 AND status IN ('Pending', 'Approved')
                 AND NOT (end_date < ? OR start_date > ?)""",
            (session["user_id"], start_date, end_date)
        ).fetchone()
        if overlap:
            flash("These dates overlap with an existing pending or approved request.", "error")
            return render_template("apply_leave.html")

        db.execute(
            """INSERT INTO leave_requests (student_id, start_date, end_date, reason)
               VALUES (?, ?, ?, ?)""",
            (session["user_id"], start_date, end_date, reason)
        )
        db.commit()
        flash("Your leave application has been submitted.", "success")
        return redirect(url_for("dashboard"))

    return render_template("apply_leave.html")


@app.route("/leave/<int:leave_id>/cancel", methods=["POST"])
@role_required("student")
def cancel_leave(leave_id):
    db = get_db()
    result = db.execute(
        """UPDATE leave_requests SET status = 'Cancelled'
           WHERE id = ? AND student_id = ? AND status = 'Pending'""",
        (leave_id, session["user_id"])
    )
    db.commit()
    if result.rowcount:
        flash("Pending leave application cancelled.", "success")
    else:
        flash("That request could not be cancelled. Only your pending requests can be cancelled.", "error")
    return redirect(url_for("dashboard"))


@app.route("/leave/<int:leave_id>/review", methods=["POST"])
@role_required("faculty", "admin")
def review_leave(leave_id):
    decision = request.form.get("decision", "")
    comments = request.form.get("comments", "").strip()
    if decision not in ("Approved", "Rejected"):
        flash("Please choose a valid decision.", "error")
        return redirect(url_for("dashboard"))
    if len(comments) > 500:
        flash("Comments must be 500 characters or fewer.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    leave = db.execute(
        "SELECT * FROM leave_requests WHERE id = ?", (leave_id,)
    ).fetchone()
    if leave is None or leave["status"] != "Pending":
        flash("This request no longer needs a review.", "error")
        return redirect(url_for("dashboard"))

    db.execute(
        "UPDATE leave_requests SET status = ? WHERE id = ? AND status = 'Pending'",
        (decision, leave_id)
    )
    db.execute(
        """INSERT INTO leave_reviews (leave_id, faculty_id, decision, comments)
           VALUES (?, ?, ?, ?)""",
        (leave_id, session["user_id"], decision, comments)
    )
    db.commit()
    flash(f"Leave request {decision.lower()}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/users", methods=["POST"])
@role_required("admin")
def create_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    if not name or not email or len(password) < 8 or role not in ("student", "faculty", "admin"):
        flash("Enter a name, valid email, password of at least 8 characters, and valid role.", "error")
        return redirect(url_for("dashboard"))

    try:
        get_db().execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), role)
        )
        get_db().commit()
        flash("User account created successfully.", "success")
    except sqlite3.IntegrityError:
        flash("That email address is already registered.", "error")
    return redirect(url_for("dashboard"))


@app.route("/admin/leave/<int:leave_id>/review", methods=["POST"])
@role_required("admin")
def admin_review_leave(leave_id):
    # Reuse the same review logic while preserving the admin-only URL.
    return review_leave.__wrapped__(leave_id=leave_id)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
