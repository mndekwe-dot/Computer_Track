"""Populate the database with realistic demo data.

    python manage.py seed_demo

Safe to run more than once - everything is looked up before it is created.
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from campus.models import Department, Gate
from checkpoint.models import Direction, LookupMethod, ScanEvent, Verdict
from devices.models import Device, DeviceFlag, DeviceStatus, FlagReason, TemporaryPermit
from students.models import Student, StudentStatus

User = get_user_model()

DEPARTMENTS = [
    ("Computer Science", "CS", "Science and Technology"),
    ("Information Systems", "IS", "Science and Technology"),
    ("Electrical Engineering", "EE", "Engineering"),
    ("Business Administration", "BA", "Business"),
    ("Nursing", "NUR", "Health Sciences"),
]

GATES = [
    ("Main Gate", "MAIN", "Front entrance, administration block"),
    ("West Gate", "WEST", "Beside the library car park"),
    ("Hostel Gate", "HOSTEL", "Student residences"),
    ("Service Gate", "SERVICE", "Deliveries and workshops"),
]

FIRST_NAMES = [
    "Aline", "Bosco", "Chantal", "David", "Esther", "Fabrice", "Grace", "Hakim",
    "Ines", "Jean", "Keza", "Liliane", "Moses", "Nadia", "Olivier", "Patience",
    "Queen", "Robert", "Sandrine", "Thierry", "Umutoni", "Vincent", "Wilson", "Yvette",
]
LAST_NAMES = [
    "Uwase", "Mugisha", "Ingabire", "Nkurunziza", "Mukamana", "Habimana", "Iradukunda",
    "Niyonzima", "Umuhoza", "Bizimana", "Kagabo", "Mutesi", "Rwigema", "Shema",
]
BRANDS = [
    ("HP", ["EliteBook 840", "ProBook 450", "Pavilion 15"]),
    ("Dell", ["Latitude 5420", "Inspiron 15", "XPS 13"]),
    ("Lenovo", ["ThinkPad T14", "IdeaPad 3", "Yoga Slim 7"]),
    ("Apple", ["MacBook Air M2", "MacBook Pro 14"]),
    ("Acer", ["Aspire 5", "Swift 3"]),
]
COLOURS = ["Silver", "Black", "Space grey", "Dark blue", "White"]
MARKS = [
    "Blue sticker on lid",
    "Cracked bottom-left corner of screen bezel",
    "Owner's name engraved under the palm rest",
    "Faded university sticker",
    "Red tape on the charger",
    "",
]


class Command(BaseCommand):
    help = "Create demo departments, gates, staff accounts, students, devices and gate logs."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=40)
        parser.add_argument("--scans", type=int, default=120)

    def handle(self, *args, **options):
        random.seed(20260815)

        departments = [
            Department.objects.get_or_create(
                code=code, defaults={"name": name, "faculty": faculty}
            )[0]
            for name, code, faculty in DEPARTMENTS
        ]
        gates = [
            Gate.objects.get_or_create(code=code, defaults={"name": name, "location": location})[0]
            for name, code, location in GATES
        ]
        self.stdout.write(f"Departments: {len(departments)}   Gates: {len(gates)}")

        staff = self._create_staff(gates)
        students = self._create_students(departments, options["students"])
        devices = self._create_devices(students, staff["registrar"])
        self._create_flags_and_permits(devices, staff["admin"])
        self._create_scans(devices, gates, staff["guards"], options["scans"])

        self.stdout.write(self.style.SUCCESS("\nDemo data ready. Sign in with:"))
        for username, role in [
            ("admin", "administrator"),
            ("registrar", "registration officer"),
            ("guard1", "guard - Main Gate"),
            ("guard2", "guard - West Gate"),
        ]:
            self.stdout.write(f"  {username} / passw0rd!  ({role})")

    def _create_staff(self, gates):
        def make(username, first, last, role, gate=None, staff_number=None):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "default_gate": gate,
                    "staff_number": staff_number,
                    "email": f"{username}@university.edu",
                },
            )
            if created:
                user.set_password("passw0rd!")
                if role == "ADMIN":
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
            return user

        admin = make("admin", "System", "Administrator", "ADMIN", staff_number="STF-001")
        registrar = make("registrar", "Claudine", "Mukamana", "REGISTRAR", staff_number="STF-002")
        guards = [
            make("guard1", "Emmanuel", "Nsengiyumva", "GUARD", gates[0], "SEC-101"),
            make("guard2", "Alphonse", "Rukundo", "GUARD", gates[1], "SEC-102"),
            make("guard3", "Josiane", "Uwera", "GUARD", gates[2], "SEC-103"),
        ]
        self.stdout.write(f"Staff accounts: {2 + len(guards)}")
        return {"admin": admin, "registrar": registrar, "guards": guards}

    def _create_students(self, departments, count):
        students = []
        for index in range(count):
            reg_number = f"21{random.randint(4, 8)}{100000 + index:06d}"
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            status = StudentStatus.ACTIVE
            if index % 17 == 0:
                status = StudentStatus.SUSPENDED
            elif index % 23 == 0:
                status = StudentStatus.GRADUATED
            department = random.choice(departments)
            student, _ = Student.objects.get_or_create(
                reg_number=reg_number,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{first.lower()}.{last.lower()}@student.university.edu",
                    "phone": f"+2507{random.randint(10000000, 89999999)}",
                    "department": department,
                    "programme": f"BSc {department.name}",
                    "year_of_study": random.randint(1, 4),
                    "status": status,
                },
            )
            students.append(student)
        self.stdout.write(f"Students: {len(students)}")
        return students

    def _create_devices(self, students, registrar):
        devices = []
        for index, student in enumerate(students):
            # Roughly one in eight students owns no computer, and a few own two.
            owned = 0 if index % 8 == 3 else (2 if index % 11 == 5 else 1)
            for slot in range(owned):
                brand, models = random.choice(BRANDS)
                serial = f"{brand[:2].upper()}{random.randint(10**8, 10**9 - 1)}"
                device, _ = Device.objects.get_or_create(
                    serial_number=serial,
                    defaults={
                        "brand": brand,
                        "model_name": random.choice(models),
                        "colour": random.choice(COLOURS),
                        "distinguishing_marks": random.choice(MARKS),
                        "owner": student,
                        "asset_tag": f"UNI-{2400 + len(devices):05d}",
                        "status": DeviceStatus.PENDING if index % 19 == 0 else DeviceStatus.ACTIVE,
                        "registered_by": registrar,
                    },
                )
                devices.append(device)
        self.stdout.write(f"Devices: {len(devices)}")
        return devices

    def _create_flags_and_permits(self, devices, admin):
        stolen = devices[4]
        stolen.status = DeviceStatus.STOLEN
        stolen.save()
        DeviceFlag.objects.get_or_create(
            device=stolen,
            reason=FlagReason.STOLEN,
            defaults={
                "details": "Reported taken from the library reading room on 3 August.",
                "raised_by": admin,
            },
        )

        disputed = devices[9]
        DeviceFlag.objects.get_or_create(
            device=disputed,
            reason=FlagReason.OWNERSHIP_DISPUTE,
            defaults={
                "details": "Two students presented receipts for this serial. Under review.",
                "raised_by": admin,
            },
        )

        borrowed = devices[2]
        TemporaryPermit.objects.get_or_create(
            device=borrowed,
            bearer_name="Patrick Habimana",
            defaults={
                "bearer_id_number": "216100045",
                "relationship": "Classmate",
                "reason": "Group project - owner is on teaching practice this week.",
                "valid_from": timezone.now() - timedelta(days=1),
                "valid_to": timezone.now() + timedelta(days=5),
                "issued_by": admin,
            },
        )
        self.stdout.write("Flags: 2   Permits: 1")

    def _create_scans(self, devices, gates, guards, count):
        if ScanEvent.objects.exists():
            self.stdout.write("Scan log already has entries - skipping.")
            return

        now = timezone.now()
        created = 0
        for _ in range(count):
            device = random.choice(devices)
            gate = random.choice(gates)
            guard = random.choice(guards)
            direction = random.choice([Direction.IN, Direction.OUT])
            blocked = device.is_blocked

            if blocked:
                verdict = Verdict.DENIED if random.random() < 0.8 else Verdict.OVERRIDE
            else:
                verdict = Verdict.ALLOWED

            ScanEvent.objects.create(
                device=device,
                student=device.owner,
                gate=gate,
                guard=guard,
                direction=direction,
                verdict=verdict,
                method=random.choice(
                    [LookupMethod.REG_NUMBER, LookupMethod.REG_NUMBER, LookupMethod.QR]
                ),
                override_reason=(
                    "Cleared by security control over the radio." if verdict == Verdict.OVERRIDE else ""
                ),
                client_timestamp=now - timedelta(minutes=random.randint(0, 60 * 24 * 6)),
            )
            created += 1

        # A couple of unregistered-device incidents for the dashboard.
        for _ in range(3):
            ScanEvent.objects.create(
                gate=random.choice(gates),
                guard=random.choice(guards),
                direction=Direction.OUT,
                verdict=Verdict.UNREGISTERED,
                method=LookupMethod.MANUAL,
                claimed_serial=f"UNKNOWN{random.randint(1000, 9999)}",
                notes="Laptop presented without any registration record. Sent to the registrar.",
                client_timestamp=now - timedelta(hours=random.randint(1, 72)),
            )
            created += 1

        self.stdout.write(f"Scan events: {created}")
