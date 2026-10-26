"""Generates the publication-grade UML Activity Diagram with professional typography and spacing:
- Modern Segoe UI typography with bold headers and crisp labels
- 4 wide vertical swimlanes (380px each) so every action/decision fits comfortably inside its lane
- Zero nodes crossing swimlane boundaries and zero overlapping lines
- Accurate offline scan queuing, 3 explicit verdicts (ALLOWED, DENIED, OVERRIDE), and conditional SMS dispatch
"""

import html
import os

HEAD = (
    '<mxfile host="app.diagrams.net" type="device">\n'
    '  <diagram name="UML Activity Diagram" id="activity_diagram">\n'
    '    <mxGraphModel dx="1680" dy="1480" grid="1" gridSize="10" guides="1" tooltips="1" '
    'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1640" pageHeight="1460" '
    'defaultFontFamily="Segoe UI" math="0" shadow="0">\n      <root>\n'
    '        <mxCell id="0" /><mxCell id="1" parent="0" />\n'
)
TAIL = "      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"


def escape(s):
    return html.escape(s)


def build_taste_activity_diagram():
    out = [HEAD]

    # Title & Subtitle
    out.append(
        '        <mxCell id="title" value="Computer Track — UML Activity Diagram (Gate Verification Workflow)" '
        'style="text;html=1;fontFamily=Segoe UI;fontSize=20;fontStyle=1;fontColor=#0F172A;align=left;verticalAlign=middle;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="18" width="850" height="28" as="geometry"/></mxCell>\n'
    )
    out.append(
        '        <mxCell id="subtitle" value="End-to-End Checkpoint Decision Flow · Edge Offline Caching &amp; Sync · Audit &amp; Departure Notifications" '
        'style="text;html=1;fontFamily=Segoe UI;fontSize=12;fontStyle=0;fontColor=#475569;align=left;verticalAlign=middle;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="46" width="850" height="20" as="geometry"/></mxCell>\n'
    )

    # 4 Wide Vertical Swimlanes (380px each -> zero overflow)
    LANE_W = 380
    LANE_H = 1330
    LANES = [
        ("lane1", "Security Guard (Checkpoint Actor)", 40, 80, LANE_W, LANE_H, "#F8FAFC", "#CBD5E1", "#E2E8F0", "#0F172A"),
        ("lane2", "Gate Console (React 19 PWA Client)", 420, 80, LANE_W, LANE_H, "#FFFFFF", "#CBD5E1", "#DBEAFE", "#1E3A8A"),
        ("lane3", "Backend API & Registry (Django REST)", 800, 80, LANE_W, LANE_H, "#F8FAFC", "#CBD5E1", "#DCFCE7", "#14532D"),
        ("lane4", "Audit Log & Sync (Outbox & SMS)", 1180, 80, LANE_W, LANE_H, "#FFFFFF", "#CBD5E1", "#F3E8FF", "#581C87"),
    ]

    for lid, lname, lx, ly, lw, lh, lfill, lstroke, hfill, fcolor in LANES:
        out.append(
            f'        <mxCell id="{lid}" value="{escape(lname)}" style="shape=swimlane;startSize=38;'
            f'horizontal=1;whiteSpace=wrap;html=1;fillColor={hfill};swimlaneFillColor={lfill};strokeColor={lstroke};strokeWidth=1.5;'
            f'fontFamily=Segoe UI;fontStyle=1;fontSize=13;fontColor={fcolor};align=center;collapsible=0;" vertex="1" parent="1">'
            f'<mxGeometry x="{lx}" y="{ly}" width="{lw}" height="{lh}" as="geometry"/></mxCell>\n'
        )

    # Professional Typography & Node Styles
    ACT_STYLE = (
        "rounded=1;arcSize=28;whiteSpace=wrap;html=1;fillColor=#FEF3C7;strokeColor=#D97706;strokeWidth=1.5;"
        "fontFamily=Segoe UI;fontSize=11;fontStyle=1;fontColor=#1E293B;align=center;"
    )
    DEC_STYLE = (
        "rhombus;whiteSpace=wrap;html=1;fillColor=#E0F2FE;strokeColor=#0284C7;strokeWidth=1.5;"
        "fontFamily=Segoe UI;fontSize=11;fontStyle=1;fontColor=#0C4A6E;align=center;"
    )
    ALLOW_STYLE = (
        "rounded=1;arcSize=28;whiteSpace=wrap;html=1;fillColor=#DCFCE7;strokeColor=#15803D;strokeWidth=2;"
        "fontFamily=Segoe UI;fontSize=12;fontStyle=1;fontColor=#14532D;align=center;"
    )
    DENY_STYLE = (
        "rounded=1;arcSize=28;whiteSpace=wrap;html=1;fillColor=#FFEDD5;strokeColor=#C2410C;strokeWidth=2;"
        "fontFamily=Segoe UI;fontSize=12;fontStyle=1;fontColor=#7C2D12;align=center;"
    )
    OVERRIDE_STYLE = (
        "rounded=1;arcSize=28;whiteSpace=wrap;html=1;fillColor=#CCFBF1;strokeColor=#0F766E;strokeWidth=2;"
        "fontFamily=Segoe UI;fontSize=12;fontStyle=1;fontColor=#134E4A;align=center;"
    )
    START_STYLE = "ellipse;fillColor=#0F172A;strokeColor=none;"
    END_STYLE = "shape=doubleEllipse;fillColor=#0F172A;strokeColor=#0F172A;strokeWidth=2;"

    # ------------------ NODES ------------------
    # Lane 1 (x=40..420, center=230)
    out.append(f'        <mxCell id="start" value="" style="{START_STYLE}" vertex="1" parent="1"><mxGeometry x="216" y="130" width="28" height="28" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_scan" value="Scan QR code or type&#xa;serial / reg number" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="120" y="185" width="220" height="54" as="geometry"/></mxCell>\n')

    # Lane 2 Lookup (x=420..800, center=610)
    out.append(f'        <mxCell id="d_net_lookup" value="Network&#xa;online?" style="{DEC_STYLE}" vertex="1" parent="1"><mxGeometry x="540" y="175" width="140" height="74" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_cache" value="Read sessionStorage cache&#xa;or manual permit check" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="435" y="290" width="168" height="52" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_call_api" value="Call verification API&#xa;(GET /checkpoint/lookup/)" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="617" y="290" width="168" height="52" as="geometry"/></mxCell>\n')

    # Lane 3 Backend (x=800..1180, center=990)
    out.append(f'        <mxCell id="a_lookup" value="Look up device &amp; student&#xa;in inverted index &amp; registry" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="885" y="290" width="210" height="52" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="d_hold" value="Unregistered, stolen, lost,&#xa;pending or flagged hold?" style="{DEC_STYLE}" vertex="1" parent="1"><mxGeometry x="885" y="375" width="210" height="86" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_ret_clear" value="Return CLEAR +&#xa;signed owner photo" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="815" y="495" width="165" height="52" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_ret_hold" value="Return HOLD / UNREG&#xa;+ reason + owner photo" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="1000" y="495" width="165" height="52" as="geometry"/></mxCell>\n')

    # Lane 2 Display & Lane 1 Visual Check
    out.append(f'        <mxCell id="a_display" value="Display owner photo +&#xa;CLEAR / HOLD / UNREG banner" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="500" y="575" width="220" height="54" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_verify" value="Visually check bearer&#xa;against owner photo" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="120" y="575" width="220" height="54" as="geometry"/></mxCell>\n')

    # Lane 1 Decisions & Lane 2 Override Prompt
    out.append(f'        <mxCell id="d_match" value="Clean status and&#xa;bearer matches photo?" style="{DEC_STYLE}" vertex="1" parent="1"><mxGeometry x="130" y="660" width="200" height="78" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="d_override" value="Guard to&#xa;override?" style="{DEC_STYLE}" vertex="1" parent="1"><mxGeometry x="245" y="755" width="145" height="76" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_reason" value="Prompt mandatory written&#xa;override justification" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="505" y="767" width="210" height="52" as="geometry"/></mxCell>\n')

    # 3 Parallel Verdict Nodes (y = 860) — cleanly inside their lanes
    out.append(f'        <mxCell id="v_allowed" value="Verdict: ALLOWED" style="{ALLOW_STYLE}" vertex="1" parent="1"><mxGeometry x="65" y="860" width="150" height="46" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="v_denied" value="Verdict: DENIED" style="{DENY_STYLE}" vertex="1" parent="1"><mxGeometry x="242" y="860" width="150" height="46" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="v_override" value="Verdict: OVERRIDE" style="{OVERRIDE_STYLE}" vertex="1" parent="1"><mxGeometry x="535" y="860" width="150" height="46" as="geometry"/></mxCell>\n')

    # Merge Diamond & Scan Sync in Lane 2
    out.append(f'        <mxCell id="d_verdict_merge" value="" style="rhombus;fillColor=#E0F2FE;strokeColor=#0284C7;strokeWidth=1.5;" vertex="1" parent="1"><mxGeometry x="595" y="930" width="30" height="30" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="d_sync_net" value="Network&#xa;online?" style="{DEC_STYLE}" vertex="1" parent="1"><mxGeometry x="540" y="985" width="140" height="68" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_queue" value="Queue scan locally&#xa;(UUID key in IndexedDB)" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="435" y="1085" width="168" height="52" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_submit_scan" value="Submit scan via API&#xa;(POST /checkpoint/scans/)" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="617" y="1085" width="168" height="52" as="geometry"/></mxCell>\n')

    # Lane 4 Audit Log & Conditional SMS (x=1180..1560, center=1370)
    out.append(f'        <mxCell id="a_log" value="Commit to append-only&#xa;ScanEvent audit log" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="1265" y="1085" width="210" height="52" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="d_sms" value="Exit direction &amp;&#xa;ALLOWED / OVERRIDE?" style="{DEC_STYLE}" vertex="1" parent="1"><mxGeometry x="1270" y="1165" width="200" height="78" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="a_sms" value="Send departure SMS alert&#xa;to owner phone (outbox)" style="{ACT_STYLE}" vertex="1" parent="1"><mxGeometry x="1265" y="1270" width="210" height="52" as="geometry"/></mxCell>\n')
    out.append(f'        <mxCell id="end" value="" style="{END_STYLE}" vertex="1" parent="1"><mxGeometry x="1356" y="1352" width="28" height="28" as="geometry"/></mxCell>\n')

    # ------------------ EDGES ------------------
    def edge(eid, src, dst, label="", exit_p=(0.5, 1), entry_p=(0.5, 0), dashed=False, pts=None):
        dash_str = "dashed=1;dashPattern=6 4;" if dashed else ""
        pts_str = ""
        if pts:
            inner = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in pts)
            pts_str = f'<Array as="points">{inner}</Array>'
        geom = f'<mxGeometry relative="1" as="geometry">{pts_str}</mxGeometry>'
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=8;jumpStyle=arc;jumpSize=6;html=1;"
            f"strokeColor=#334155;strokeWidth=1.5;fontFamily=Segoe UI;fontSize=10;fontStyle=1;fontColor=#0F172A;"
            f"exitX={exit_p[0]};exitY={exit_p[1]};entryX={entry_p[0]};entryY={entry_p[1]};"
            f"labelBackgroundColor=#FFFFFF;{dash_str}"
        )
        return f'        <mxCell id="{eid}" value="{escape(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">{geom}</mxCell>\n'

    out.append(edge("e0", "start", "a_scan"))
    out.append(edge("e1", "a_scan", "d_net_lookup", exit_p=(1, 0.5), entry_p=(0, 0.5)))
    out.append(edge("e2", "d_net_lookup", "a_cache", "[Offline: Cache]", exit_p=(0.25, 1), entry_p=(0.5, 0)))
    out.append(edge("e3", "d_net_lookup", "a_call_api", "[Online]", exit_p=(0.75, 1), entry_p=(0.5, 0)))
    out.append(edge("e4", "a_call_api", "a_lookup", exit_p=(1, 0.5), entry_p=(0, 0.5)))
    out.append(edge("e5", "a_cache", "a_display", exit_p=(0.5, 1), entry_p=(0.25, 0), pts=[(519, 430), (555, 430)]))
    out.append(edge("e6", "a_lookup", "d_hold", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    # d_hold branches
    out.append(edge("e7", "d_hold", "a_ret_clear", "[No: Clear]", exit_p=(0.25, 1), entry_p=(0.5, 0)))
    out.append(edge("e8", "d_hold", "a_ret_hold", "[Yes: Hold / Unreg]", exit_p=(0.75, 1), entry_p=(0.5, 0)))

    # Returns converge to Display
    out.append(edge("e9", "a_ret_clear", "a_display", exit_p=(0.5, 1), entry_p=(1, 0.3), pts=[(897, 591)]))
    out.append(edge("e10", "a_ret_hold", "a_display", exit_p=(0.5, 1), entry_p=(1, 0.7), pts=[(1082, 613)]))

    # Display to Guard verify
    out.append(edge("e11", "a_display", "a_verify", exit_p=(0, 0.5), entry_p=(1, 0.5)))
    out.append(edge("e12", "a_verify", "d_match", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    # d_match branches
    out.append(edge("e13", "d_match", "v_allowed", "[Yes: Match & Clear]", exit_p=(0.2, 1), entry_p=(0.5, 0), pts=[(170, 745), (140, 745)]))
    out.append(edge("e14", "d_match", "d_override", "[No: Hold / Mismatch]", exit_p=(0.8, 1), entry_p=(0.5, 0), pts=[(290, 742), (317, 742)]))

    # d_override branches
    out.append(edge("e15", "d_override", "a_reason", "[Yes: Override]", exit_p=(1, 0.5), entry_p=(0, 0.5)))
    out.append(edge("e16", "d_override", "v_denied", "[No: Enforce Deny]", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    # Override reason -> Verdict: OVERRIDE
    out.append(edge("e17", "a_reason", "v_override", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    # 3 Verdicts -> Merge Diamond
    out.append(edge("e18", "v_allowed", "d_verdict_merge", exit_p=(0.5, 1), entry_p=(0, 0.5), pts=[(140, 945)]))
    out.append(edge("e19", "v_denied", "d_verdict_merge", exit_p=(0.5, 1), entry_p=(0, 0.5), pts=[(317, 945)]))
    out.append(edge("e20", "v_override", "d_verdict_merge", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    # Merge -> Network Check for Scan Submission
    out.append(edge("e21", "d_verdict_merge", "d_sync_net", exit_p=(0.5, 1), entry_p=(0.5, 0)))
    out.append(edge("e22", "d_sync_net", "a_queue", "[Offline]", exit_p=(0.25, 1), entry_p=(0.5, 0)))
    out.append(edge("e23", "d_sync_net", "a_submit_scan", "[Online]", exit_p=(0.75, 1), entry_p=(0.5, 0)))

    # Offline queue flush on reconnect (dashed)
    out.append(edge("e24", "a_queue", "a_submit_scan", "Sync on reconnect", exit_p=(1, 0.5), entry_p=(0, 0.5), dashed=True))

    # Submit Scan -> Commit to Log in Audit Lane
    out.append(edge("e25", "a_submit_scan", "a_log", exit_p=(1, 0.5), entry_p=(0, 0.5)))

    # a_log -> d_sms
    out.append(edge("e26", "a_log", "d_sms", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    # d_sms branches
    out.append(edge("e27", "d_sms", "a_sms", "[Yes: Permitted Exit]", exit_p=(0.5, 1), entry_p=(0.5, 0)))
    out.append(edge("e28", "d_sms", "end", "[No: Denied or Entry]", exit_p=(1, 0.5), entry_p=(1, 0.5), pts=[(1525, 1204), (1525, 1366)]))

    # a_sms -> end
    out.append(edge("e29", "a_sms", "end", exit_p=(0.5, 1), entry_p=(0.5, 0)))

    out.append(TAIL)
    return "".join(out)


def main():
    target_dir = os.path.dirname(os.path.abspath(__file__))
    act_path = os.path.join(target_dir, "activity-diagram.drawio")
    with open(act_path, "w", encoding="utf-8") as f:
        f.write(build_taste_activity_diagram())
    print(f"Updated successfully with fixed workflow: {act_path}")


if __name__ == "__main__":
    main()
