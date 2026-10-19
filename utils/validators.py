import re
from datetime import datetime


def validate_email(email):
    # Email regex validation according to CASUS requirements
    if not email:
        return "E-mailadres is verplicht"

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return "Ongeldig e-mailadres formaat"

    return None


def validate_postcode(postcode):
    # Dutch postcode validation: 1234AB or 1234 AB
    if not postcode:
        return None

    pattern = r"^[1-9][0-9]{3}\s?[A-Z]{2}$"
    if not re.match(pattern, postcode.strip()):
        return "Ongeldige postcode. Gebruik formaat: 1234AB"

    return None


def validate_phone(phone):
    # phone validation: exactly 10 digits (with 0) or 11 digits (with +31)
    if not phone:
        return None

    # First check if phone contains only valid characters
    if not re.match(r"^[\d\s\-\+\(\)]+$", phone):
        return (
            "Telefoonnummer mag alleen cijfers, spaties, streepjes en haakjes bevatten"
        )

    # Remove spaces, dashes, parentheses for validation
    cleaned_phone = (
        phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    )

    # exactly 10 digits starting with 0, or 11 digits starting with +31
    if cleaned_phone.startswith("+31"):
        # Must be exactly 12 characters: +31 + 9 digits
        pattern = r"^\+31[1-9][0-9]{8}$"
    else:
        # Must be exactly 10 digits starting with 0
        pattern = r"^0[1-9][0-9]{8}$"

    if not re.match(pattern, cleaned_phone):
        return "Ongeldig telefoonnummer. Voorbeelden: 06-12345678, 020-1234567, +31-6-12345678"

    return None


def validate_birth_date(birth_date):
    # Birth date cannot be in the future
    if not birth_date:
        return None

    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d")
        if birth > datetime.now():
            return "Geboortedatum kan niet in de toekomst liggen"
    except ValueError:
        return "Ongeldige datum formaat"

    return None


def validate_date_range(start_date, end_date):
    # End date must be after start date
    if not start_date or not end_date:
        return None

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if end <= start:
            return "Einddatum moet na de startdatum liggen"
    except ValueError:
        return "Ongeldige datum formaat"

    return None


def validate_required_field(value, field_name):
    # Generic required field validation
    if not value or (isinstance(value, str) and not value.strip()):
        return f"{field_name} is verplicht"
    return None


def validate_expert_form(form_data):
    # Validate expert registration/edit form
    errors = {}

    # Required fields
    email_error = validate_email(form_data.get("email"))
    if email_error:
        errors["email"] = email_error

    first_name_error = validate_required_field(form_data.get("first_name"), "Voornaam")
    if first_name_error:
        errors["first_name"] = first_name_error

    last_name_error = validate_required_field(form_data.get("last_name"), "Achternaam")
    if last_name_error:
        errors["last_name"] = last_name_error

    # Optional fields with format validation
    postcode_error = validate_postcode(form_data.get("postcode"))
    if postcode_error:
        errors["postcode"] = postcode_error

    phone_error = validate_phone(form_data.get("phone"))
    if phone_error:
        errors["phone"] = phone_error

    birth_date_error = validate_birth_date(form_data.get("birth_date"))
    if birth_date_error:
        errors["birth_date"] = birth_date_error

    return errors


def validate_study_form(form_data):
    # Validate study form
    errors = {}

    # Required fields
    title_error = validate_required_field(form_data.get("title"), "Titel")
    if title_error:
        errors["title"] = title_error

    description_error = validate_required_field(
        form_data.get("description"), "Beschrijving"
    )
    if description_error:
        errors["description"] = description_error

    start_date = form_data.get("start_date")
    end_date = form_data.get("end_date")

    if not start_date:
        errors["start_date"] = "Startdatum is verplicht"

    if not end_date:
        errors["end_date"] = "Einddatum is verplicht"

    # Date range validation
    if start_date and end_date:
        date_range_error = validate_date_range(start_date, end_date)
        if date_range_error:
            errors["end_date"] = date_range_error

    return errors


def validate_organization_form(form_data):
    # Validate organization form
    errors = {}

    # Required fields
    name_error = validate_required_field(form_data.get("name"), "Naam")
    if name_error:
        errors["name"] = name_error

    email_error = validate_email(form_data.get("email"))
    if email_error:
        errors["email"] = email_error

    contact_person_error = validate_required_field(
        form_data.get("contact_person"), "Contactpersoon"
    )
    if contact_person_error:
        errors["contact_person"] = contact_person_error

    # Optional fields with format validation
    phone_error = validate_phone(form_data.get("phone"))
    if phone_error:
        errors["phone"] = phone_error

    return errors
