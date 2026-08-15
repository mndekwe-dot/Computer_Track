"""Small helpers so each test reads as the scenario it is testing."""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from campus.models import Gate
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
