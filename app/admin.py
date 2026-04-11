from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required():
    return current_user.is_authenticated and current_user.is_admin


@admin_bp.route("/")
@login_required
def dashboard():
    if not admin_required():
        flash("Nur Admins dürfen diese Seite öffnen.")
        return redirect(url_for("chat.dashboard"))

    users = User.query.order_by(User.id.asc()).all()
    return render_template("admin_dashboard.html", users=users)


@admin_bp.route("/make-admin/<int:user_id>")
@login_required
def make_admin(user_id):
    if not admin_required():
        flash("Nur Admins dürfen diese Aktion ausführen.")
        return redirect(url_for("chat.dashboard"))

    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()

    flash(f"{user.username} ist jetzt Admin.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/remove-admin/<int:user_id>")
@login_required
def remove_admin(user_id):
    if not admin_required():
        flash("Nur Admins dürfen diese Aktion ausführen.")
        return redirect(url_for("chat.dashboard"))

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Du kannst dir selbst Admin nicht wegnehmen.")
        return redirect(url_for("admin.dashboard"))

    user.is_admin = False
    db.session.commit()

    flash(f"{user.username} ist kein Admin mehr.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/deactivate/<int:user_id>")
@login_required
def deactivate_user(user_id):
    if not admin_required():
        flash("Nur Admins dürfen diese Aktion ausführen.")
        return redirect(url_for("chat.dashboard"))

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Du kannst dich nicht selbst deaktivieren.")
        return redirect(url_for("admin.dashboard"))

    user.is_active_user = False
    user.is_online = False
    db.session.commit()

    flash(f"{user.username} wurde deaktiviert.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/activate/<int:user_id>")
@login_required
def activate_user(user_id):
    if not admin_required():
        flash("Nur Admins dürfen diese Aktion ausführen.")
        return redirect(url_for("chat.dashboard"))

    user = User.query.get_or_404(user_id)
    user.is_active_user = True
    db.session.commit()

    flash(f"{user.username} wurde aktiviert.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/delete/<int:user_id>")
@login_required
def delete_user(user_id):
    if not admin_required():
        flash("Nur Admins dürfen diese Aktion ausführen.")
        return redirect(url_for("chat.dashboard"))

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Du kannst dich nicht selbst löschen.")
        return redirect(url_for("admin.dashboard"))

    db.session.delete(user)
    db.session.commit()

    flash("Benutzer wurde gelöscht.")
    return redirect(url_for("admin.dashboard"))