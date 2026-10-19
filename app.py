from datetime import datetime, timedelta
import os
import csv
import io
import smtplib
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, Response, abort
from data.database import Database
from models.user import User
from models.organization import Organization
from models.study import Study
from models.enrollment import Enrollment
from utils.validators import (
    validate_expert_form,
    validate_study_form,
    validate_organization_form,
)

app = Flask(__name__)
app.secret_key = "super_duper_secret_key"

# email config
app.config["MAIL_HOST"] = os.getenv("MAIL_HOST", "localhost")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 1025))
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
app.config["MAIL_FROM"] = os.getenv("MAIL_FROM", "noreply@accessibilityhub.local")
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "false").lower() == "true"

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")

_db = Database(DB_PATH)
users = User(DB_PATH)
organizations = Organization(DB_PATH)
studies = Study(DB_PATH)
enrollments = Enrollment(DB_PATH)


# check if current user is admin, redirect if not
def require_admin():
    """Require admin to view"""
    if not g.current_user or g.current_user["role"] != "admin":
        flash("Geen toegang - alleen voor beheerders", "error")
        return redirect(url_for("index"))
    return None


def get_profile_id():
    """This returns the profile id."""
    if not g.current_user:
        return None
    if g.current_user["role"] != "expert":
        return None

    profile_id = users.get_profile_by_user_id(g.current_user["id"])
    if not profile_id:
        return None

    return profile_id["id"]

# EMAIL HELPER FUNCTIONS
def send_email(to_email, subject, text_body, html_body=None):
    """ Used to send an email """
    if not to_email:
        print("Geen ontvanger opgegeven voor e-mail.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = app.config["MAIL_FROM"]
    msg["To"] = to_email
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(app.config["MAIL_HOST"], app.config["MAIL_PORT"]) as smtp:
            if app.config["MAIL_USE_TLS"]:
                smtp.starttls()

            username = app.config["MAIL_USERNAME"]
            password = app.config["MAIL_PASSWORD"]

            if username and password:
                smtp.login(username, password)

            smtp.send_message(msg)

        print(f"E-mail succesvol verstuurd naar {to_email}")
        return True

    except Exception as exc:
        print(f"Fout bij versturen e-mail naar {to_email}: {exc}")
        return False

def send_status_email(recipient_email, recipient_name, item_type, item_title, status):
    """ Generate and send a status email """
    subject = f"Statusupdate: {item_type} {status}"

    text_body = render_template(
        "emails/status_update.html.jinja",
        recipient_name=recipient_name,
        item_type=item_type,
        item_title=item_title,
        status=status,
    )

    html_body = render_template(
        "emails/status_update.html.jinja",
        recipient_name=recipient_name,
        item_type=item_type,
        item_title=item_title,
        status=status,
    )

    return send_email(recipient_email, subject, text_body, html_body)

# CSV HELPER FUNCTIONS
def csv_response(filename, fieldnames, rows):
    """ Create a CSV file """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# ICS HELPER FUNCTIONS
def ics_format_text(value):
    """ Text for ICS format """
    if value is None:
        return ""
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace(";", r"\;")
    value = value.replace(",", r"\,")
    value = value.replace("\n", r"\n")
    return value

def ics_response(name, studies_list):
    """ Used to create ICS files """
    now = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", f"X-WR-CALNAME:{name} onderzoeken"]

    for study in studies_list:
        if not study["start_date"]:
            continue
        print(dict(study))
        start = datetime.strptime(study["start_date"], "%Y-%m-%d")
        end = datetime.strptime(study["end_date"] or study["start_date"], "%Y-%m-%d") + timedelta(days=1)

        desc = study["description"]
        if study["reward"]:
            desc += f"\nBeloning: {study['reward']}"
        if study["status"]:
            desc += f"\nStatus: {study['status']}"

        lines += [
            "BEGIN:VEVENT",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
            f"DTEND;VALUE=DATE:{end:%Y%m%d}",
            f"SUMMARY:{ics_format_text(study['title'] or "onderzoek")}",
            f"DESCRIPTION:{ics_format_text(desc)}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

@app.before_request
def load_user_once():
    """Used to get the currently logged in user every time there's a request"""
    g.current_user = None
    user_id = session.get("id")
    if user_id:
        g.current_user = users.get_current_user(user_id)


@app.context_processor
def insert_user():
    """Inserts the user's data"""
    return {"user": g.get("current_user")}


@app.route("/")
def index():
    counts = {
        "experts": users.count_all()[0],
        "organizations": organizations.count_all()[0],
        "studies": studies.count_all()[0],
        "enrollments": enrollments.count_all()[0],
    }
    return render_template("index.html.jinja", counts=counts)


@app.route("/login")
def login():
    """Shows the login page"""
    return render_template("login.html.jinja")


@app.route("/signin", methods=["POST"])
def signin():
    """Gets the form's data and logs in the user with the correct validation"""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        # print("Form data:", email, password)
        main_user = users.authenticate(email, password)

        if not main_user:
            return render_template(
                "login.html.jinja", error="Verkeerde email en of wachtwoord"
            )

        if main_user["status"] == "nieuw" or main_user["status"] == "afgekeurd":
            return render_template(
                "login.html.jinja", error="Uw account is nog niet goedgekeurt"
            )

        session["id"] = main_user["id"]
        session["role"] = main_user["role"]

        # print(main_user, session["id"])

        new_user = users.get_current_user(session["id"])

        # print("New logged in user:", new_user)

        # -- Can be used later to redirect certain roles to different pages [TEST] --
        if session["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        elif session["role"] == "expert":
            return redirect(url_for("expert_dashboard"))
        elif session["role"] == "organization":
            return redirect(url_for("dashboard_organizations"))
        # --

        return redirect(url_for("index"))


@app.route("/signup", methods=["POST"])
def signup():
    """Gets the form's data and registers the user with correct validation"""
    if g.current_user:
        return redirect(url_for("index"))

    if request.method == "POST":
        role = "expert"  # request.form["role"] # HARD coded for nu
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirmpassword"]
        print("Form data:", email, password, confirm_password)
        existing_user = users.authenticate_register(email)

        print(existing_user)

        if existing_user:
            return render_template("register.html.jinja", error="Gebruiker bestaat al")

        if password != confirm_password:
            return render_template(
                "register.html.jinja", error="Wachtwoorden zijn niet gelijk aan elkaar"
            )

        new_user = users.create_new_user(email, password, role)
        print("New User created:", new_user)

        all_disabilities = users.get_all_disabilities()
        return render_template(
            "create_profile.html.jinja",
            new_user=new_user,
            all_disabilities=all_disabilities,
        )


@app.route("/createprofile", methods=["POST"])
def create_profile():
    """Gets the form's data and creates the profile"""
    if request.method == "POST":
        user_id = int(request.form["user_id"])
        disability_id = int(request.form["select_disability"])

        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        postcode = request.form["postcode"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        birth_date = request.form["birth_date"]
        assistive_tools = request.form["assistive_tools"]
        contact_preference = request.form["contact_preference"]
        intro = request.form["intro"]
        notes = request.form["notes"]

        users.create_new_profile(
            user_id,
            first_name,
            last_name,
            postcode,
            gender,
            phone,
            birth_date,
            assistive_tools,
            contact_preference,
            intro,
            notes,
            disability_id,
        )

        return redirect(url_for("index"))


@app.route("/signout")
def signout():
    """logs the current user out and clears the session"""
    session.clear()
    return redirect(url_for("index"))


@app.route("/register")
def register():
    """Shows the register page"""
    return render_template("register.html.jinja")


@app.route("/info")
def info():
    """Shows the info page"""
    return render_template("info.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    auth_check = require_admin()
    if auth_check:
        return auth_check

    # counts for dashboard cards
    new_experts_count = users.count_experts_by_status("nieuw")
    new_studies_count = studies.count_studies_by_status("nieuw")
    new_enrollments_count = enrollments.count_enrollments_by_status("nieuw")
    total_organizations_count = organizations.count_all()[0]

    # latest entries for dashboard lists
    new_experts = users.get_all_experts(limit=5, offset=0, status="nieuw")
    new_studies = studies.get_all_studies(limit=5, offset=0, status="nieuw")
    new_enrollments_list = enrollments.get_enrollment_list(
        limit=5, offset=0, status="nieuw"
    )
    latest_organizations = organizations.select_all_organisations(limit=5, offset=0)

    return render_template(
        "admin_dashboard.html.jinja",
        new_experts_count=new_experts_count,
        new_studies_count=new_studies_count,
        new_enrollments_count=new_enrollments_count,
        total_organizations_count=total_organizations_count,
        new_experts=new_experts,
        new_studies=new_studies,
        new_enrollments=new_enrollments_list,
        latest_organizations=latest_organizations,
    )


@app.route("/admin/experts")
def admin_experts():
    auth_check = require_admin()
    if auth_check:
        return auth_check

    # pagination
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    # Search and filters from GET parameters
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    # Pass filters to model
    experts = users.get_all_experts(
        limit=per_page,
        offset=offset,
        search=search if search else None,
        status=status if status else None,
    )
    total_experts = users.count_all_experts(
        search=search if search else None, status=status if status else None
    )
    total_pages = (total_experts + per_page - 1) // per_page

    return render_template(
        "admin_experts_list.html.jinja",
        experts=experts,
        page=page,
        total_pages=total_pages,
        search=search,
        status=status,
    )


@app.route("/admin/experts/detail")
def admin_expert_detail():
    auth_check = require_admin()
    if auth_check:
        return auth_check
    expert_id = request.args.get("id")
    if not expert_id:
        return "Expert ID is verplicht", 400

    expert = users.get_expert_detail_by_id(expert_id)
    if not expert:
        return "Expert niet gevonden", 404

    return render_template("admin_expert_detail.html.jinja", expert=expert)


# edit expert route
@app.route("/admin/experts/edit/<int:expert_id>", methods=["GET", "POST"])
def admin_expert_edit(expert_id):
    auth_check = require_admin()
    if auth_check:
        return auth_check

    expert = users.get_expert_detail_by_id(expert_id)

    if not expert:
        flash("Expert niet gevonden", "error")
        return redirect(url_for("admin_experts"))

    if request.method == "POST":
        # Validate form data
        errors = validate_expert_form(request.form)

        if errors:
            # Return to form with errors and preserve form data
            return render_template(
                "admin_expert_edit.html.jinja",
                expert=expert,
                errors=errors,
                form_data=request.form,
            )

        # user fields
        email = request.form.get("email")
        status = request.form.get("status")

        # profile fields
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        phone = request.form.get("phone")
        postcode = request.form.get("postcode")
        birth_date = request.form.get("birth_date")
        gender = request.form.get("gender")
        assistive_tools = request.form.get("assistive_tools")
        contact_preference = request.form.get("contact_preference")
        preferred_study_type = request.form.get("preferred_study_type")
        availability = request.form.get("availability")
        intro = request.form.get("intro")
        notes = request.form.get("notes")

        # update user and profile
        users.update_expert(
            expert_id,
            email,
            status,
            first_name,
            last_name,
            phone,
            postcode,
            birth_date,
            gender,
            assistive_tools,
            contact_preference,
            preferred_study_type,
            availability,
            intro,
            notes,
        )
        flash("Expert succesvol bijgewerkt", "success")
        return redirect(url_for("admin_experts"))

    return render_template("admin_expert_edit.html.jinja", expert=expert)


# ADMIN | ORGANISATION ------------------
@app.route("/admin/organizations")
def admin_organizations():
    """Get list of all organizations with search and filter"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    # pagination
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    # Search and filters from GET parameters
    search = request.args.get("search", "").strip()
    org_type = request.args.get("type", "").strip()

    # Pass filters to model
    organization = organizations.select_all_organisations(
        limit=per_page,
        offset=offset,
        search=search if search else None,
        org_type=org_type if org_type else None,
    )
    # user_list = users.get_users_by_role("organization")
    user_list = users.get_all_users()
    total_organizations = organizations.count_all_organizations(
        search=search if search else None, org_type=org_type if org_type else None
    )
    total_pages = (total_organizations + per_page - 1) // per_page

    return render_template(
        "admin_organizations_list.html.jinja",
        organization=organization,
        user_list=user_list,
        page=page,
        total_pages=total_pages,
        search=search,
        org_type=org_type,
    )


@app.route("/admin/organizations-details/<int:organization_id>")
def admin_organization_details(organization_id):
    """Get details of single organization"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    organization = organizations.get_single_organisations(organization_id)

    if not organization:
        flash("Organisatie niet gevonden", "error")
        return redirect(url_for("admin_organizations"))

    user_list = users.get_user_organization_id(organization_id)
    return render_template(
        "admin_organization_details.html.jinja",
        organization=organization,
        user_list=user_list,
    )


@app.route("/admin/organizations/<int:organization_id>/accept", methods=["POST"])
def admin_accept_organization(organization_id):
    """Accept organization connected with organization-user"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    user_id = int(request.form.get("user_id"))
    user = users.get_user(user_id)

    if not user:
        return redirect(url_for("admin_organizations"))

    if user["role"] == "admin":
        return redirect(url_for("admin_organizations"))

    action = request.form.get("action")

    if not user_id:
        flash("User ID ?", "warning")
        return redirect(url_for("admin_organizations"))

    organization = organizations.get_single_organisations(organization_id)
    if not organization:
        flash("Organisatie niet gevonden", "error")
        return redirect(url_for("admin_organizations"))

    organizations.set_organization(user_id, organization_id)

    if action == "accept":
        organizations.update_status(user_id, status="goedgekeurd")
        organizations.set_role(user_id, role="organization")

        send_status_email(
            recipient_email=organization["email"] or user["email"],
            recipient_name=organization["contact_person"] or organization["name"],
            item_type="organisatie registratie",
            item_title=organization["name"],
            status="goedgekeurd",
        )
    else:
        organizations.update_status(user_id, status="nieuw", clear_email=True)
        organizations.set_role(user_id, role="expert")

        send_status_email(
            recipient_email=organization["email"] or user["email"],
            recipient_name=organization["contact_person"] or organization["name"],
            item_type="organisatie registratie",
            item_title=organization["name"],
            status="afgekeurd",
        )

    return redirect(url_for("admin_organizations"))


@app.route("/admin/organizations/new", methods=["GET", "POST"])
def admin_organization_new():
    """Create a new organization profile"""
    organization = organizations.select_all_organisations()
    user_list = users.get_users_by_role("organization")
    auth_check = require_admin()
    if auth_check:
        return auth_check

    if request.method == "POST":
        # Validate form data
        errors = validate_organization_form(request.form)

        if errors:
            # Return to form with errors and preserve form data
            return render_template(
                "admin_organization_form.html.jinja",
                errors=errors,
                form_data=request.form,
            )

        name = request.form.get("name")
        org_type = request.form.get("org_type")
        website = request.form.get("website")
        description = request.form.get("description")
        contact_person = request.form.get("contact_person")
        email = request.form.get("email")
        phone = request.form.get("phone")
        details = request.form.get("details")
        user_idx = request.form.get("user_id")
        user_id = int(user_idx) if user_idx else None

        organization_id = organizations.create_organization(
            name, org_type, website, description, contact_person, email, phone, details
        )
        organizations.set_organization(user_id, organization_id)
        organizations.update_status(user_id, organization_id)
        flash("New organization created", "success")
        return redirect(url_for("admin_organizations"))
    return render_template(
        "admin_organization_form.html.jinja", organization=organization
    )


@app.route("/admin/organizations/edit/<int:organization_id>", methods=["GET", "POST"])
def admin_organization_edit(organization_id):
    """Edit organization profile"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    organization = organizations.get_single_organisations(organization_id)

    if not organization:
        flash("Organisatie niet gevonden", "error")
        return redirect(url_for("admin_organizations"))

    if request.method == "POST":
        # Validate form data
        errors = validate_organization_form(request.form)

        if errors:
            # Return to form with errors and preserve form data
            return render_template(
                "admin_organization_edit.html.jinja",
                organization=organization,
                errors=errors,
                form_data=request.form,
            )

        name = request.form.get("name")
        org_type = request.form.get("org_type")
        website = request.form.get("website")
        description = request.form.get("description")
        contact_person = request.form.get("contact_person")
        email = request.form.get("email")
        phone = request.form.get("phone")
        details = request.form.get("details")

        organizations.update_organization(
            organization_id,
            name,
            org_type,
            website,
            description,
            contact_person,
            email,
            phone,
            details,
        )
        flash("Organisatie succesvol bijgewerkt", "success")
        return redirect(url_for("admin_organizations"))

    return render_template(
        "admin_organization_edit.html.jinja", organization=organization
    )


# ---------------------------------
# CSV EXPORT ROUTES
@app.route("/admin/export/studies.csv")
def export_studies_csv():
    """ Export studies as CSV """
    auth_check = require_admin()
    if auth_check:
        return auth_check

    all_studies = studies.get_all_studies(limit=100000, offset=0)

    rows = []
    for study in all_studies:
        rows.append({
            "#": study["id"],
            "Studie Titel": study["title"],
            "Beschrijving": study["description"],
            "Start Datum": study["start_date"],
            "Eind Datum": study["end_date"],
            "Beloning": study["reward"],
            "Studie Status": study["status"],
            "Studie Type": study["study_type"],
            "Organisatie": study["org_name"],
        })

    return csv_response(
        "onderzoeken.csv",
        [
            "#",
            "Studie Titel",
            "Beschrijving",
            "Start Datum",
            "Eind Datum",
            "Beloning",
            "Studie Status",
            "Studie Type",
            "Organisatie",
        ],
        rows,
    )

@app.route("/admin/export/enrollments.csv")
def export_enrollments_csv():
    """ Export enrollments as CSV """
    auth_check = require_admin()
    if auth_check:
        return auth_check

    all_enrollments = enrollments.get_enrollment_list(limit=100000, offset=0)

    rows = []
    for enrollment in all_enrollments:
        rows.append({
            "#": enrollment["enrollment_id"],
            "Studie ID": enrollment["study_id"],
            "Studie Titel": enrollment["study_title"],
            "Profiel ID": enrollment["profile_id"],
            "Voornaam": enrollment["first_name"],
            "Achternaam": enrollment["last_name"],
            "Email": enrollment["email"],
            "Organisatie Naam": enrollment["organization_name"],
            "Organisatie Email": enrollment["organization_email"],
            "Inschrijving Status": enrollment["enrollment_status"],
        })

    return csv_response(
        "inschrijvingen.csv",
        [
            "#",
            "Studie ID",
            "Studie Titel",
            "Profiel ID",
            "Voornaam",
            "Achternaam",
            "Email",
            "Organisatie Naam",
            "Organisatie Email",
            "Inschrijving Status",
        ],
        rows,
    )

# ---------------------------------
# ICS EXPORT ROUTES

@app.route("/organization/calendar.ics")
def organization_calendar_ics():
    """ Download an ICS calendar for the current organization """
    if not g.current_user:
        return redirect(url_for("login"))

    if g.current_user["role"] != "organization":
        flash("Geen toegang tot agenda-export", "error")
        return redirect(url_for("index"))

    organization_id = g.current_user["organization_id"]
    organization = organizations.get_single_organisations(organization_id)

    if not organization:
        flash("Organisatie niet gevonden", "error")
        return redirect(url_for("dashboard_organizations"))

    studies_list = studies.get_studies_by_organization_paginated(
        organization_id, limit=100000, offset=0
    )

    ics_data = ics_response(organization["name"], studies_list)

    filename = f'organisatie_{organization_id}_agenda.ics'
    return Response(
        ics_data,
        mimetype="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# ---------------------------------

@app.route("/admin/studies")
def admin_studies():
    """Get all studies"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    # pagination
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    # Search and filters from GET parameters
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    # Pass filters to model
    all_studies = studies.get_all_studies(
        limit=per_page,
        offset=offset,
        search=search if search else None,
        status=status if status else None,
    )
    total_studies = studies.count_all_studies(
        search=search if search else None, status=status if status else None
    )
    total_pages = (total_studies + per_page - 1) // per_page

    return render_template(
        "admin_studies_list.html.jinja",
        studies=all_studies,
        page=page,
        total_pages=total_pages,
        search=search,
        status=status,
    )


@app.route("/admin/enrollments")
def admin_enrollments():
    """Get all enrollments"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    # pagination
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    # Filter from GET parameter
    status = request.args.get("status", "").strip()

    # Pass filter to model
    enroll = enrollments.get_enrollment_list(
        limit=per_page, offset=offset, status=status if status else None
    )
    total_enrollments = enrollments.count_all_enrollments(
        status=status if status else None
    )
    total_pages = (total_enrollments + per_page - 1) // per_page

    return render_template(
        "admin_enrollments_list.html.jinja",
        enroll=enroll,
        page=page,
        total_pages=total_pages,
        status=status,
    )


@app.route("/admin/enrollment_details/<int:enroll_id>")
def admin_enrollment_detail(enroll_id):
    """Show enrollment details"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    enrollment = enrollments.get_enrollment_list_items(enroll_id)

    if not enrollment:
        flash("Inschrijving niet gevonden", "error")
        return redirect(url_for("admin_enrollments"))

    return render_template("admin_enrollment_detail.html.jinja", enrollment=enrollment)


@app.route("/admin/approve-enrollment/<int:enroll_id>/approve", methods=["POST"])
def approve_enrollment(enroll_id):
    """Approve an enrollment"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    enrollment = enrollments.get_enrollment_list_items(enroll_id)
    enrollments.update_enrollment_status(enroll_id)

    if enrollment:
        expert_name = f"{enrollment['first_name']} {enrollment['last_name']}".strip()
        study_title = enrollment["study_title"]

        send_status_email(
            recipient_email=enrollment["email"],
            recipient_name=expert_name,
            item_type="inschrijving",
            item_title=study_title,
            status="goedgekeurd",
        )

        send_status_email(
            recipient_email=enrollment["organization_email"],
            recipient_name=enrollment["organization_name"],
            item_type="inschrijving",
            item_title=study_title,
            status="goedgekeurd",
        )

    return redirect(url_for("admin_enrollments"))


#
@app.route("/admin/reject-enrollment/<int:enroll_id>/reject", methods=["POST"])
def reject_enrollment(enroll_id):
    """Reject an enrollment"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    enrollment = enrollments.get_enrollment_list_items(enroll_id)
    enrollments.delete_enrollment_status(enroll_id)

    print(dict(enrollment))

    if enrollment:
        expert_name = f"{enrollment['first_name']} {enrollment['last_name']}".strip()
        study_title = enrollment["study_title"]

        send_status_email(
            recipient_email=enrollment["email"],
            recipient_name=expert_name,
            item_type="inschrijving",
            item_title=study_title,
            status="afgekeurd",
        )

        send_status_email(
            recipient_email=enrollment["organization_email"],
            recipient_name=enrollment["organization_name"],
            item_type="inschrijving",
            item_title=study_title,
            status="afgekeurd",
        )

    return redirect(url_for("admin_enrollments"))


@app.route("/admin/approve-expert/<int:expert_id>", methods=["POST"])
def approve_expert(expert_id):
    """Approve an Expert"""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    expert = users.get_expert_detail_by_id(expert_id)
    success = users.approve_expert(expert_id)

    print(dict(expert))

    if success and expert:
        full_name = f"{expert['first_name']} {expert['last_name']}".strip()

        send_status_email(
            recipient_email=expert["email"],
            recipient_name=full_name,
            item_type="registratie als ervaringsdeskundige",
            item_title=full_name,
            status="goedgekeurd",
        )

        flash("Expert succesvol goedgekeurd!", "success")
    else:
        flash("Expert niet gevonden of kon niet worden goedgekeurd.", "error")

    return redirect(url_for("admin_experts"))


@app.route("/admin/reject-expert/<int:expert_id>", methods=["POST"])
def reject_expert(expert_id):
    """Reject an expert"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    success = users.reject_expert(expert_id)
    if success:
        flash(f"Expert afgekeurd.", "warning")
    else:
        flash("Expert niet gevonden of kon niet worden afgekeurd.", "error")
    return redirect(url_for("admin_experts"))


@app.route("/organization/dashboard")
def dashboard_organizations():
    """Displays the organization dashboard"""
    if not g.current_user:
        return redirect(url_for("login"))

    if g.current_user["role"] != "organization":
        return redirect(url_for("index"))

    organization_id = g.current_user["organization_id"]

    # pagination per page, there is 5 rows
    page = int(request.args.get("page", 1))
    per_page = 5
    offset = (page - 1) * per_page

    studies_list = studies.get_studies_by_organization_paginated(
        organization_id, limit=per_page, offset=offset
    )

    total_studies = studies.count_studies_by_organization(organization_id)
    total_pages = (total_studies + per_page - 1) // per_page

    return render_template(
        "dashboard_organization.html.jinja",
        studies=studies_list,
        page=page,
        total_pages=total_pages,
    )


# EXPERT ROUTE -------------------------
@app.route("/expert/dashboard")
def expert_dashboard():
    """Get enrollment list of profile"""
    enrollment = users.get_enrollment_by_id(get_profile_id())
    return render_template("expert_enrollments.html", enrollment=enrollment)


@app.route("/expert/enrollments")
def expert_enrollments():
    """Get enrollment list of profile"""
    enrollment = users.get_enrollment_by_id(get_profile_id())
    return render_template("expert_enrollments.html", enrollment=enrollment)


@app.route("/expert/enrollment_details/<int:enrollment_id>")
def expert_enrollment_details(enrollment_id):
    """Get enrollment details"""
    enrollment = users.get_enrollment_id(enrollment_id)
    return render_template(
        "expert_enrollments_details.html.jinja", enrollment=enrollment
    )


@app.route("/expert/register_enrollment")
def expert_register_enrollment():
    """Register for a study"""
    study_id = request.args.get("study_id", type=int)
    if not study_id:
        return "No study id", 400
    enrollment = users.get_enrollment_by_id(get_profile_id())
    register_enrollment = users.register_enrollment(study_id, get_profile_id())
    return render_template(
        "expert_enrollments.html", enrollment=enrollment, register=register_enrollment
    )


@app.route("/expert/expert_enrollments_list_details")
def expert_enrollments_list_details():
    """Get enrollment list details"""
    study_id = request.args.get("study_id", type=int)
    enrollment = users.get_enrollment_by_id(get_profile_id())

    if not study_id:
        return "No study ID", 400
    study = users.get_study_list_by_id(study_id)
    if not study:
        return "Study Not Found", 404

    if study:
        for s in study:
            print(s)

    return render_template(
        "expert_enrollments_list_details.html.jinja", study=study, enrollment=enrollment
    )


@app.route("/expert/studies")
def expert_studies():
    """Show all studies"""

    enrollment_filtered = users.get_enrollment_list_filtered_disability(
        get_profile_id()
    )
    return render_template(
        "expert_studies.html.jinja", enrollment_filtered=enrollment_filtered
    )


@app.route("/expert/profile/<int:user_id>")
def expert_profile(user_id):
    """Show profile of user"""
    # logged in, but if this is not your profile than access denied
    if g.current_user["id"] != user_id:
        abort(403) #Forbidden

    profile = users.get_profile(user_id)
    if not profile:
        abort(404) #Not found

    profile_id = profile["id"]
    all_disabilities = users.get_all_disabilities()
    profile_disability = users.get_profile_disability(get_profile_id())
    profile_disability_item = profile_disability[0] if profile_disability else None

    return render_template(
        "expert_profile.html",
        profile=profile,
        profile_disability_item=profile_disability_item,
        all_disabilities=all_disabilities,
    )


@app.route("/expert/expert_profile/update", methods=["POST"])
def expert_profile_update():
    """Update profile"""
    profile = users.get_profile(g.current_user["id"])
    profile_id = profile["id"]
    user_id = profile["user_id"]
    disability_id = int(request.form["select_disability"])

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    postcode = request.form["postcode"]
    gender = request.form["gender"]
    phone = request.form["phone"]
    birth_date = request.form["birth_date"]
    assistive_tools = request.form["assistive_tools"]
    intro = request.form["intro"]
    notes = request.form["notes"]
    contact_preference = request.form["contact_preference"]

    users.update_profile(
        first_name,
        last_name,
        postcode,
        gender,
        phone,
        birth_date,
        assistive_tools,
        intro,
        notes,
        contact_preference,
        disability_id,
        profile_id,
    )
    return redirect(url_for("expert_profile", user_id=user_id))


# ORGANIZATION ------------------------


@app.route("/study/details/<int:study_id>")
def study_details(study_id):
    """Shows the details page of a specific study"""
    study = studies.get_study_by_id(study_id)
    return render_template("dashboard_organization_details.html.jinja", study=study)


@app.route("/study/new")
def study_new():
    """Displays the page where an organization can create a new study"""
    return render_template("dashboard_organization_study.html.jinja")


@app.route("/organization/study/new", methods=["GET", "POST"])
def organization_study_new():
    """Creates a new organization study"""
    if not g.current_user or g.current_user["role"] != "organization":
        return redirect(url_for("login"))

    organization_id = g.current_user["organization_id"]

    if request.method == "POST":
        studies.create_study(
            title=request.form["title"],
            description=request.form["description"],
            start_date=request.form["start_date"],
            end_date=request.form["end_date"],
            reward=request.form["reward"],
            organization_id=organization_id,
        )
        return redirect("/organization/dashboard")
    print("USER", g.current_user)
    print("ORG id", organization_id)
    return render_template("dashboard_organization_study.html.jinja")


@app.route("/organization/study/edit/<int:study_id>", methods=["GET", "POST"])
def organization_study_edit(study_id):
    """Allows organization to edit an existing study"""
    study = studies.get_study_by_id(study_id)

    if not study:
        return "Onderzoek niet gevonden", 404

    if request.method == "POST":
        studies.update_study(
            study_id,
            request.form["title"],
            request.form["description"],
            request.form["start_date"],
            request.form["end_date"],
            request.form["reward"],
            study["status"],
            study["organization_id"],
            study["study_type"],
        )

        return redirect("/organization/dashboard")
    return render_template("dashboard_organization_edit.html.jinja", study=study)


@app.route("/organization/enrollments/<int:study_id>")
def organization_enrollments(study_id):
    approved_enrollments = enrollments.approved_enrollments_study(study_id)

    return render_template(
        "dashboard_organization_enrollments.html.jinja",
        enrollments=approved_enrollments,
    )


@app.route("/admin/study/<int:study_id>")
def admin_detail(study_id):
    """Shows detailed information about a study for admin"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    study = studies.get_study_with_organization(study_id)

    if not study:
        return "Onderzoek niet gevonden", 404

    # disabilities for this study
    study_disabilities = studies.get_study_disabilities_details(study_id)

    return render_template(
        "admin_study_detail.html.jinja",
        study=study,
        study_disabilities=study_disabilities,
    )


# edit study route
@app.route("/admin/studies/edit/<int:study_id>", methods=["GET", "POST"])
def admin_study_edit(study_id):
    auth_check = require_admin()
    if auth_check:
        return auth_check

    study = studies.get_study_by_id(study_id)

    if not study:
        flash("Onderzoek niet gevonden", "error")
        return redirect(url_for("admin_studies"))

    if request.method == "POST":
        # Validate form data
        errors = validate_study_form(request.form)

        if errors:
            # Get all organizations for dropdown
            all_organizations = organizations.select_all_organisations(
                limit=1000, offset=0
            )
            # Return to form with errors and preserve form data
            return render_template(
                "admin_study_edit.html.jinja",
                study=study,
                organizations=all_organizations,
                errors=errors,
                form_data=request.form,
            )

        title = request.form.get("title")
        description = request.form.get("description")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        reward = request.form.get("reward")
        status = request.form.get("status")
        organization_id = request.form.get("organization_id")
        study_type = request.form.get("study_type")

        studies.update_study(
            study_id,
            title,
            description,
            start_date,
            end_date,
            reward,
            status,
            organization_id,
            study_type,
        )
        flash("Onderzoek succesvol bijgewerkt", "success")
        return redirect(url_for("admin_studies"))

    # Get all organizations for dropdown
    all_organizations = organizations.select_all_organisations(limit=1000, offset=0)

    return render_template(
        "admin_study_edit.html.jinja", study=study, organizations=all_organizations
    )


@app.route("/admin/approve-study/<int:study_id>", methods=["POST"])
def admin_approve_study(study_id):
    """Approves a study by updating it too 'goedgekeurd'."""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    study = studies.get_study_with_organization(study_id)
    studies.update_status(study_id, "goedgekeurd")

    print(dict(study))

    if study:
        send_status_email(
            recipient_email=study["organization_email"],
            recipient_name=study["org_name"],
            item_type="onderzoek",
            item_title=study["title"],
            status="goedgekeurd",
        )

    return redirect(url_for("admin_studies"))


@app.route("/admin/reject-study/<int:study_id>", methods=["POST"])
def admin_reject_study(study_id):
    """Rejects a study by updating it too 'afgekeurd'."""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    study = studies.get_study_with_organization(study_id)
    studies.update_status(study_id, "afgekeurd")

    if study:
        send_status_email(
            recipient_email=study["organization_email"],
            recipient_name=study["org_name"],
            item_type="onderzoek",
            item_title=study["title"],
            status="afgekeurd",
        )

    return redirect(url_for("admin_studies"))


@app.route("/admin/close-study/<int:study_id>", methods=["POST"])
def admin_close_study(study_id):
    """Closes a study by updating it too 'gesloten'."""
    auth_check = require_admin()
    if auth_check:
        return auth_check

    studies.update_status(study_id, "gesloten")
    study = studies.get_study_with_organization(study_id)

    if study:
        send_status_email(
            recipient_email=study["organization_email"],
            recipient_name=study["org_name"],
            item_type="onderzoek",
            item_title=study["title"],
            status="gesloten",
        )
    return redirect(url_for("admin_studies"))


if __name__ == "__main__":
    app.run(debug=True)
