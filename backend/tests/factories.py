"""Small helpers so each test reads as the scenario it is testing."""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from campus import rules
from campus.models import Gate, Rule
from devices.models import Device
from students.models import Student

User = get_user_model()


def make_user(username, role="GUARD", **extra):
    user = User.objects.create_user(
        username=username, password="passw0rd!", role=role, **extra
    )
    return user


def make_gate(name="Main Gate", code="MAIN"):
    return Gate.objects.create(name=name, code=code)


def make_student(reg_number="218001234", **extra):
    defaults = {"first_name": "Aline", "last_name": "Uwase"}
    defaults.update(extra)
    return Student.objects.create(reg_number=reg_number, **defaults)


def make_device(owner, serial_number="HP12345678", **extra):
    defaults = {"brand": "HP", "model_name": "EliteBook 840"}
    defaults.update(extra)
    return Device.objects.create(owner=owner, serial_number=serial_number, **defaults)


def api_client(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


def set_rule(key, value):
    """Set a policy rule the way the Registration Office portal would.

    Goes through the same validation the API uses, so a test cannot store a
    value the real screen would have refused - which would make the test prove
    something about a state the system cannot reach.
    """
    spec = rules.REGISTRY[key]
    Rule.objects.update_or_create(key=key, defaults={"value": spec.clean(value)})
    rules.invalidate()


def photo_bytes():
    """The smallest valid PNG, for tests that must supply a real image.

    Pillow validates uploads to an ImageField, so a text file called .png is
    rejected before the test gets anywhere near what it meant to check.
    """
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
