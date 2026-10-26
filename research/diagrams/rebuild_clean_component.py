"""Rebuilds component-diagram.drawio with a 2-column Application Tier hub-and-spoke layout,
explicit UML 2.5 Ports (square boundary ports), stereotyped connectors, 130px vertical/horizontal
corridors so every relationship line and arrowhead is 100% visible, and a UML Notation Legend.
"""

import html
import os

HEAD = (
    '<mxfile host="app.diagrams.net" type="device">\n'
    '  <diagram name="UML Component Diagram" id="component_diagram">\n'
    '    <mxGraphModel dx="1950" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" '
    'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1930" pageHeight="940" '
    'defaultFontFamily="Segoe UI" math="0" shadow="0">\n      <root>\n'
    '        <mxCell id="0" /><mxCell id="1" parent="0" />\n'
)
TAIL = "      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"


def escape(s):
    return html.escape(s)


def build_clean_component_diagram():
    out = [HEAD]

    # Title & Subtitle
    out.append(
        '        <mxCell id="title" value="Computer Track — UML 2.5 Component Diagram" '
        'style="text;html=1;fontFamily=Segoe UI;fontSize=20;fontStyle=1;fontColor=#0F172A;align=left;verticalAlign=middle;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="18" width="800" height="28" as="geometry"/></mxCell>\n'
    )
    out.append(
        '        <mxCell id="subtitle" value="Four-Tier Subsystem Architecture · Explicit Component Ports &amp; Stereotyped Relationships · Offline-First Gate Verification" '
        'style="text;html=1;fontFamily=Segoe UI;fontSize=12;fontStyle=0;fontColor=#475569;align=left;verticalAlign=middle;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="46" width="950" height="20" as="geometry"/></mxCell>\n'
    )

    def subsystem(sid, label, x, y, w, h, fill="#F8FAFC", stroke="#3B82F6", header_fill="#DBEAFE", font_color="#1E3A8A"):
        val = f"&amp;laquo;subsystem&amp;raquo;&lt;br/&gt;&lt;b style=&quot;font-size:12px;&quot;&gt;{escape(label)}&lt;/b&gt;"
        style = (
            f"shape=swimlane;startSize=44;horizontal=1;rounded=1;arcSize=4;whiteSpace=wrap;html=1;"
            f"fillColor={header_fill};swimlaneFillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
            f"fontFamily=Segoe UI;fontSize=11;fontStyle=0;fontColor={font_color};align=center;collapsible=0;"
        )
        return (
            f'        <mxCell id="{sid}" value="{val}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    def comp(cid, name, subtitle, x, y, w, h, fill="#FFFFFF", stroke="#2563EB", badge_color="#1D4ED8"):
        val = (
            f"&lt;font style=&quot;font-size:10px;color:{badge_color};&quot;&gt;&amp;laquo;component&amp;raquo;&lt;/font&gt;&lt;br/&gt;"
            f"&lt;b style=&quot;font-size:12px;color:#0F172A;&quot;&gt;{escape(name)}&lt;/b&gt;"
        )
        if subtitle:
            val += f"&lt;br/&gt;&lt;font style=&quot;font-size:10px;color:#475569;&quot;&gt;{escape(subtitle)}&lt;/font&gt;"
        style = (
            f"shape=module;jettyWidth=12;jettyHeight=6;align=center;verticalAlign=middle;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontFamily=Segoe UI;fontSize=11;fontStyle=0;"
        )
        return (
            f'        <mxCell id="{cid}" value="{val}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    def port_box(pid, x, y, stroke="#2563EB", fill="#FFFFFF"):
        style = f"rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
        return (
            f'        <mxCell id="{pid}" value="" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="10" height="10" as="geometry"/></mxCell>\n'
        )

    def database_node(did, name, subtitle, x, y, w, h, fill="#FFFFFF", stroke="#E11D48"):
        val = (
            f"&lt;font style=&quot;font-size:10px;color:#BE123C;&quot;&gt;&amp;laquo;database&amp;raquo;&lt;/font&gt;&lt;br/&gt;"
            f"&lt;b style=&quot;font-size:12px;color:#0F172A;&quot;&gt;{escape(name)}&lt;/b&gt;&lt;br/&gt;"
            f"&lt;font style=&quot;font-size:10px;color:#475569;&quot;&gt;{escape(subtitle)}&lt;/font&gt;"
        )
        style = (
            f"shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontFamily=Segoe UI;fontSize=11;align=center;"
        )
        return (
            f'        <mxCell id="{did}" value="{val}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>\n'
        )

    # =========================================================================
    # TIER 1: PRESENTATION TIER (x=40..330)
    # =========================================================================
    out.append(subsystem("sub_pres", "Presentation Tier (React 19 PWA)", 40, 85, 290, 665, "#F8FAFC", "#3B82F6", "#DBEAFE", "#1E3A8A"))
    out.append(comp("c_guard_ui", "Security Gate Console", "Lookup · Photo Match · Override", 65, 145, 240, 66, "#EFF6FF", "#2563EB", "#1D4ED8"))
    out.append(comp("c_offline", "Offline Queue & Worker", "IndexedDB Scan Queue · Session Cache", 65, 265, 240, 66, "#F5F3FF", "#7C3AED", "#6D28D9"))
    out.append(comp("c_reg_ui", "Registration Office Portal", "Approvals · Hold Flags · Permits", 65, 385, 240, 66, "#EFF6FF", "#2563EB", "#1D4ED8"))
    out.append(comp("c_admin_ui", "Administration Dashboard", "Staff · Policy Rules · Read-Audit", 65, 495, 240, 66, "#EFF6FF", "#2563EB", "#1D4ED8"))
    out.append(comp("c_public_ui", "Public Self-Service Form", "Unauthenticated Register & Loss Report", 65, 605, 240, 66, "#EFF6FF", "#2563EB", "#1D4ED8"))

    # UML Ports on Tier 1 right boundary
    out.append(port_box("p_guard", 300, 173, "#2563EB", "#DBEAFE"))
    out.append(port_box("p_off", 300, 293, "#7C3AED", "#EDE9FE"))
    out.append(port_box("p_reg", 300, 413, "#2563EB", "#DBEAFE"))
    out.append(port_box("p_adm", 300, 523, "#2563EB", "#DBEAFE"))
    out.append(port_box("p_pub", 300, 633, "#2563EB", "#DBEAFE"))

    # =========================================================================
    # TIER 2: APPLICATION TIER (x=470..1070, 2-Column Layout with 100px gap!)
    # =========================================================================
    out.append(subsystem("sub_app", "Application Tier (Django 5 REST API)", 470, 85, 600, 665, "#F0FDF4", "#16A34A", "#DCFCE7", "#14532D"))

    # Left Column (Gateway, Policy, Audit) — x=500, w=225
    out.append(comp("c_gateway", "API Gateway & Auth", "JWT Bearer · TOTP 2FA · Rate Throttles", 500, 155, 225, 70, "#FFFFFF", "#16A34A", "#15803D"))
    out.append(comp("c_policy_svc", "Policy & Rule Store", "Runtime JSON Rules & Wording Store", 500, 365, 225, 70, "#FEFCE8", "#CA8A04", "#A16207"))
    out.append(comp("c_audit_svc", "Read-Audit & Security", "Register Read Log · Anomaly Alerting", 500, 575, 225, 70, "#FFF7ED", "#EA580C", "#C2410C"))

    # Right Column (Checkpoint, Device, Student) — x=820, w=225
    out.append(comp("c_checkpoint", "Checkpoint & Search Service", "Inverted Index · Gate Decision Engine", 820, 155, 225, 70, "#FFFFFF", "#16A34A", "#15803D"))
    out.append(comp("c_device_svc", "Device Management Service", "Devices · Hold Flags · Gate Permits", 820, 365, 225, 70, "#FFFFFF", "#16A34A", "#15803D"))
    out.append(comp("c_student_svc", "Student Registry Service", "Student Records · CSV Import · Identity", 820, 575, 225, 70, "#FFFFFF", "#16A34A", "#15803D"))

    # UML Ports inside Tier 2
    out.append(port_box("p_gw_in", 495, 185, "#16A34A", "#DCFCE7"))
    out.append(port_box("p_gw_out", 720, 185, "#16A34A", "#DCFCE7"))
    out.append(port_box("p_cp_in", 815, 185, "#16A34A", "#DCFCE7"))
    out.append(port_box("p_cp_out", 1040, 185, "#16A34A", "#DCFCE7"))
    out.append(port_box("p_dev_out", 1040, 395, "#16A34A", "#DCFCE7"))
    out.append(port_box("p_stu_out", 1040, 605, "#16A34A", "#DCFCE7"))

    # =========================================================================
    # TIER 3: PERSISTENCE & BACKGROUND TIER (x=1220..1500)
    # =========================================================================
    out.append(subsystem("sub_data", "Persistence & Background Tasks", 1220, 85, 280, 665, "#FFF1F2", "#E11D48", "#FFE4E6", "#881337"))
    out.append(database_node("c_db", "PostgreSQL Database", "Domain Models · Append-Only Scans", 1245, 150, 230, 82, "#FFFFFF", "#E11D48"))
    out.append(database_node("c_redis", "Redis Cache & Broker", "Rate Limits · Rule Cache · Celery Queue", 1245, 305, 230, 82, "#FFFFFF", "#E11D48"))
    out.append(comp("c_celery", "Celery Worker & Beat", "Async Outbox Drain · Audit Sweepers", 1245, 455, 230, 68, "#FFFFFF", "#E11D48", "#BE123C"))
    out.append(comp("c_media", "Secure Media Storage", "Expiring Signed HMAC Photo URLs", 1245, 585, 230, 68, "#FFFFFF", "#E11D48", "#BE123C"))

    # =========================================================================
    # TIER 4: EXTERNAL CLOUD GATEWAYS (x=1630..1890)
    # =========================================================================
    out.append(subsystem("sub_ext", "Notification & Cloud Gateways", 1630, 85, 260, 665, "#FAF5FF", "#9333EA", "#F3E8FF", "#581C87"))
    out.append(comp("c_outbox", "Transactional Outbox", "Atomic Outbox Table · Templates", 1650, 160, 220, 68, "#FFFFFF", "#9333EA", "#7E22CE"))
    out.append(comp("c_sms", "Africa's Talking SMS API", "E.164 SMS · Exit & Security Alerts", 1650, 365, 220, 68, "#FFFFFF", "#9333EA", "#7E22CE"))
    out.append(comp("c_mail", "Resend Email API", "Transactional Email · Approvals", 1650, 575, 220, 68, "#FFFFFF", "#9333EA", "#7E22CE"))

    # =========================================================================
    # BOTTOM SUMMARY & UML 2.5 NOTATION LEGEND (y=775..900)
    # =========================================================================
    out.append(
        '        <mxCell id="arch_note" value='
        '"&lt;b style=&quot;font-size:12px;color:#0F172A;&quot;&gt;Component Relationships, Inputs &amp; Outputs Summary&lt;/b&gt;&lt;br/&gt;'
        '&lt;font style=&quot;color:#334155;&quot;&gt;'
        '• &lt;b&gt;Presentation → API Gateway (&amp;laquo;HTTPS/JWT&amp;raquo;):&lt;/b&gt; Portals send authenticated JSON requests; Public Form sends unauthenticated intake requests.&lt;br/&gt;'
        '• &lt;b&gt;Gate Console ↔ Offline Queue (&amp;laquo;cache/enqueue&amp;raquo;):&lt;/b&gt; Buffers scan verdicts locally in IndexedDB with UUID idempotency keys and bulk-syncs on reconnect.&lt;br/&gt;'
        '• &lt;b&gt;API Gateway → Domain Services (&amp;laquo;delegate&amp;raquo;):&lt;/b&gt; Dispatches validated requests to Checkpoint, Device Management, and Student Registry services.&lt;br/&gt;'
        '• &lt;b&gt;Domain Services → Persistence &amp; Outbox (&amp;laquo;SQL/ORM&amp;raquo;, &amp;laquo;RESP&amp;raquo;, &amp;laquo;async&amp;raquo;):&lt;/b&gt; Reads/writes PostgreSQL &amp; Redis; commits Outbox rows drained by Celery to SMS/Email APIs.'
        '&lt;/font&gt;" '
        'style="rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#F8FAFC;strokeColor=#CBD5E1;strokeWidth=1.5;align=left;verticalAlign=middle;spacingLeft=16;spacingRight=16;fontFamily=Segoe UI;fontSize=11;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="775" width="1150" height="115" as="geometry"/></mxCell>\n'
    )

    out.append(
        '        <mxCell id="uml_legend" value='
        '"&lt;b style=&quot;font-size:12px;color:#0F172A;&quot;&gt;UML 2.5 Component Notation Legend&lt;/b&gt;&lt;br/&gt;'
        '&lt;font style=&quot;color:#334155;&quot;&gt;'
        '• &lt;b&gt;&amp;laquo;component&amp;raquo; + Port (□):&lt;/b&gt; Encapsulated software module with explicit boundary interaction port.&lt;br/&gt;'
        '• &lt;b&gt;Solid Arrow (────▶):&lt;/b&gt; Synchronous invocation / request delegation (&amp;laquo;HTTPS/JWT&amp;raquo;, &amp;laquo;delegate&amp;raquo;, &amp;laquo;SQL&amp;raquo;).&lt;br/&gt;'
        '• &lt;b&gt;Dashed Open Arrow (- - -▷):&lt;/b&gt; UML Dependency / Asynchronous event / Offline replay (&amp;laquo;use&amp;raquo;, &amp;laquo;async&amp;raquo;).&lt;br/&gt;'
        '• &lt;b&gt;&amp;laquo;subsystem&amp;raquo; / &amp;laquo;database&amp;raquo;:&lt;/b&gt; Architectural tier boundary container and persistent storage cylinder.'
        '&lt;/font&gt;" '
        'style="rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#94A3B8;strokeWidth=1.5;align=left;verticalAlign=middle;spacingLeft=16;spacingRight=16;fontFamily=Segoe UI;fontSize=11;" vertex="1" parent="1">'
        '<mxGeometry x="1220" y="775" width="670" height="115" as="geometry"/></mxCell>\n'
    )

    # =========================================================================
    # EDGES — HIGH VISIBILITY, LONG UNOBSTRUCTED SHAFTS, CLEAR UML ARROWS
    # =========================================================================
    def edge(eid, src, dst, label="", exit_side=(1, 0.5), entry_side=(0, 0.5), dashed=False, pts=None, color="#1E293B"):
        dash_str = "dashed=1;dashPattern=6 4;endArrow=open;endFill=0;endSize=10;" if dashed else "endArrow=block;endFill=1;endSize=8;"
        pts_str = ""
        if pts:
            inner = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in pts)
            pts_str = f'<Array as="points">{inner}</Array>'

        geom = f'<mxGeometry relative="1" as="geometry">{pts_str}</mxGeometry>'
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=8;jumpStyle=arc;jumpSize=6;html=1;"
            f"strokeColor={color};strokeWidth=1.8;fontFamily=Segoe UI;fontSize=10;fontStyle=1;fontColor={color};"
            f"exitX={exit_side[0]};exitY={exit_side[1]};entryX={entry_side[0]};entryY={entry_side[1]};"
            f"labelBackgroundColor=#FFFFFF;{dash_str}"
        )
        return f'        <mxCell id="{eid}" value="{escape(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">{geom}</mxCell>\n'

    # 1. Presentation Tier internal: Gate Console -> Offline Queue
    out.append(edge("e_guard_off", "c_guard_ui", "c_offline", "«use» Cache & Queue", exit_side=(0.5, 1), entry_side=(0.5, 0), dashed=True, color="#6D28D9"))

    # 2. Presentation Tier -> Application Tier (Corridor x=330..470)
    out.append(edge("e1", "c_guard_ui", "c_gateway", "«HTTPS/JWT»", exit_side=(1, 0.5), entry_side=(0, 0.25), pts=[(390, 178), (390, 172)], color="#1D4ED8"))
    out.append(edge("e_offline_sync", "c_offline", "c_checkpoint", "«sync» POST /scans/bulk/", exit_side=(1, 0.5), entry_side=(0.5, 0), dashed=True, pts=[(365, 298), (365, 130), (932, 130)], color="#6D28D9"))
    out.append(edge("e2", "c_reg_ui", "c_gateway", "«HTTPS/JWT»", exit_side=(1, 0.5), entry_side=(0, 0.5), pts=[(390, 418), (390, 190)], color="#1D4ED8"))
    out.append(edge("e3", "c_admin_ui", "c_gateway", "«HTTPS/2FA»", exit_side=(1, 0.5), entry_side=(0, 0.75), pts=[(415, 528), (415, 207)], color="#1D4ED8"))
    out.append(edge("e4", "c_public_ui", "c_gateway", "«HTTPS Public»", exit_side=(1, 0.5), entry_side=(0, 0.9), pts=[(440, 638), (440, 218)], color="#1D4ED8"))

    # 3. Inside Application Tier (Hub-and-Spoke across 95px horizontal & 140px vertical gaps!)
    out.append(edge("e_gw_cp", "c_gateway", "c_checkpoint", "«delegate» /checkpoint/*", exit_side=(1, 0.5), entry_side=(0, 0.5), color="#15803D"))
    out.append(edge("e_gw_dev", "c_gateway", "c_device_svc", "«delegate» /devices/*", exit_side=(0.5, 1), entry_side=(0, 0.3), pts=[(612, 285), (765, 285), (765, 386)], color="#15803D"))
    out.append(edge("e_gw_stu", "c_gateway", "c_student_svc", "«delegate» /students/*", exit_side=(0.3, 1), entry_side=(0, 0.3), pts=[(567, 315), (745, 315), (745, 596)], color="#15803D"))

    # Checkpoint -> Device Service & Policy Store & Audit
    out.append(edge("e_cp_dev", "c_checkpoint", "c_device_svc", "«use» blocking_reasons()", exit_side=(0.5, 1), entry_side=(0.5, 0), dashed=True, color="#15803D"))
    out.append(edge("e_dev_stu", "c_device_svc", "c_student_svc", "«use» is_clear_to_pass()", exit_side=(0.5, 1), entry_side=(0.5, 0), dashed=True, color="#15803D"))
    out.append(edge("e_pol_dev", "c_policy_svc", "c_device_svc", "«use» Gate Policy Rules", exit_side=(1, 0.5), entry_side=(0, 0.7), dashed=True, pts=[(775, 400), (775, 414)], color="#A16207"))
    out.append(edge("e_cp_aud", "c_checkpoint", "c_audit_svc", "«log»GATE_LOOKUP", exit_side=(0.2, 1), entry_side=(0.5, 0), dashed=True, pts=[(865, 260), (612, 260), (612, 575)], color="#C2410C"))
    out.append(edge("e_stu_aud", "c_student_svc", "c_audit_svc", "«log» Read Audit", exit_side=(0, 0.65), entry_side=(1, 0.65), dashed=True, color="#C2410C"))

    # 4. Application Tier -> Persistence Tier (Corridor x=1045..1245 — 200px wide!)
    out.append(edge("e_cp_db", "c_checkpoint", "c_db", "«SQL» Append ScanEvent", exit_side=(1, 0.5), entry_side=(0, 0.5), color="#BE123C"))
    out.append(edge("e_dev_db", "c_device_svc", "c_db", "«SQL» Devices & Flags", exit_side=(1, 0.3), entry_side=(0, 0.8), pts=[(1130, 386), (1130, 215)], color="#BE123C"))
    out.append(edge("e_stu_db", "c_student_svc", "c_db", "«SQL» Student Roll", exit_side=(1, 0.3), entry_side=(0, 0.95), pts=[(1155, 596), (1155, 228)], color="#BE123C"))
    out.append(edge("e_pol_redis", "c_policy_svc", "c_redis", "«RESP» Rule Cache", exit_side=(0.5, 1), entry_side=(0, 0.5), dashed=True, pts=[(612, 480), (1180, 480), (1180, 346)], color="#BE123C"))
    out.append(edge("e_dev_media", "c_device_svc", "c_media", "«HMAC» Sign Photo URL", exit_side=(1, 0.7), entry_side=(0, 0.5), dashed=True, pts=[(1105, 414), (1105, 619)], color="#BE123C"))

    # 5. Persistence & Background -> Notification Gateways (Corridor x=1475..1650)
    out.append(edge("e_db_outbox", "c_db", "c_outbox", "«SQL» Atomic Outbox Row", exit_side=(1, 0.5), entry_side=(0, 0.5), color="#7E22CE"))
    out.append(edge("e_redis_cel", "c_redis", "c_celery", "«Broker» Task Queue", exit_side=(0.5, 1), entry_side=(0.5, 0), dashed=True, color="#BE123C"))
    out.append(edge("e_cel_outbox", "c_celery", "c_outbox", "«async» Drain Pending", exit_side=(1, 0.5), entry_side=(0, 0.8), dashed=True, pts=[(1560, 489), (1560, 214)], color="#7E22CE"))
    out.append(edge("e_outbox_sms", "c_outbox", "c_sms", "«HTTPS» POST /sms (E.164)", exit_side=(0.5, 1), entry_side=(0.5, 0), color="#7E22CE"))
    out.append(edge("e_outbox_mail", "c_outbox", "c_mail", "«HTTPS» POST /emails", exit_side=(1, 0.5), entry_side=(1, 0.5), pts=[(1880, 194), (1880, 609)], color="#7E22CE"))

    out.append(TAIL)
    return "".join(out)


def main():
    target_dir = os.path.dirname(os.path.abspath(__file__))
    comp_path = os.path.join(target_dir, "component-diagram.drawio")
    with open(comp_path, "w", encoding="utf-8") as f:
        f.write(build_clean_component_diagram())
    print(f"Updated successfully: {comp_path}")


if __name__ == "__main__":
    main()
