"""Generates three professional, publication-quality UML diagrams in native draw.io format:
1. UML Class Diagram (Domain Model & Methods) -> class-diagram.drawio
2. UML Component Diagram (Subsystems, Ports & Interfaces) -> component-diagram.drawio
3. UML Activity Diagram with Swimlanes (Gate Verification & Offline Decision) -> activity-diagram.drawio

Combined with the existing use-case.drawio, this provides the required 4 UML diagram types.
"""

import html
import os

HEAD = (
    '<mxfile host="app.diagrams.net" type="device">\n'
    '  <diagram name="{name}" id="{did}">\n'
    '    <mxGraphModel dx="1600" dy="1100" grid="1" gridSize="10" guides="1" tooltips="1" '
    'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" '
    'math="0" shadow="0">\n      <root>\n'
    '        <mxCell id="0" /><mxCell id="1" parent="0" />\n'
)
TAIL = "      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"


def escape(s):
    return html.escape(s)


# ==============================================================================
# 1. UML CLASS DIAGRAM
# ==============================================================================
def build_class_diagram():
    out = []
    out.append(HEAD.format(name="UML Class Diagram", did="class_diagram", pw=1650, ph=1250))

    # Title
    out.append(
        '        <mxCell id="title" value="Computer Track — UML Class Diagram (Domain Model &amp; Core Operations)" '
        'style="text;html=1;fontSize=18;fontStyle=1;align=left;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="20" width="800" height="30" as="geometry"/></mxCell>\n'
    )

    # Class box builder
    def uml_class(cid, name, stereotype, attrs, methods, x, y, w, h, fill="#DAE8FC", stroke="#6C8EBF"):
        header = f"&lt;b&gt;{escape(name)}&lt;/b&gt;"
        if stereotype:
            header = f"&amp;laquo;{escape(stereotype)}&amp;raquo;&lt;br/&gt;" + header

        attr_block = "&lt;br/&gt;".join(escape(a) for a in attrs) if attrs else "&lt;i&gt;None&lt;/i&gt;"
        method_block = "&lt;br/&gt;".join(escape(m) for m in methods) if methods else ""

        val = f"{header}&lt;hr size=&quot;1&quot;/&gt;{attr_block}"
        if methods:
            val += f"&lt;hr size=&quot;1&quot;/&gt;{method_block}"

        style = (
            f"rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=6;fontSize=10;"
            f"fillColor={fill};strokeColor={stroke};fontColor=#000000;"
        )
        return (
            f'        <mxCell id="{cid}" value="{val}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    # Classes
    # Row 1: Department, Student, Device, Gate
    out.append(uml_class(
        "cls_dept", "Department", None,
        ["+ id: Integer", "+ code: String", "+ name: String", "+ faculty: String"],
        [], 40, 80, 200, 110, "#E1D5E7", "#9673A6"
    ))

    out.append(uml_class(
        "cls_student", "Student", None,
        [
            "+ id: Integer",
            "+ reg_number: String",
            "- reg_number_key: String",
            "+ first_name: String",
            "+ last_name: String",
            "+ email: String",
            "+ phone: String",
            "+ national_id: String",
            "+ programme: String",
            "+ year_of_study: Integer",
            "+ photo: Image",
            "+ status: StudentStatus",
        ],
        [
            "+ get_full_name(): String",
            "+ is_clear_to_pass(): Boolean",
        ],
        310, 80, 230, 270, "#DAE8FC", "#6C8EBF"
    ))

    out.append(uml_class(
        "cls_device", "Device", None,
        [
            "+ uid: UUID",
            "+ serial_number: String",
            "- serial_key: String",
            "+ asset_tag: String",
            "+ device_type: String",
            "+ brand: String",
            "+ model_name: String",
            "+ colour: String",
            "+ distinguishing_marks: String",
            "+ ownership: Ownership",
            "+ status: DeviceStatus",
            "+ purchase_details: String",
            "+ photo: Image",
            "+ is_archived: Boolean",
        ],
        [
            "+ label(): String",
            "+ active_flags(): List<DeviceFlag>",
            "+ valid_permits(): List<TemporaryPermit>",
            "+ blocking_reasons(): List<String>",
            "+ exit_restrictions(): List<String>",
            "+ is_blocked(): Boolean",
        ],
        630, 80, 260, 360, "#DAE8FC", "#6C8EBF"
    ))

    out.append(uml_class(
        "cls_scan", "ScanEvent", None,
        [
            "+ id: Integer",
            "+ direction: Direction",
            "+ verdict: Verdict",
            "+ method: LookupMethod",
            "+ claimed_serial: String",
            "+ claimed_reg_number: String",
            "+ device_label: String",
            "+ student_name: String",
            "+ bearer_name: String",
            "+ override_reason: String",
            "+ client_reference: String",
            "+ created_at: DateTime",
        ],
        [],
        980, 80, 230, 260, "#FFF2CC", "#D6B656"
    ))

    out.append(uml_class(
        "cls_gate", "Gate", None,
        [
            "+ id: Integer",
            "+ code: String",
            "+ name: String",
            "+ location: String",
            "+ allows_entry: Boolean",
            "+ allows_exit: Boolean",
            "+ opens_at: Time",
            "+ closes_at: Time",
            "+ contact_phone: String",
            "+ is_active: Boolean",
        ],
        [
            "+ allows(direction: Direction): Boolean",
            "+ is_open_at(moment: DateTime): Boolean",
        ],
        1300, 80, 240, 240, "#E1D5E7", "#9673A6"
    ))

    # Row 2 & Subordinate entities: RegistrationAttempt, DeviceFlag, TemporaryPermit, OwnershipTransfer, User
    out.append(uml_class(
        "cls_attempt", "RegistrationAttempt", None,
        [
            "+ id: Integer",
            "+ submitted_reg_number: String",
            "+ submitted_serial: String",
            "+ outcome: AttemptOutcome",
            "+ failure_reason: String",
            "+ ip_address: IPAddress",
            "+ created_at: DateTime",
        ],
        [],
        310, 420, 230, 160, "#F8CECC", "#B85450"
    ))

    out.append(uml_class(
        "cls_flag", "DeviceFlag", None,
        [
            "+ id: Integer",
            "+ reason: FlagReason",
            "+ details: String",
            "+ is_active: Boolean",
            "+ created_at: DateTime",
        ],
        [],
        630, 500, 220, 130, "#F8CECC", "#B85450"
    ))

    out.append(uml_class(
        "cls_permit", "TemporaryPermit", None,
        [
            "+ id: Integer",
            "+ bearer_name: String",
            "+ bearer_id_number: String",
            "+ relationship: String",
            "+ reason: String",
            "+ valid_from: DateTime",
            "+ valid_to: DateTime",
            "+ is_revoked: Boolean",
        ],
        [
            "+ is_valid_now(): Boolean",
        ],
        910, 420, 220, 180, "#D5E8D4", "#82B366"
    ))

    out.append(uml_class(
        "cls_transfer", "OwnershipTransfer", None,
        [
            "+ id: Integer",
            "+ reason: String",
            "+ transferred_at: DateTime",
        ],
        [],
        630, 680, 220, 90, "#DAE8FC", "#6C8EBF"
    ))

    out.append(uml_class(
        "cls_user", "User", "staff",
        [
            "+ id: Integer",
            "+ username: String",
            "+ role: Role",
            "+ staff_number: String",
            "+ phone: String",
            "+ is_active: Boolean",
        ],
        [],
        1300, 390, 200, 150, "#D5E8D4", "#82B366"
    ))

    # Row 3: Rule, EquipmentType, ReadAuditLog, Notification
    out.append(uml_class(
        "cls_rule", "Rule", "policy",
        [
            "+ key: String",
            "+ value: JSON",
        ],
        [
            "+ get(key: String): Any",
            "+ evaluate(): Boolean",
        ],
        40, 240, 200, 120, "#FFF2CC", "#D6B656"
    ))

    out.append(uml_class(
        "cls_equip", "EquipmentType", None,
        [
            "+ code: String",
            "+ label: String",
            "+ description: String",
            "+ offered_to_students: Boolean",
            "+ is_active: Boolean",
            "+ sort_order: Integer",
        ],
        [],
        40, 410, 200, 150, "#E1D5E7", "#9673A6"
    ))

    out.append(uml_class(
        "cls_audit", "ReadAuditLog", "audit",
        [
            "+ id: Integer",
            "+ endpoint: String",
            "+ target_model: String",
            "+ target_id: String",
            "+ ip_address: IPAddress",
            "+ created_at: DateTime",
        ],
        [],
        1300, 600, 200, 150, "#FFE6CC", "#D79B00"
    ))

    out.append(uml_class(
        "cls_notif", "Notification", "outbox",
        [
            "+ id: Integer",
            "+ kind: String",
            "+ channel: String",
            "+ recipient: String",
            "+ subject: String",
            "+ status: String",
            "+ attempts: Integer",
            "+ next_attempt_at: DateTime",
        ],
        [],
        980, 670, 220, 170, "#DAE8FC", "#6C8EBF"
    ))

    # Enumerations box
    enum_text = (
        "&lt;b&gt;&amp;laquo;enumeration&amp;raquo;&lt;br/&gt;StudentStatus&lt;/b&gt;&lt;br/&gt;"
        "ACTIVE, SUSPENDED, GRADUATED, WITHDRAWN&lt;hr size=&quot;1&quot;/&gt;"
        "&lt;b&gt;&amp;laquo;enumeration&amp;raquo;&lt;br/&gt;DeviceStatus&lt;/b&gt;&lt;br/&gt;"
        "PENDING, ACTIVE, LOST, STOLEN, RETIRED&lt;hr size=&quot;1&quot;/&gt;"
        "&lt;b&gt;&amp;laquo;enumeration&amp;raquo;&lt;br/&gt;Ownership&lt;/b&gt;&lt;br/&gt;"
        "STUDENT, UNIVERSITY&lt;hr size=&quot;1&quot;/&gt;"
        "&lt;b&gt;&amp;laquo;enumeration&amp;raquo;&lt;br/&gt;Verdict&lt;/b&gt;&lt;br/&gt;"
        "ALLOWED, DENIED, OVERRIDE, UNREGISTERED&lt;hr size=&quot;1&quot;/&gt;"
        "&lt;b&gt;&amp;laquo;enumeration&amp;raquo;&lt;br/&gt;Role&lt;/b&gt;&lt;br/&gt;"
        "ADMIN, REGISTRAR, GUARD"
    )
    out.append(
        f'        <mxCell id="enums" value="{enum_text}" style="rounded=0;whiteSpace=wrap;html=1;align=center;'
        f'verticalAlign=top;spacing=6;fontSize=9;fillColor=#F5F5F5;strokeColor=#666666;" vertex="1" parent="1">'
        f'<mxGeometry x="40" y="610" width="220" height="230" as="geometry"/></mxCell>\n'
    )

    # Relationships / Connectors
    def assoc(eid, src, dst, label="", head="none", tail="none", sfill=0, tfill=0, pts=None, spts=""):
        p_str = ""
        if pts:
            inner = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in pts)
            p_str = f'<Array as="points">{inner}</Array>'
        geom = f'<mxGeometry relative="1" as="geometry">{p_str}</mxGeometry>'

        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#333333;fontSize=10;"
            f"startArrow={tail};startFill={sfill};endArrow={head};endFill={tfill};"
            f"labelBackgroundColor=#FFFFFF;{spts}"
        )
        return f'        <mxCell id="{eid}" value="{label}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">{geom}</mxCell>\n'

    # Department 1 --- 0..* Student
    out.append(assoc("rel_dept_stu", "cls_dept", "cls_student", "1 has 0..*"))
    # Department 1 --- 0..* Device (university property)
    out.append(assoc("rel_dept_dev", "cls_dept", "cls_device", "1 owns 0..*", pts=[(140, 60), (760, 60)]))
    # Student 1 --- 0..* Device (student owned)
    out.append(assoc("rel_stu_dev", "cls_student", "cls_device", "1 owns 0..*"))
    # Student 1 --- 0..* RegistrationAttempt
    out.append(assoc("rel_stu_att", "cls_student", "cls_attempt", "1 submits 0..*"))
    # Device 1 *--- 0..* DeviceFlag (Composition)
    out.append(assoc("rel_dev_flag", "cls_device", "cls_flag", "1 carries 0..*", tail="diamond", sfill=1))
    # Device 1 *--- 0..* TemporaryPermit (Composition)
    out.append(assoc("rel_dev_perm", "cls_device", "cls_permit", "1 authorises 0..*", tail="diamond", sfill=1))
    # Device 1 --- 0..* ScanEvent
    out.append(assoc("rel_dev_scan", "cls_device", "cls_scan", "1 checked in 0..*"))
    # Student 0..1 --- 0..* ScanEvent
    out.append(assoc("rel_stu_scan", "cls_student", "cls_scan", "0..1 bearer in 0..*", pts=[(425, 60), (425, 40), (1050, 40), (1050, 80)]))
    # Gate 1 --- 0..* ScanEvent
    out.append(assoc("rel_gate_scan", "cls_gate", "cls_scan", "1 records 0..*"))
    # User 1 --- 0..* ScanEvent (Guard evaluated)
    out.append(assoc("rel_user_scan", "cls_user", "cls_scan", "1 decides 0..*", pts=[(1300, 470), (1150, 470), (1150, 340)]))
    # Device 1 --- 0..* OwnershipTransfer
    out.append(assoc("rel_dev_trans", "cls_device", "cls_transfer", "1 history 0..*"))
    # User 1 --- 0..* ReadAuditLog
    out.append(assoc("rel_user_audit", "cls_user", "cls_audit", "1 triggers 0..*"))
    # TemporaryPermit 0..1 --- 0..* ScanEvent
    out.append(assoc("rel_perm_scan", "cls_permit", "cls_scan", "0..1 linked 0..*"))

    # Architecture note
    note = (
        "&lt;b&gt;Design notes&lt;/b&gt;&lt;br/&gt;"
        "1. &lt;i&gt;Student&lt;/i&gt; is a record, not a login account. No student credentials exist.&lt;br/&gt;"
        "2. &lt;i&gt;Device.blocking_reasons()&lt;/i&gt; returns a combined list of all violations at once.&lt;br/&gt;"
        "3. &lt;i&gt;ScanEvent&lt;/i&gt; snapshots device_label and student_name to remain valid forever.&lt;br/&gt;"
        "4. Offline replays use &lt;i&gt;client_reference&lt;/i&gt; UUID for idempotency."
    )
    out.append(
        f'        <mxCell id="note" value="{note}" style="shape=note;whiteSpace=wrap;html=1;size=16;'
        f'fillColor=#FFFFFF;strokeColor=#999999;align=left;verticalAlign=top;spacingLeft=8;spacingTop=4;fontSize=10;" '
        f'vertex="1" parent="1"><mxGeometry x="310" y="620" width="270" height="150" as="geometry"/></mxCell>\n'
    )

    out.append(TAIL)
    return "".join(out)


# ==============================================================================
# 2. UML COMPONENT DIAGRAM
# ==============================================================================
def build_component_diagram():
    out = []
    out.append(HEAD.format(name="UML Component Diagram", did="component_diagram", pw=1600, ph=1100))

    # Title
    out.append(
        '        <mxCell id="title" value="Computer Track — UML Component Diagram (Subsystems, Ports &amp; Interfaces)" '
        'style="text;html=1;fontSize=18;fontStyle=1;align=left;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="20" width="800" height="30" as="geometry"/></mxCell>\n'
    )

    def sub_package(pid, label, x, y, w, h, stroke="#6C8EBF", fill="none"):
        return (
            f'        <mxCell id="{pid}" value="«subsystem»\n{escape(label)}" '
            f'style="rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};dashed=1;'
            f'verticalAlign=top;align=left;spacingLeft=10;fontSize=12;fontStyle=1;fontColor={stroke};" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    def uml_comp(cid, name, desc, x, y, w, h, fill="#DAE8FC", stroke="#6C8EBF"):
        val = f"&amp;laquo;component&amp;raquo;&lt;br/&gt;&lt;b&gt;{escape(name)}&lt;/b&gt;"
        if desc:
            val += f"&lt;br/&gt;&lt;font size=&quot;1&quot; color=&quot;#555555&quot;&gt;{escape(desc)}&lt;/font&gt;"
        style = (
            f"shape=module;align=center;verticalAlign=middle;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};fontSize=11;"
        )
        return (
            f'        <mxCell id="{cid}" value="{val}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    # 1. Presentation Tier (Client)
    out.append(sub_package("sub_client", "Presentation Tier (React 19 SPA / Client PWA)", 40, 80, 360, 860, "#6C8EBF"))
    out.append(uml_comp("c_guard_ui", "Security Gate Console", "Lookup, Photo Match, Clear/Hold/Override", 70, 130, 300, 65, "#DAE8FC", "#6C8EBF"))
    out.append(uml_comp("c_reg_ui", "Registration Office Portal", "Approvals, Student/Device Admin, Holds, Passes", 70, 220, 300, 65, "#DAE8FC", "#6C8EBF"))
    out.append(uml_comp("c_admin_ui", "Administration Dashboard", "Analytics, Rules, Staff, 2FA, Read-Audit", 70, 310, 300, 65, "#DAE8FC", "#6C8EBF"))
    out.append(uml_comp("c_public_ui", "Public Self-Service Form", "Unauthenticated Register, Report Lost, Status", 70, 400, 300, 65, "#DAE8FC", "#6C8EBF"))
    out.append(uml_comp("c_sw", "Service Worker Shell", "PWA App Shell Caching (Workbox)", 70, 520, 300, 65, "#E1D5E7", "#9673A6"))
    out.append(uml_comp("c_queue", "Offline Queue Engine", "IndexedDB/LocalStorage + UUID Idempotency", 70, 610, 300, 65, "#E1D5E7", "#9673A6"))

    # 2. Application & API Tier (Backend Django)
    out.append(sub_package("sub_api", "Application Tier (Django 5 REST API & Core Services)", 470, 80, 520, 860, "#82B366"))
    out.append(uml_comp("c_gateway", "API Gateway & Auth", "SimpleJWT, 2FA TOTP, Rate Limiting, JSON Errors", 500, 130, 460, 65, "#D5E8D4", "#82B366"))
    out.append(uml_comp("c_checkpoint_svc", "Checkpoint Service", "Gate Lookups, Decision Engine, Append-Only Log", 500, 230, 460, 65, "#D5E8D4", "#82B366"))
    out.append(uml_comp("c_device_svc", "Device Management Service", "Devices, Flags, Passes, Transfers, Public Ingest", 500, 330, 460, 65, "#D5E8D4", "#82B366"))
    out.append(uml_comp("c_student_svc", "Student Registry Service", "Student CRUD, CSV Bulk Ingest, Identity Checks", 500, 430, 460, 65, "#D5E8D4", "#82B366"))
    out.append(uml_comp("c_policy_svc", "Policy & Rule Store", "Code Registry, JSON Rule DB, Runtime Evaluator", 500, 530, 460, 65, "#FFF2CC", "#D6B656"))
    out.append(uml_comp("c_search_svc", "Inverted Search Indexer", "Normalized Reg & Serial Fast Index (<100ms)", 500, 630, 460, 65, "#D5E8D4", "#82B366"))
    out.append(uml_comp("c_audit_svc", "Audit & Anomaly Detector", "Read-Audit Log, Velocity Checks, Alert Triggers", 500, 730, 460, 65, "#FFE6CC", "#D79B00"))

    # 3. Persistence & Messaging Tier
    out.append(sub_package("sub_data", "Persistence & Asynchronous Task Tier", 1060, 80, 480, 430, "#B85450"))
    out.append(uml_comp("c_db", "PostgreSQL Database", "Relational Models, Constraints, Audit History", 1100, 130, 400, 65, "#F8CECC", "#B85450"))
    out.append(uml_comp("c_redis", "Redis Cache & Broker", "Session Cache, Throttling, Celery Task Broker", 1100, 225, 400, 65, "#F8CECC", "#B85450"))
    out.append(uml_comp("c_celery", "Celery Worker & Beat", "Outbox Dispatch, Audit Sweepers, Hourly Metrics", 1100, 320, 400, 65, "#F8CECC", "#B85450"))
    out.append(uml_comp("c_media", "Expiring Media Storage", "HMAC Signed Photo URLs (No raw public exposure)", 1100, 415, 400, 65, "#F8CECC", "#B85450"))

    # 4. External Services Tier
    out.append(sub_package("sub_ext", "External Providers (Third-Party Cloud Gateways)", 1060, 560, 480, 380, "#9673A6"))
    out.append(uml_comp("c_sms", "Africa's Talking SMS Gateway", "HTTPS REST API (Exit alerts, Hold notices)", 1100, 620, 400, 65, "#E1D5E7", "#9673A6"))
    out.append(uml_comp("c_mail", "Resend Email Delivery API", "HTTPS API (Approval confirmations, Pass links)", 1100, 720, 400, 65, "#E1D5E7", "#9673A6"))

    # Interfaces & Connectors
    def c_edge(eid, src, dst, label="", style_extra=""):
        return (
            f'        <mxCell id="{eid}" value="{label}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;'
            f'strokeColor=#4D5A66;fontSize=10;labelBackgroundColor=#FFFFFF;{style_extra}" '
            f'edge="1" parent="1" source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry"/></mxCell>\n'
        )

    # Client to Gateway
    out.append(c_edge("e_g1", "c_guard_ui", "c_gateway", "HTTPS / REST (JWT)"))
    out.append(c_edge("e_g2", "c_reg_ui", "c_gateway", "HTTPS / REST (JWT)"))
    out.append(c_edge("e_g3", "c_admin_ui", "c_gateway", "HTTPS / REST (TOTP)"))
    out.append(c_edge("e_g4", "c_public_ui", "c_gateway", "HTTPS / REST (Public)"))

    # Offline engine to checkpoint
    out.append(c_edge("e_q1", "c_queue", "c_checkpoint_svc", "Replay Queue on reconnect", "dashed=1;"))

    # Gateway routing to services
    out.append(c_edge("e_svc1", "c_gateway", "c_checkpoint_svc", "/api/checkpoint/*"))
    out.append(c_edge("e_svc2", "c_gateway", "c_device_svc", "/api/devices/*"))
    out.append(c_edge("e_svc3", "c_gateway", "c_student_svc", "/api/students/*"))

    # Checkpoint uses Policy & Search
    out.append(c_edge("e_cp_pol", "c_checkpoint_svc", "c_policy_svc", "Evaluates Gate Rules"))
    out.append(c_edge("e_cp_srch", "c_checkpoint_svc", "c_search_svc", "Lookup Token Query"))

    # Services to Database
    out.append(c_edge("e_db1", "c_checkpoint_svc", "c_db", "SQL (psycopg3)", style_extra="exitX=1;exitY=0.5;entryX=0;entryY=0.5;"))
    out.append(c_edge("e_db2", "c_device_svc", "c_db", "ORM Write"))
    out.append(c_edge("e_db3", "c_policy_svc", "c_redis", "Rule Cache"))

    # Celery to External
    out.append(c_edge("e_cel_sms", "c_celery", "c_sms", "HTTP POST SMS Outbox"))
    out.append(c_edge("e_cel_mail", "c_celery", "c_mail", "HTTP POST Mail Outbox"))

    out.append(TAIL)
    return "".join(out)


# ==============================================================================
# 3. UML ACTIVITY DIAGRAM WITH SWIMLANES
# ==============================================================================
def build_activity_diagram():
    out = []
    out.append(HEAD.format(name="UML Activity Diagram", did="activity_diagram", pw=1600, ph=1400))

    # Title
    out.append(
        '        <mxCell id="title" value="Computer Track — UML Activity Diagram (Gate Verification &amp; Edge Override Flow)" '
        'style="text;html=1;fontSize=18;fontStyle=1;align=left;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="20" width="850" height="30" as="geometry"/></mxCell>\n'
    )

    # 4 Swimlanes
    SW_W = 360
    SW_H = 1250
    LANES = [
        ("lane_guard", "Security Guard (Human Actor)", 40, 70, SW_W, SW_H, "#EAF2FB", "#4A6E96"),
        ("lane_client", "Gate Console (React PWA Client)", 400, 70, SW_W, SW_H, "#E8F5E9", "#388E3C"),
        ("lane_backend", "Backend API & Policy Engine", 760, 70, SW_W, SW_H, "#FFF8E1", "#FFA000"),
        ("lane_audit", "Audit Log & Background Services", 1120, 70, SW_W, SW_H, "#F3E5F5", "#7B1FA2"),
    ]

    for lid, lname, lx, ly, lw, lh, lfill, lstroke in LANES:
        out.append(
            f'        <mxCell id="{lid}" value="{escape(lname)}" style="shape=swimlane;startSize=34;'
            f'horizontal=1;whiteSpace=wrap;html=1;fillColor={lfill};strokeColor={lstroke};fontStyle=1;'
            f'fontSize=12;align=center;collapsible=0;" vertex="1" parent="1">'
            f'<mxGeometry x="{lx}" y="{ly}" width="{lw}" height="{lh}" as="geometry"/></mxCell>\n'
        )

    # Helper nodes inside parent lanes or absolute parent=1 coordinates
    def act(nid, label, x, y, w, h, fill="#FFFFFF", stroke="#4A6E96"):
        return (
            f'        <mxCell id="{nid}" value="{escape(label)}" style="rounded=1;arcSize=24;whiteSpace=wrap;'
            f'html=1;fillColor={fill};strokeColor={stroke};fontSize=11;align=center;" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    def dec(nid, label, x, y, w, h):
        return (
            f'        <mxCell id="{nid}" value="{escape(label)}" style="rhombus;whiteSpace=wrap;html=1;'
            f'fillColor=#FFF2CC;strokeColor=#D6B656;fontSize=10;align=center;" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    # Initial Node (in Guard lane)
    out.append(
        '        <mxCell id="init" value="" style="ellipse;fillColor=#000000;strokeColor=none;" vertex="1" parent="1">'
        '<mxGeometry x="205" y="120" width="28" height="28" as="geometry"/></mxCell>\n'
    )

    # Guard actions
    out.append(act("a_intercept", "Intercept bearer carrying device at campus gate", 85, 175, 270, 45, "#DAE8FC", "#4A6E96"))
    out.append(act("a_scan", "Scan QR sticker OR type serial / reg number", 85, 250, 270, 45, "#DAE8FC", "#4A6E96"))

    # Client actions
    out.append(dec("d_net", "Network\navailable?", 490, 240, 180, 65))
    out.append(act("a_queue", "Enqueue scan locally with UUID client_reference", 445, 335, 270, 45, "#FFE6CC", "#D79B00"))
    out.append(act("a_req", "Dispatch lookup request to /api/checkpoint/lookup/", 445, 410, 270, 45, "#D5E8D4", "#82B366"))

    # Backend actions
    out.append(act("a_query", "Query Inverted Index & retrieve Student/Device records", 805, 410, 270, 50, "#FFF2CC", "#D6B656"))
    out.append(act("a_eval", "Execute blocking_reasons() & policy rule checks", 805, 490, 270, 50, "#FFF2CC", "#D6B656"))
    out.append(dec("d_block", "Any blocking hold\nor unregistered?", 850, 570, 180, 70))

    # Back to Client & Guard for Decision
    out.append(act("a_display", "Display owner photo, specs, and status banner (CLEAR / HOLD)", 445, 660, 270, 55, "#D5E8D4", "#82B366"))
    out.append(act("a_verify_photo", "Visually verify bearer matches owner photo & markings", 85, 665, 270, 45, "#DAE8FC", "#4A6E96"))
    out.append(dec("d_allow", "Visual check passed\n& no blocking hold?", 130, 740, 180, 70))

    # Override / Deny branch
    out.append(dec("d_override", "Guard exercises\noverride?", 130, 845, 180, 70))
    out.append(act("a_enter_reason", "Enter mandatory written override justification", 85, 950, 270, 45, "#FFF2CC", "#D6B656"))
    out.append(act("a_deny", "Deny exit & detain device for investigation", 85, 1030, 270, 45, "#F8CECC", "#B85450"))

    # Record scan on Client
    out.append(act("a_post_scan", "Submit scan verdict (ALLOWED / OVERRIDE / DENIED)", 445, 945, 270, 50, "#D5E8D4", "#82B366"))

    # Fork bar in Audit/Backend
    out.append(
        '        <mxCell id="fork1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=#000000;" '
        'vertex="1" parent="1"><mxGeometry x="840" y="965" width="200" height="6" as="geometry"/></mxCell>\n'
    )

    # Parallel tasks in Audit
    out.append(act("a_log_scan", "Commit immutable ScanEvent record to audit database", 1165, 920, 270, 45, "#E1D5E7", "#7B1FA2"))
    out.append(act("a_read_audit", "Record query to ReadAuditLog for staff accountability", 1165, 985, 270, 45, "#E1D5E7", "#7B1FA2"))
    out.append(act("a_notif", "Trigger SMS / Email exit notification if rule enabled", 1165, 1050, 270, 45, "#E1D5E7", "#7B1FA2"))

    # Join bar
    out.append(
        '        <mxCell id="join1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=#000000;" '
        'vertex="1" parent="1"><mxGeometry x="1200" y="1120" width="200" height="6" as="geometry"/></mxCell>\n'
    )

    # Final Node (in Guard lane)
    out.append(act("a_pass", "Allow student to pass through gate", 85, 1140, 270, 45, "#D5E8D4", "#82B366"))
    out.append(
        '        <mxCell id="fin" value="" style="shape=doubleEllipse;fillColor=#000000;strokeColor=#000000;strokeWidth=2;" '
        'vertex="1" parent="1"><mxGeometry x="205" y="1220" width="28" height="28" as="geometry"/></mxCell>\n'
    )

    # Connectors
    def a_edge(eid, src, dst, label="", pts=None):
        p_str = ""
        if pts:
            inner = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in pts)
            p_str = f'<Array as="points">{inner}</Array>'
        geom = f'<mxGeometry relative="1" as="geometry">{p_str}</mxGeometry>'
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#333333;fontSize=10;"
            "labelBackgroundColor=#FFFFFF;"
        )
        return f'        <mxCell id="{eid}" value="{label}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">{geom}</mxCell>\n'

    out.append(a_edge("e1", "init", "a_intercept"))
    out.append(a_edge("e2", "a_intercept", "a_scan"))
    out.append(a_edge("e3", "a_scan", "d_net"))
    out.append(a_edge("e4", "d_net", "a_queue", "[Offline: Network drop]"))
    out.append(a_edge("e5", "d_net", "a_req", "[Online]"))
    out.append(a_edge("e6", "a_queue", "a_req", "[On reconnect: flush queue]", pts=[(580, 395)]))
    out.append(a_edge("e7", "a_req", "a_query"))
    out.append(a_edge("e8", "a_query", "a_eval"))
    out.append(a_edge("e9", "a_eval", "d_block"))
    out.append(a_edge("e10", "d_block", "a_display", "Verdict recommendation", pts=[(940, 685)]))
    out.append(a_edge("e11", "a_display", "a_verify_photo"))
    out.append(a_edge("e12", "a_verify_photo", "d_allow"))
    out.append(a_edge("e13", "d_allow", "a_pass", "[Pass: Clear to leave]", pts=[(40, 775), (40, 1162)]))
    out.append(a_edge("e14", "d_allow", "d_override", "[Mismatch or Hold]"))
    out.append(a_edge("e15", "d_override", "a_enter_reason", "[Yes: Override]"))
    out.append(a_edge("e16", "d_override", "a_deny", "[No: Enforce Hold]", pts=[(330, 880), (330, 1052)]))
    out.append(a_edge("e17", "a_enter_reason", "a_post_scan"))
    out.append(a_edge("e18", "a_post_scan", "fork1"))
    out.append(a_edge("e19", "fork1", "a_log_scan", "", pts=[(940, 942)]))
    out.append(a_edge("e20", "fork1", "a_read_audit", "", pts=[(940, 1007)]))
    out.append(a_edge("e21", "fork1", "a_notif", "", pts=[(940, 1072)]))
    out.append(a_edge("e22", "a_log_scan", "join1"))
    out.append(a_edge("e23", "a_read_audit", "join1"))
    out.append(a_edge("e24", "a_notif", "join1"))
    out.append(a_edge("e25", "a_pass", "fin"))
    out.append(a_edge("e26", "a_deny", "fin", "", pts=[(219, 1100), (219, 1220)]))

    out.append(TAIL)
    return "".join(out)


def main():
    target_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Class diagram
    cls_path = os.path.join(target_dir, "class-diagram.drawio")
    with open(cls_path, "w", encoding="utf-8") as f:
        f.write(build_class_diagram())
    print(f"Generated: {cls_path}")

    # 2. Component diagram
    comp_path = os.path.join(target_dir, "component-diagram.drawio")
    with open(comp_path, "w", encoding="utf-8") as f:
        f.write(build_component_diagram())
    print(f"Generated: {comp_path}")

    # 3. Activity diagram
    try:
        from build_taste_activity import build_taste_activity_diagram
        act_content = build_taste_activity_diagram()
    except ImportError:
        from .build_taste_activity import build_taste_activity_diagram
        act_content = build_taste_activity_diagram()

    act_path = os.path.join(target_dir, "activity-diagram.drawio")
    with open(act_path, "w", encoding="utf-8") as f:
        f.write(act_content)
    print(f"Generated: {act_path}")


if __name__ == "__main__":
    main()

