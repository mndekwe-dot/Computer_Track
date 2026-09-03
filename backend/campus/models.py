from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    faculty = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class Gate(models.Model):
    """A physical entry point manned by security.

    Gates are opened and closed by the registration office, not by a developer:
    a new service entrance is a fact about the campus, and the office that
    keeps the register is the one that knows about it first.
    """

    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Short label, e.g. MAIN, WEST")
    location = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)

    # Some gates are one-way by design: a delivery entrance that nothing leaves
    # through, a turnstile that only admits. The console hides the direction a
    # gate does not serve, so a guard cannot record a movement that cannot
    # physically have happened there.
    allows_entry = models.BooleanField(default=True)
    allows_exit = models.BooleanField(default=True)

    # Staffed hours. Left blank the gate is treated as always open. When they
    # are set, a scan outside them is still recorded - refusing to record it
    # would only mean the movement goes unlogged - but it is marked so the
    # office can ask why the west gate was busy at three in the morning.
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)

    contact_phone = models.CharField(
        max_length=40, blank=True, help_text="Reached from the console when a computer is held."
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def allows(self, direction):
        from checkpoint.models import Direction

        return self.allows_entry if direction == Direction.IN else self.allows_exit

    def is_open_at(self, moment):
        """Within staffed hours? True when no hours are set.

        Handles a gate whose hours cross midnight (22:00 to 06:00), which is
        exactly the shape a night gate has.
        """
        if not self.opens_at or not self.closes_at:
            return True
        now = moment.time()
        if self.opens_at <= self.closes_at:
            return self.opens_at <= now <= self.closes_at
        return now >= self.opens_at or now <= self.closes_at


class EquipmentType(models.Model):
    """A kind of equipment the register recognises.

    This was a fixed list in the code, which meant a university that checks
    lab oscilloscopes at the gate had to file a bug and wait for a release.
    It is a table now. `code` is what gets stored on a device and appears in
    exports, so it is immutable once used; `label` is what people read and can
    be reworded at any time.
    """

    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Stored on the record and used in exports. Upper case, no spaces.",
    )
    label = models.CharField(max_length=80, help_text="What a student and a guard see.")
    description = models.CharField(max_length=200, blank=True)
    # Student-facing: a university may register projectors without offering
    # "projector" as a choice on the student form.
    offered_to_students = models.BooleanField(
        default=True, help_text="Shown as a choice on the public student form."
    )
    is_active = models.BooleanField(
        default=True, help_text="Turn off to retire a type without touching existing records."
    )
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ("sort_order", "label")

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper().replace(" ", "_")
        super().save(*args, **kwargs)

    def devices_exist(self):
        """Is anything filed under this code?

        Asked before allowing the code to change, because the code is what is
        written onto each device row and into every export already taken.
        """
        from devices.models import Device

        return Device.objects.filter(device_type=self.code).exists()


class Rule(models.Model):
    """One stored policy value. See campus/rules.py for what may be stored.

    Only keys in that registry are accepted, and each is coerced and bounds
    checked on the way in, so this table cannot become an unvalidated dump.
    """

    key = models.CharField(max_length=80, unique=True)
    value = models.JSONField()
    updated_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="rules_set"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("key",)

    def __str__(self):
        return f"{self.key} = {self.value!r}"
