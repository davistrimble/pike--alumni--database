import hmac
import os
import secrets
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import members
import tracking
from search import search_it

load_dotenv()

MIN_PASSWORD_LENGTH = 8

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Set SESSION_COOKIE_SECURE=1 in production (HTTPS only).
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
)


# ---------------------------------------------------------------------------
# Session, CSRF, and access-control helpers
# ---------------------------------------------------------------------------


@app.before_request
def load_member():
    """Look up the logged-in member (if any) once per request."""
    g.member = None
    member_id = session.get("member_id")
    if member_id is not None:
        member = members.get_member_by_id(member_id)
        # Removed members or reset passwords end any existing session.
        if member and member["password_hash"]:
            g.member = member
        else:
            session.clear()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def check_csrf():
    """Every POST must echo the session's CSRF token (form field or header)."""
    if request.method != "POST":
        return
    sent = request.form.get("csrf") or request.headers.get("X-CSRF-Token") or ""
    expected = session.get("csrf") or ""
    if not expected or not hmac.compare_digest(sent.encode(), expected.encode()):
        abort(400, "Your form expired. Go back, refresh the page, and try again.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.member is None:
            return redirect(url_for("login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.member["is_admin"]:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def safe_next(target):
    """Only follow ?next= to paths on this site (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("search_page")


# ---------------------------------------------------------------------------
# Public pages: login, sign-up, logout
# ---------------------------------------------------------------------------


@app.route("/")
def home():
    if g.member:
        return redirect(url_for("search_page"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.member:
        return redirect(url_for("search_page"))
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        member = members.get_member(email)
        if (
            member
            and member["password_hash"]
            and check_password_hash(member["password_hash"], password)
        ):
            session.clear()
            session["member_id"] = member["id"]
            members.record_login(member["id"])
            return redirect(safe_next(request.args.get("next")))
        flash("Wrong email or password.", "error")
        return render_template("login.html", email=email), 401
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.member:
        return redirect(url_for("search_page"))
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        code = request.form.get("code", "").strip()

        def fail(message):
            flash(message, "error")
            return render_template("signup.html", email=email, code=code), 400

        real_code = tracking.get_setting(tracking.SIGNUP_CODE_KEY)
        if not real_code:
            return fail("Sign-up is closed right now. Ask a chapter admin.")
        if not hmac.compare_digest(code.lower().encode(), real_code.lower().encode()):
            return fail("That chapter code is wrong. Ask a chapter admin for it.")
        member = members.get_member(email)
        if not member:
            return fail("This email isn't on the approved list. Ask a chapter admin to add it.")
        if member["password_hash"]:
            flash("This account already exists. Log in instead.", "info")
            return redirect(url_for("login"))
        if len(password) < MIN_PASSWORD_LENGTH:
            return fail(f"Use a password with at least {MIN_PASSWORD_LENGTH} characters.")
        if password != confirm:
            return fail("The two passwords don't match.")

        members.set_password(email, generate_password_hash(password))
        flash("Account created. Log in to start searching.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You're logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Member pages
# ---------------------------------------------------------------------------


@app.route("/search")
@login_required
def search_page():
    query = request.args.get("q", "").strip()
    results = search_it(query)
    if query:
        tracking.log_search(g.member["id"])
    return render_template("search.html", query=query, results=results)


@app.route("/track", methods=["POST"])
@login_required
def track():
    """Called by search.html's JavaScript when a member clicks or copies a contact."""
    data = request.get_json(silent=True) or {}
    alumni_id = data.get("alumni_id")
    if not isinstance(alumni_id, int):
        alumni_id = None
    ok = tracking.log_contact(
        g.member["id"], alumni_id, data.get("channel"), data.get("action")
    )
    return ("", 204) if ok else ("", 400)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


@app.route("/admin")
@admin_required
def admin():
    stats = tracking.member_stats()
    totals = {
        key: sum(row[key] for row in stats)
        for key in (
            "searches",
            "email_clicks",
            "email_copies",
            "linkedin_clicks",
            "linkedin_copies",
        )
    }
    totals["activated"] = sum(1 for row in stats if row["activated_at"])
    return render_template(
        "admin.html",
        stats=stats,
        totals=totals,
        signup_code=tracking.get_setting(tracking.SIGNUP_CODE_KEY),
    )


@app.route("/admin/members", methods=["POST"])
@admin_required
def admin_add_member():
    added, skipped = [], []
    # Accept one email or many separated by commas, spaces, or new lines.
    raw = request.form.get("emails", "").replace(",", " ").split()
    for email in raw:
        email = members.normalize_email(email)
        if "@" not in email or "." not in email.split("@")[-1]:
            skipped.append(email)
        elif members.add_member(email):
            added.append(email)
        else:
            skipped.append(email)
    if added:
        flash(f"Approved {len(added)} email(s): {', '.join(added)}", "success")
    if skipped:
        flash(f"Skipped (invalid or already approved): {', '.join(skipped)}", "info")
    if not raw:
        flash("Type at least one email.", "error")
    return redirect(url_for("admin"))


def _other_member_or_404(member_id):
    member = members.get_member_by_id(member_id)
    if member is None:
        abort(404)
    if member["id"] == g.member["id"]:
        flash("You can't do that to your own account.", "error")
        return None
    return member


@app.route("/admin/members/<int:member_id>/remove", methods=["POST"])
@admin_required
def admin_remove_member(member_id):
    member = _other_member_or_404(member_id)
    if member:
        members.remove_member(member_id)
        flash(f"Removed {member['email']}.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/members/<int:member_id>/admin", methods=["POST"])
@admin_required
def admin_toggle_admin(member_id):
    member = _other_member_or_404(member_id)
    if member:
        members.set_admin(member_id, not member["is_admin"])
        state = "no longer an admin" if member["is_admin"] else "now an admin"
        flash(f"{member['email']} is {state}.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/members/<int:member_id>/reset", methods=["POST"])
@admin_required
def admin_reset_password(member_id):
    member = _other_member_or_404(member_id)
    if member:
        members.reset_password(member_id)
        flash(
            f"Password cleared for {member['email']}. They can sign up again "
            "with the chapter code to set a new one.",
            "success",
        )
    return redirect(url_for("admin"))


@app.route("/admin/code", methods=["POST"])
@admin_required
def admin_set_code():
    code = request.form.get("code", "").strip()
    if len(code) < 4:
        flash("Make the chapter code at least 4 characters.", "error")
    else:
        tracking.set_setting(tracking.SIGNUP_CODE_KEY, code)
        flash("Chapter sign-up code updated.", "success")
    return redirect(url_for("admin"))


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def error_page(error):
    return render_template("error.html", error=error), error.code
