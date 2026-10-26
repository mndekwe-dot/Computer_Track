"""Generates a draw.io ERD with classic table shapes: coloured header, white body,
orthogonal crow's foot relationships, laid out on a grid instead of auto-routed."""

HEADER_H = 28
ROW_H = 22
W = 265
KEY_W = 38

ENTITIES = {
    "DEPARTMENT": (40, 40, [
        ("PK", "id"), ("", "code"), ("", "name"), ("", "faculty"),
    ]),
    "EQUIPMENT_TYPE": (40, 230, [
        ("PK", "id"), ("", "code"), ("", "label"), ("", "offered_to_students"), ("", "is_active"),
    ]),
    "STUDENT": (380, 40, [
        ("PK", "id"), ("", "reg_number"), ("", "first_name"), ("", "last_name"),
        ("", "email"), ("", "phone"), ("", "national_id"), ("", "status"),
        ("FK", "department_id"),
    ]),
    "REGISTRATION_ATTEMPT": (380, 400, [
        ("PK", "id"), ("", "reg_number"), ("", "serial_number"), ("", "outcome"),
        ("", "ip_address"), ("", "created_at"), ("FK", "student_id"),
    ]),
    "DEVICE": (720, 40, [
        ("PK", "id"), ("", "serial_number"), ("", "asset_tag"), ("", "device_type"),
        ("", "brand"), ("", "colour"), ("", "ownership"), ("", "status"),
        ("", "is_archived"), ("FK", "owner_id"), ("FK", "department_id"),
    ]),
    "DEVICE_FLAG": (720, 420, [
        ("PK", "id"), ("", "reason"), ("", "details"), ("", "is_active"),
        ("", "created_at"), ("FK", "device_id"),
    ]),
    "TEMPORARY_PERMIT": (720, 630, [
        ("PK", "id"), ("", "bearer_name"), ("", "valid_from"), ("", "valid_to"),
        ("", "is_revoked"), ("FK", "device_id"),
    ]),
    "SCAN_EVENT": (1060, 40, [
        ("PK", "id"), ("", "direction"), ("", "verdict"), ("", "method"),
        ("", "device_label"), ("", "student_name"), ("", "override_reason"),
        ("", "client_reference"), ("", "created_at"),
        ("FK", "device_id"), ("FK", "gate_id"), ("FK", "guard_id"),
    ]),
    "GATE": (1400, 40, [
        ("PK", "id"), ("", "code"), ("", "name"), ("", "location"),
        ("", "allows_entry"), ("", "allows_exit"), ("", "is_active"),
    ]),
    "APP_USER": (1400, 260, [
        ("PK", "id"), ("", "username"), ("", "role"), ("", "staff_number"), ("", "is_active"),
    ]),
}

# source, target, label, exit side, entry side, dashed, waypoints
# Waypoints keep the two long edges out of the STUDENT box: DEPARTMENT to DEVICE
# routes over the top, EQUIPMENT_TYPE to DEVICE routes through the gap below
# STUDENT and above REGISTRATION_ATTEMPT.
EDGES = [
    ("DEPARTMENT", "STUDENT", "has", "right", "left", False, []),
    ("DEPARTMENT", "DEVICE", "owns", "top", "top", False, [(172, 12), (852, 12)]),
    ("EQUIPMENT_TYPE", "DEVICE", "classifies by code", "right", "left_low", True, [(690, 299)]),
    ("STUDENT", "DEVICE", "owns", "right", "left", False, []),
    ("STUDENT", "REGISTRATION_ATTEMPT", "attempted by", "bottom", "top", False, []),
    ("DEVICE", "DEVICE_FLAG", "carries", "bottom", "top", False, []),
    ("DEVICE", "TEMPORARY_PERMIT", "authorised by", "bottom_right", "right", False, [(1010, 305), (1010, 700)]),
    ("DEVICE", "SCAN_EVENT", "verified in", "right", "left", False, []),
    ("GATE", "SCAN_EVENT", "records", "left", "right", False, []),
    ("APP_USER", "SCAN_EVENT", "guard decides", "left", "right", False, []),
]

SIDES = {
    "left":     (0, 0.5),   "right":        (1, 0.5),
    "top":      (0.5, 0),   "bottom":       (0.5, 1),
    "left_low": (0, 0.85),  "bottom_right": (0.8, 1),
}

TABLE_STYLE = (
    "shape=table;startSize={h};container=1;collapsible=0;childLayout=tableLayout;"
    "fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;html=1;"
    "fillColor=#F8CECC;strokeColor=#B85450;swimlaneFillColor=#FFFFFF;fontSize=12;"
).format(h=HEADER_H)

ROW_STYLE = (
    "shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=0;"
    "fillColor=none;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];"
    "portConstraint=eastwest;top=0;left=0;right=0;bottom=0;"
)

CELL_KEY = (
    "shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;"
    "fontStyle=1;overflow=hidden;whiteSpace=wrap;html=1;align=center;fontSize=10;fontColor=#7A3B36;"
)
CELL_NAME = (
    "shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;"
    "align=left;spacingLeft=6;overflow=hidden;whiteSpace=wrap;html=1;fontSize=11;"
)

out = []
out.append('<mxfile host="app.diagrams.net" type="device">')
out.append('  <diagram name="ERD" id="erd">')
out.append('    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" '
           'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
           'pageWidth="1700" pageHeight="1100" math="0" shadow="0">')
out.append('      <root>')
out.append('        <mxCell id="0" /><mxCell id="1" parent="0" />')

out.append('        <mxCell id="title" value="Computer Track - Entity Relationship Diagram" '
           'style="text;html=1;fontSize=20;fontStyle=1;align=left;" vertex="1" parent="1">'
           '<mxGeometry x="40" y="-60" width="700" height="30" as="geometry"/></mxCell>')

for name, (x, y, attrs) in ENTITIES.items():
    h = HEADER_H + ROW_H * len(attrs)
    tid = name.lower()
    out.append(f'        <mxCell id="{tid}" value="{name}" style="{TABLE_STYLE}" vertex="1" parent="1">'
               f'<mxGeometry x="{x}" y="{y}" width="{W}" height="{h}" as="geometry"/></mxCell>')
    for idx, (key, field) in enumerate(attrs):
        rid = f'{tid}_r{idx}'
        ry = HEADER_H + ROW_H * idx
        out.append(f'        <mxCell id="{rid}" value="" style="{ROW_STYLE}" vertex="1" parent="{tid}">'
                   f'<mxGeometry y="{ry}" width="{W}" height="{ROW_H}" as="geometry"/></mxCell>')
        out.append(f'        <mxCell id="{rid}_k" value="{key}" style="{CELL_KEY}" vertex="1" parent="{rid}">'
                   f'<mxGeometry width="{KEY_W}" height="{ROW_H}" as="geometry">'
                   f'<mxRectangle width="{KEY_W}" height="{ROW_H}" as="alternateBounds"/></mxGeometry></mxCell>')
        out.append(f'        <mxCell id="{rid}_n" value="{field}" style="{CELL_NAME}" vertex="1" parent="{rid}">'
                   f'<mxGeometry x="{KEY_W}" width="{W - KEY_W}" height="{ROW_H}" as="geometry">'
                   f'<mxRectangle width="{W - KEY_W}" height="{ROW_H}" as="alternateBounds"/></mxGeometry></mxCell>')

for n, (src, dst, label, ex, en, dashed, points) in enumerate(EDGES):
    exx, exy = SIDES[ex]
    enx, eny = SIDES[en]
    style = (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;jumpStyle=arc;jumpSize=8;"
        f"exitX={exx};exitY={exy};exitDx=0;exitDy=0;entryX={enx};entryY={eny};entryDx=0;entryDy=0;"
        "startArrow=ERone;startFill=0;endArrow=ERmany;endFill=0;strokeColor=#4D5A66;fontSize=10;"
        "labelBackgroundColor=#FFFFFF;"
        + ("dashed=1;" if dashed else "")
    )
    geom = '<mxGeometry relative="1" as="geometry"/>'
    if points:
        pts = ''.join(f'<mxPoint x="{px}" y="{py}" />' for px, py in points)
        geom = f'<mxGeometry relative="1" as="geometry"><Array as="points">{pts}</Array></mxGeometry>'
    out.append(f'        <mxCell id="e{n}" value="{label}" style="{style}" edge="1" parent="1" '
               f'source="{src.lower()}" target="{dst.lower()}">{geom}</mxCell>')

note = (
    "&lt;b&gt;Notes&lt;/b&gt;&lt;br&gt;"
    "1. EQUIPMENT_TYPE to DEVICE is dashed: device_type stores the type &lt;i&gt;code&lt;/i&gt;, not a "
    "foreign key, so a scan recorded last year still reads correctly after a registrar renames the type. "
    "The code is validated against the table on write.&lt;br&gt;"
    "2. device_label and student_name on SCAN_EVENT intentionally duplicate the register. They are "
    "snapshotted at decision time so history survives a later rename or ownership transfer.&lt;br&gt;"
    "3. Staff foreign keys (registered_by, raised_by, resolved_by, issued_by) all reference APP_USER "
    "and are omitted for legibility."
)
out.append(f'        <mxCell id="note" value="{note}" '
           'style="shape=note;whiteSpace=wrap;html=1;size=16;fillColor=#FFFFFF;strokeColor=#999999;'
           'align=left;verticalAlign=top;spacingLeft=8;spacingTop=4;fontSize=11;" vertex="1" parent="1">'
           '<mxGeometry x="40" y="640" width="600" height="150" as="geometry"/></mxCell>')

out.append('      </root>')
out.append('    </mxGraphModel>')
out.append('  </diagram>')
out.append('</mxfile>')

with open('computer-track-erd.drawio', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('wrote computer-track-erd.drawio  entities=%d  edges=%d' % (len(ENTITIES), len(EDGES)))
