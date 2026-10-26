"""Generates two native draw.io files: a UML use case diagram and a revised
gate verification flowchart. Native XML, so it opens directly or pastes into
Extras > Edit Diagram."""

# ----------------------------------------------------------------- helpers
HEAD = ('<mxfile host="app.diagrams.net" type="device">\n'
        '  <diagram name="{name}" id="{did}">\n'
        '    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" '
        'math="0" shadow="0">\n      <root>\n'
        '        <mxCell id="0" /><mxCell id="1" parent="0" />\n')
TAIL = '      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n'


def node(i, label, style, x, y, w, h):
    return (f'        <mxCell id="{i}" value="{label}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n')


def edge(i, src, dst, style, label="", pts=None):
    geom = '<mxGeometry relative="1" as="geometry"/>'
    if pts:
        p = ''.join(f'<mxPoint x="{a}" y="{b}" />' for a, b in pts)
        geom = f'<mxGeometry relative="1" as="geometry"><Array as="points">{p}</Array></mxGeometry>'
    return (f'        <mxCell id="{i}" value="{label}" style="{style}" edge="1" parent="1" '
            f'source="{src}" target="{dst}">{geom}</mxCell>\n')


# ============================================================ USE CASE
UC = "ellipse;whiteSpace=wrap;html=1;fillColor=#EAF2FB;strokeColor=#4A6E96;fontSize=11;"
UC_SYS = "ellipse;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;fontSize=11;"
ACTOR = ("shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;"
         "outlineConnect=0;fontSize=11;fontStyle=1;")
BOUND = ("rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#666666;"
         "verticalAlign=top;fontSize=13;fontStyle=1;fontColor=#444444;")
GROUP = "text;html=1;fontSize=11;fontStyle=2;fontColor=#4A6E96;align=left;"
ASSOC = "endArrow=none;html=1;rounded=0;strokeColor=#333333;"
INCL = ("endArrow=open;endFill=0;dashed=1;html=1;rounded=0;strokeColor=#6C8EBF;"
        "fontSize=9;fontColor=#4A6E96;labelBackgroundColor=#FFFFFF;")

EW, EH = 220, 54
CA, CS, CB = 280, 600, 920

usecases = [
    # id,     label,                                        x,   y,   style
    ("u1",  "Register a device",                            CA, 105, UC),
    ("u2",  "Report a device lost or stolen",               CA, 175, UC),
    ("u3",  "Check my devices",                             CA, 245, UC),
    ("u4",  "Verify identity against records on file",      CA, 315, UC),
    ("u5",  "Look up a device",                             CA, 460, UC),
    ("u6",  "Scan a QR sticker",                            CA, 530, UC),
    ("u7",  "View owner photograph and device status",      CA, 600, UC),
    ("u8",  "Record the gate decision",                     CA, 670, UC),
    ("u9",  "Override a hold with a written reason",        CA, 740, UC),
    ("u10", "Queue a decision offline and sync later",      CA, 810, UC),
    ("u11", "Review pending registrations",                 CB, 105, UC),
    ("u12", "Approve or reject a registration",             CB, 175, UC),
    ("u13", "Record approval evidence",                     CB, 245, UC),
    ("u14", "Place or resolve a hold",                      CB, 315, UC),
    ("u15", "Issue a temporary gate pass",                  CB, 385, UC),
    ("u16", "Manage students and import CSV",               CB, 455, UC),
    ("u17", "Review registration attempts",                 CB, 525, UC),
    ("u18", "Configure rules, gates and equipment types",   CB, 670, UC),
    ("u19", "Edit message templates",                       CB, 740, UC),
    ("u20", "Manage staff accounts",                        CB, 810, UC),
    ("u21", "View audit log and dashboard",                 CB, 880, UC),
    ("u24", "Block the device at every gate",               CS, 175, UC_SYS),
    ("u23", "Write to the append-only scan log",            CS, 460, UC_SYS),
    ("u22", "Send a notification",                          CS, 740, UC_SYS),
]

actors = [
    ("stu", "Student\\n(no account)", 120, 190),
    ("grd", "Security Guard",         110, 640),
    ("reg", "Registration Officer",  1290, 280),
    ("adm", "Administrator",         1290, 760),
    ("mail", "Email Service",         640, 1090),
    ("sms", "SMS Gateway",            790, 1090),
]

assoc = [
    ("stu", "u1"), ("stu", "u2"), ("stu", "u3"),
    ("grd", "u5"), ("grd", "u6"), ("grd", "u8"), ("grd", "u10"),
    ("reg", "u11"), ("reg", "u12"), ("reg", "u14"), ("reg", "u15"),
    ("reg", "u16"), ("reg", "u17"), ("reg", "u18"), ("reg", "u19"),
    ("adm", "u20"), ("adm", "u21"),
    ("u22", "mail"), ("u22", "sms"),
]

# include / extend, routed down the gaps between columns so they miss the ellipses
rel = [
    ("u1", "u4", "&#171;include&#187;", [(262, 132), (262, 342)]),
    ("u2", "u4", "&#171;include&#187;", [(525, 202), (525, 342)]),
    ("u3", "u4", "&#171;include&#187;", [(545, 272), (545, 342)]),
    ("u2", "u24", "&#171;include&#187;", None),
    ("u5", "u7", "&#171;include&#187;", [(525, 487), (525, 627)]),
    ("u6", "u5", "&#171;extend&#187;", [(262, 557), (262, 487)]),
    ("u9", "u8", "&#171;extend&#187;", [(262, 767), (262, 697)]),
    ("u10", "u8", "&#171;extend&#187;", [(272, 837), (272, 697)]),
    ("u8", "u23", "&#171;include&#187;", [(545, 697), (545, 487)]),
    ("u8", "u22", "&#171;extend&#187;", [(560, 697), (560, 767)]),
    ("u12", "u13", "&#171;include&#187;", [(905, 202), (905, 272)]),
    ("u12", "u22", "&#171;include&#187;", [(880, 202), (880, 767)]),
]

x = HEAD.format(name="Use case diagram", did="usecase", pw=1400, ph=1250)
x += node("title", "Computer Track - Use Case Diagram",
          "text;html=1;fontSize=20;fontStyle=1;align=left;", 40, 10, 700, 30)
x += node("boundary", "Computer Track", BOUND, 250, 60, 930, 900)
x += node("g1", "Public (no login)", GROUP, 280, 72, 240, 20)
x += node("g2", "Gate console", GROUP, 280, 428, 240, 20)
x += node("g3", "Registration office", GROUP, 920, 72, 260, 20)
x += node("g4", "Configuration and oversight", GROUP, 920, 638, 280, 20)
x += node("g5", "System actions", GROUP, 600, 72, 240, 20)

for i, label, cx, cy, style in usecases:
    x += node(i, label, style, cx, cy, EW, EH)
for i, label, ax, ay in actors:
    x += node(i, label, ACTOR, ax, ay, 30, 60)
for n, (a, b) in enumerate(assoc):
    x += edge(f"a{n}", a, b, ASSOC)
for n, (a, b, lbl, pts) in enumerate(rel):
    x += edge(f"r{n}", a, b, INCL, lbl, pts)

x += node("ucnote",
          "&lt;b&gt;Notes&lt;/b&gt;&lt;br&gt;"
          "1. An administrator inherits every guard and registration officer use case, "
          "so that a support call can be reproduced from the caller's own portal.&lt;br&gt;"
          "2. The public use cases create a PENDING record only. Approval is always in person.&lt;br&gt;"
          "3. Override &lt;i&gt;extends&lt;/i&gt; rather than replaces the gate decision: the system "
          "advises, the guard decides.",
          "shape=note;whiteSpace=wrap;html=1;size=16;fillColor=#FFFFFF;strokeColor=#999999;"
          "align=left;verticalAlign=top;spacingLeft=8;spacingTop=4;fontSize=11;",
          40, 790, 195, 210)
x += TAIL
open("use-case.drawio", "w", encoding="utf-8").write(x)

# ============================================================ GATE FLOW
TERM = "rounded=1;arcSize=40;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;fontSize=12;"
PROC = "rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=12;"
DEC = "rhombus;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;fontSize=11;"
HOLDS = "rounded=0;whiteSpace=wrap;html=1;fillColor=#F8CECC;strokeColor=#B85450;fontSize=12;fontStyle=1;"
CLEARS = "rounded=0;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;fontSize=12;fontStyle=1;"
STORE = ("shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=12;whiteSpace=wrap;html=1;"
         "fillColor=#DAE8FC;strokeColor=#6C8EBF;fontSize=12;")
WARN = "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;"
E = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;jumpStyle=arc;jumpSize=8;fontSize=10;"
     "labelBackgroundColor=#FFFFFF;strokeColor=#4D5A66;")

gn = [
    ("start", "Student arrives at a gate carrying a device", TERM, 330, 40, 260, 50),
    ("ident", "How is the device identified?", DEC, 310, 120, 300, 90),
    ("unreg", "UNREGISTERED&#10;Guard records the attempt", WARN, 680, 130, 210, 70),
    ("found", "Device record retrieved", PROC, 330, 250, 260, 40),
    ("show", "Console shows owner photograph,&#10;brand, colour, serial and status", PROC, 330, 320, 260, 60),
    ("bearer", "Does the bearer match the owner photograph?", DEC, 310, 415, 300, 95),
    ("block", "Any blocking reason?&#10;stolen · lost · pending&#10;active hold · owner suspended", DEC, 295, 545, 330, 125),
    ("hold", "HOLD&#10;Guard reads the configured reason", HOLDS, 680, 565, 210, 80),
    ("prop", "Leaving with university property and no valid pass?", DEC, 295, 705, 330, 105),
    ("clear", "CLEAR&#10;Allow through", CLEARS, 330, 850, 260, 56),
    ("ovr", "Guard overrides?", DEC, 680, 705, 210, 90),
    ("override", "OVERRIDE&#10;Written reason stored", CLEARS, 680, 850, 210, 60),
    ("denied", "DENIED", HOLDS, 680, 945, 210, 44),
    ("net", "Network available?", DEC, 310, 950, 300, 90),
    ("queue", "Queued locally with an idempotency key", WARN, 40, 955, 220, 70),
    ("recheck", "On reconnection the server re-applies every rule and rejects replays", WARN, 40, 1075, 220, 85),
    ("log", "Scan written to the append-only log&#10;device · student · gate · guard&#10;direction · verdict · time", STORE, 330, 1085, 260, 95),
    ("notify", "Owner notified by SMS or email, if the rule is enabled", TERM, 330, 1215, 260, 56),
    ("done", "Student passes, or is held", TERM, 330, 1300, 260, 50),
]

ge = [
    ("start", "ident", "", None),
    ("ident", "found", "QR · serial · asset tag&#10;registration number", None),
    ("ident", "unreg", "no match", None),
    ("found", "show", "", None),
    ("show", "bearer", "", None),
    ("bearer", "hold", "no", [(785, 462)]),
    ("bearer", "block", "yes", None),
    ("block", "hold", "one or more", None),
    ("block", "prop", "none", None),
    ("prop", "hold", "yes", [(650, 757), (650, 605)]),
    ("prop", "clear", "no, or a valid pass", None),
    ("hold", "ovr", "", None),
    ("ovr", "override", "yes, with a written reason", None),
    ("ovr", "denied", "no", [(930, 750), (930, 967)]),
    ("clear", "net", "", None),
    ("override", "net", "", [(640, 880), (640, 1000)]),
    ("denied", "net", "", [(658, 967), (658, 1018)]),
    ("unreg", "net", "", [(950, 165), (950, 1062), (460, 1062)]),
    ("net", "log", "yes", None),
    ("net", "queue", "no", [(150, 995)]),
    ("queue", "recheck", "", None),
    ("recheck", "log", "", [(150, 1132)]),
    ("log", "notify", "", None),
    ("notify", "done", "", None),
]

y = HEAD.format(name="Gate verification", did="gateflow", pw=1000, ph=1400)
y += node("t", "Gate verification decision flow",
          "text;html=1;fontSize=20;fontStyle=1;align=left;", 40, 10, 600, 30)
for i, label, style, a, b, w, h in gn:
    y += node(i, label, style, a, b, w, h)
for n, (a, b, lbl, pts) in enumerate(ge):
    y += edge(f"g{n}", a, b, E, lbl, pts)
y += node("gnote",
          "Every path ends in a stored record, including the ones that found nothing. "
          "The software advises; the guard decides. Any hold can be overridden with a "
          "written reason, because a gate that cannot be overridden cannot let an ambulance through.",
          "shape=note;whiteSpace=wrap;html=1;size=16;fillColor=#FFFFFF;strokeColor=#999999;"
          "align=left;verticalAlign=top;spacingLeft=8;spacingTop=4;fontSize=11;",
          40, 250, 230, 160)
y += TAIL
open("gate-verification-v2.drawio", "w", encoding="utf-8").write(y)

print("wrote use-case.drawio (%d use cases, %d actors) and gate-verification-v2.drawio (%d nodes)"
      % (len(usecases), len(actors), len(gn)))
