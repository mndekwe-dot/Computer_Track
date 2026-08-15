"""Bulk student import from CSV.

Nobody types 5,000 students by hand. The design constraint is that a registrar
should never be able to half-import a file: the whole thing is parsed and
validated first, the results are shown as a preview, and only then is it
committed - in a single transaction, so a failure part-way leaves nothing
behind.
"""

import csv
import io

from django.db import transaction
from rest_framework import serializers

from campus.models import Department

from .models import Student, StudentStatus, normalise_reg_number

# Accepted column names, lower-cased and stripped. Several spellings are
# allowed because every registry exports something slightly different.
COLUMNS = {
    "reg_number": {"reg_number", "registration_number", "reg no", "reg", "student_id"},
    "first_name": {"first_name", "firstname", "given_name", "first"},
    "last_name": {"last_name", "lastname", "surname", "family_name", "last"},
    "email": {"email", "e-mail", "email_address"},
    "phone": {"phone", "telephone", "mobile", "phone_number"},
    "national_id": {"national_id", "nid", "id_number"},
    "department": {"department", "department_code", "dept"},
    "programme": {"programme", "program", "course"},
    "year_of_study": {"year_of_study", "year", "level"},
    "status": {"status"},
}

REQUIRED = {"reg_number", "first_name", "last_name"}
MAX_ROWS = 10000


def _map_headers(fieldnames):
    """Map the file's headers onto our field names, or say what is missing."""
    mapping = {}
    for raw in fieldnames or []:
        key = (raw or "").strip().lower().replace(" ", "_")
        for field, aliases in COLUMNS.items():
            if key == field or key in {alias.replace(" ", "_") for alias in aliases}:
                mapping[raw] = field
                break

    missing = REQUIRED - set(mapping.values())
    if missing:
        raise serializers.ValidationError(
            {
                "file": [
                    "The file is missing required column(s): "
                    + ", ".join(sorted(missing))
                    + ". Expected headers include reg_number, first_name, last_name."
                ]
            }
        )
    return mapping


def parse_csv(upload):
    """Read the upload into rows, classified as create / update / error.

    Nothing is written. The result is what the preview screen shows.
    """
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise serializers.ValidationError(
            {"file": ["The file is not valid UTF-8. Re-export it as UTF-8 CSV."]}
        )

    reader = csv.DictReader(io.StringIO(text))
    mapping = _map_headers(reader.fieldnames)

    departments = {
        code.upper(): pk for pk, code in Department.objects.values_list("id", "code")
    }
    existing = {
        key: pk for pk, key in Student.objects.values_list("id", "reg_number_key")
    }

    creates, updates, errors = [], [], []
    seen_in_file = {}

    for line_number, raw_row in enumerate(reader, start=2):
        if line_number - 1 > MAX_ROWS:
            errors.append(
                {"line": line_number, "reg_number": "", "problems": [f"File exceeds {MAX_ROWS} rows."]}
            )
            break

        row = {}
        for raw_key, field in mapping.items():
            row[field] = (raw_row.get(raw_key) or "").strip()

        problems = []
        reg_number = row.get("reg_number", "")
        key = normalise_reg_number(reg_number)

        if not key:
            problems.append("Registration number is blank.")
        if not row.get("first_name"):
            problems.append("First name is blank.")
        if not row.get("last_name"):
            problems.append("Last name is blank.")

        if key and key in seen_in_file:
            problems.append(f"Duplicate of line {seen_in_file[key]} in this same file.")
        elif key:
            seen_in_file[key] = line_number

        department_code = (row.get("department") or "").strip().upper()
        department_id = None
        if department_code:
            department_id = departments.get(department_code)
            if department_id is None:
                problems.append(f"Unknown department code '{department_code}'.")

        year = row.get("year_of_study") or ""
        year_value = None
        if year:
            try:
                year_value = int(year)
                if not 1 <= year_value <= 8:
                    problems.append("Year of study must be between 1 and 8.")
            except ValueError:
                problems.append(f"Year of study '{year}' is not a number.")

        status = (row.get("status") or StudentStatus.ACTIVE).strip().upper()
        if status not in StudentStatus.values:
            problems.append(f"Unknown status '{status}'.")

        if problems:
            errors.append({"line": line_number, "reg_number": reg_number, "problems": problems})
            continue

        record = {
            "line": line_number,
            "reg_number": reg_number.strip().upper(),
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "email": row.get("email", ""),
            "phone": row.get("phone", ""),
            "national_id": row.get("national_id", ""),
            "programme": row.get("programme", ""),
            "department_id": department_id,
            "year_of_study": year_value,
            "status": status,
        }

        if key in existing:
            record["existing_id"] = existing[key]
            updates.append(record)
        else:
            creates.append(record)

    return {"creates": creates, "updates": updates, "errors": errors}


@transaction.atomic
def commit(parsed, update_existing=True):
    """Write the parsed rows. All or nothing.

    Rows are saved one at a time rather than bulk-created on purpose: the
    search index is maintained by post_save signals, and `bulk_create` does not
    fire them. Correct search beats a faster import.
    """
    created = updated = 0

    for record in parsed["creates"]:
        Student.objects.create(**_fields(record))
        created += 1

    if update_existing:
        for record in parsed["updates"]:
            student = Student.objects.get(pk=record["existing_id"])
            for field, value in _fields(record).items():
                # A blank cell means "no new information", not "erase what we
                # have" - registry exports are frequently partial.
                if value not in ("", None):
                    setattr(student, field, value)
            student.save()
            updated += 1

    return {"created": created, "updated": updated, "skipped": len(parsed["errors"])}


def _fields(record):
    return {
        "reg_number": record["reg_number"],
        "first_name": record["first_name"],
        "last_name": record["last_name"],
        "email": record["email"],
        "phone": record["phone"],
        "national_id": record["national_id"],
        "programme": record["programme"],
        "department_id": record["department_id"],
        "year_of_study": record["year_of_study"],
        "status": record["status"],
    }
