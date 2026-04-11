import os
from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import (
    PrivateMessage,
    User,
    Group,
    GroupMember,
    GroupMessage
)

chat_bp = Blueprint("chat", __name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "docx", "txt"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@chat_bp.route("/dashboard")
@login_required
def dashboard():
    users = User.query.filter(User.id != current_user.id).all()

    my_group_links = GroupMember.query.filter_by(user_id=current_user.id).all()
    my_groups = []
    for item in my_group_links:
        group = Group.query.get(item.group_id)
        if group:
            my_groups.append(group)

    return render_template("dashboard.html", users=users, groups=my_groups)


@chat_bp.route("/chat/<int:user_id>", methods=["GET", "POST"])
@login_required
def private_chat(user_id):
    other_user = User.query.get_or_404(user_id)

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        file = request.files.get("file")

        file_name = None

        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                file_name = filename
            else:
                flash("Dateityp nicht erlaubt.")
                return redirect(url_for("chat.private_chat", user_id=user_id))

        if not content and not file_name:
            flash("Bitte Nachricht oder Datei eingeben.")
            return redirect(url_for("chat.private_chat", user_id=user_id))

        msg = PrivateMessage(
            content=content if content else None,
            file_name=file_name,
            sender_id=current_user.id,
            receiver_id=other_user.id
        )

        db.session.add(msg)
        db.session.commit()

        return redirect(url_for("chat.private_chat", user_id=user_id))

    messages = PrivateMessage.query.filter(
        ((PrivateMessage.sender_id == current_user.id) & (PrivateMessage.receiver_id == user_id)) |
        ((PrivateMessage.sender_id == user_id) & (PrivateMessage.receiver_id == current_user.id))
    ).order_by(PrivateMessage.created_at.asc()).all()

    return render_template("private_chat.html", messages=messages, other_user=other_user)


@chat_bp.route("/groups/create", methods=["GET", "POST"])
@login_required
def create_group():
    users = User.query.filter(User.id != current_user.id).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        selected_user_ids = request.form.getlist("members")

        if not name:
            flash("Bitte Gruppennamen eingeben.")
            return redirect(url_for("chat.create_group"))

        group = Group(name=name)
        db.session.add(group)
        db.session.commit()

        my_membership = GroupMember(group_id=group.id, user_id=current_user.id)
        db.session.add(my_membership)

        for user_id in selected_user_ids:
            member = GroupMember(group_id=group.id, user_id=int(user_id))
            db.session.add(member)

        db.session.commit()

        flash("Gruppe erfolgreich erstellt.")
        return redirect(url_for("chat.group_chat", group_id=group.id))

    return render_template("create_group.html", users=users)


@chat_bp.route("/groups/<int:group_id>", methods=["GET", "POST"])
@login_required
def group_chat(group_id):
    group = Group.query.get_or_404(group_id)

    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not membership:
        flash("Du bist nicht Mitglied dieser Gruppe.")
        return redirect(url_for("chat.dashboard"))

    if request.method == "POST":
        content = request.form.get("content", "").strip()

        if not content:
            flash("Bitte eine Nachricht eingeben.")
            return redirect(url_for("chat.group_chat", group_id=group_id))

        message = GroupMessage(
            content=content,
            group_id=group_id,
            sender_id=current_user.id
        )
        db.session.add(message)
        db.session.commit()

        return redirect(url_for("chat.group_chat", group_id=group_id))

    messages = GroupMessage.query.filter_by(group_id=group_id).order_by(GroupMessage.created_at.asc()).all()

    member_links = GroupMember.query.filter_by(group_id=group_id).all()
    members = []
    for link in member_links:
        user = User.query.get(link.user_id)
        if user:
            members.append(user)

    return render_template(
        "group_chat.html",
        group=group,
        messages=messages,
        members=members
    )


@chat_bp.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)