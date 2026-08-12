"""
Intelligence Engine - PDF Compiler

Renders IntelligenceManager.compile_report()'s dict into an actual,
downloadable PDF - the artifact behind the Intelligence page's
"Compile" button. Nothing here computes anything: every number, finding,
and sentence comes straight from the compiled report dict, which itself
comes straight from the same deterministic Reasoning Engine every other
Intelligence surface reads (spec's Deterministic Intelligence rule) -
this module's only job is to make it "a vivid explanation of how the
company is faring" (formatted, explained, readable) rather than raw
JSON.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_INK = colors.HexColor("#1c1c1e")
_MUTED = colors.HexColor("#5a5a5f")
_ACCENT = colors.HexColor("#c9852b")  # matches the product's signal-amber
_CRITICAL = colors.HexColor("#c23b3b")
_WARNING = colors.HexColor("#b6822a")
_INFO = colors.HexColor("#3c6e8f")
_RULE = colors.HexColor("#d8d5cf")

_SEVERITY_COLOR = {"critical": _CRITICAL, "warning": _WARNING, "info": _INFO}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("OrbitTitle", parent=base["Title"], textColor=_INK, fontSize=26, spaceAfter=4),
        "subtitle": ParagraphStyle("OrbitSubtitle", parent=base["Normal"], textColor=_MUTED, fontSize=11, spaceAfter=18),
        "h2": ParagraphStyle("OrbitH2", parent=base["Heading2"], textColor=_INK, spaceBefore=18, spaceAfter=8),
        "h3": ParagraphStyle("OrbitH3", parent=base["Heading3"], textColor=_INK, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("OrbitBody", parent=base["Normal"], textColor=_INK, fontSize=10, leading=14),
        "muted": ParagraphStyle("OrbitMuted", parent=base["Normal"], textColor=_MUTED, fontSize=9, leading=13),
        "metric": ParagraphStyle("OrbitMetric", parent=base["Normal"], textColor=_INK, fontSize=18, leading=20),
        "metric_label": ParagraphStyle("OrbitMetricLabel", parent=base["Normal"], textColor=_MUTED, fontSize=8, leading=10),
    }


def _fmt_money(value: Any, currency: str = "") -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if n < 0 else ""
    return f"{sign}{currency} {abs(n):,.2f}".strip()


def _fmt_dt(value: str | None) -> str:
    if not value:
        return "\u2014"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def _metric_table(cells: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    row = [
        [Paragraph(value, styles["metric"]), Paragraph(label.upper(), styles["metric_label"])]
        for label, value in cells
    ]
    # transpose into one wide row of stacked (value, label) pairs
    flat = []
    for value, label in row:
        flat.append([value, label])
    table_data = [[cell[0] for cell in flat], [cell[1] for cell in flat]]
    t = Table(table_data, colWidths=[(17 * cm) / max(1, len(cells))] * len(cells))
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
            ]
        )
    )
    return t


def _executive_summary(report: dict) -> str:
    company = report.get("company", {}).get("name") or "Your company"
    health = report.get("health", {})
    summary = report.get("summary", {})
    forecast = report.get("forecast", {})
    connector = report.get("connector", {})

    score = health.get("score", "n/a")
    label = health.get("label", "unknown")
    net_30d = summary.get("net_30d")
    currency = summary.get("currency", "")
    projected_30d = (forecast.get("projected_balance") or {}).get("30d")

    parts = [
        f"{company}'s business health currently scores <b>{score}/100</b> ({label}). "
    ]
    if net_30d is not None:
        trend_word = "positive" if net_30d >= 0 else "negative"
        parts.append(
            f"Net cash flow over the last 30 days was {trend_word} at {_fmt_money(net_30d, currency)}. "
        )
    if projected_30d is not None:
        parts.append(
            f"Holding that trend steady, the projected balance in 30 days is "
            f"{_fmt_money(projected_30d, currency)}. "
        )
    if connector.get("connected"):
        parts.append(
            "This report also incorporates live data read directly from your connected business "
            "systems via your saved Connector URL - not just the ledger. "
        )
    else:
        parts.append(
            "No Connector URL is saved yet, so this report is based on ledger activity only; "
            "connect one from the Developer page to bring your own live business data - whatever "
            "tables you connect - into future reports. "
        )
    return "".join(parts)


def render_intelligence_pdf(report: dict[str, Any]) -> bytes:
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Orbit Intelligence Report",
    )

    story: list[Any] = []
    company = report.get("company", {})
    summary = report.get("summary", {})
    health = report.get("health", {})
    forecast = report.get("forecast", {})
    findings = report.get("findings", [])
    connector = report.get("connector", {})
    knowledge = report.get("knowledge_highlights", [])
    recommendations = report.get("recommendations", [])
    notifications = report.get("recent_notifications", [])
    currency = summary.get("currency", "")

    # --- Cover -----------------------------------------------------------
    story.append(Paragraph(company.get("name") or "Orbit Intelligence Report", styles["title"]))
    story.append(
        Paragraph(
            f"Generated {_fmt_dt(report.get('generated_at'))} "
            f"&middot; Country: {company.get('country') or '\u2014'} "
            f"&middot; Engine status: {'Active' if (report.get('status') or {}).get('active') else 'Inactive'}",
            styles["subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", color=_RULE, thickness=1))
    story.append(Spacer(1, 12))

    story.append(
        _metric_table(
            [
                ("Health score", f"{health.get('score', '\u2014')}/100"),
                ("Cash balance", _fmt_money(summary.get("balance"), currency)),
                ("Net cash flow (30d)", _fmt_money(summary.get("net_30d"), currency)),
                ("Projected balance (30d)", _fmt_money((forecast.get("projected_balance") or {}).get("30d"), currency)),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph("Executive summary", styles["h2"]))
    story.append(Paragraph(_executive_summary(report), styles["body"]))
    if health.get("signals"):
        story.append(
            ListFlowable(
                [ListItem(Paragraph(s, styles["body"])) for s in health["signals"]],
                bulletType="bullet",
                start="circle",
            )
        )

    # --- Financial overview ------------------------------------------------
    story.append(Paragraph("Financial overview", styles["h2"]))
    fin_rows = [
        ["Metric", "Value"],
        ["Cash balance", _fmt_money(summary.get("balance"), currency)],
        ["Inflow (30d)", _fmt_money(summary.get("inflow_30d"), currency)],
        ["Outflow (30d)", _fmt_money(summary.get("outflow_30d"), currency)],
        ["Net cash flow (30d)", _fmt_money(summary.get("net_30d"), currency)],
        ["Transactions (30d)", str(summary.get("transactions_30d", "\u2014"))],
        ["Anomalies flagged (30d)", str(summary.get("anomalies_30d", "\u2014"))],
        ["Projected balance (30d)", _fmt_money((forecast.get("projected_balance") or {}).get("30d"), currency)],
        ["Projected balance (90d)", _fmt_money((forecast.get("projected_balance") or {}).get("90d"), currency)],
        ["Forecast method", forecast.get("method", "\u2014")],
    ]
    story.append(_data_table(fin_rows))

    # --- Findings ------------------------------------------------------
    story.append(Paragraph("Findings", styles["h2"]))
    if not findings:
        story.append(Paragraph("Not enough activity yet for the Engine to produce findings.", styles["muted"]))
    for f in findings:
        color = _SEVERITY_COLOR.get(f.get("severity"), _INK)
        story.append(
            Paragraph(
                f'<font color="{color.hexval()}">&#9679;</font> <b>{f.get("title", "")}</b> '
                f'<font color="{_MUTED.hexval()}">[{f.get("severity", "info").upper()}]</font>',
                styles["body"],
            )
        )
        story.append(Paragraph(f.get("message", ""), styles["muted"]))
        story.append(Spacer(1, 4))

    # --- Connector-sourced business data --------------------------------
    story.append(Paragraph("Business data from your connected systems", styles["h2"]))
    if not connector.get("connected"):
        story.append(
            Paragraph(
                connector.get("reason")
                or "No Connector URL is saved for this company yet. Connect one from the Developer page "
                "(Connector Generator) so future reports include your live business data - whatever "
                "tables you connect, in your own words for them.",
                styles["muted"],
            )
        )
    else:
        if not connector.get("discovered", True):
            story.append(
                Paragraph(
                    "Entity discovery (?entity=_health) wasn't available on this connector, so Orbit fell "
                    "back to a generic guess at entity names below. Redeploy the latest connector file to "
                    "let Orbit discover your actual tables automatically.",
                    styles["muted"],
                )
            )
        for entity in connector.get("entities", []):
            kind_label = entity.get("kind", "generic")
            heading = entity["entity"].title()
            if kind_label and kind_label not in ("generic", "unknown"):
                heading += f"  \u2014  recognized as {kind_label} data"
            story.append(Paragraph(heading, styles["h3"]))
            if not entity.get("reachable"):
                story.append(
                    Paragraph(
                        f"Not available: {entity.get('error') or 'no data returned for this entity.'}",
                        styles["muted"],
                    )
                )
                continue
            s = entity.get("summary", {})
            rows = [["Field", "Value"]] + [[_label(k), str(v)] for k, v in s.items() if k != "low_stock_items"]
            story.append(_data_table(rows))
            if s.get("low_stock_items"):
                story.append(
                    Paragraph(
                        "Low stock: " + ", ".join(f"{it['item']} ({it['quantity']})" for it in s["low_stock_items"]),
                        styles["muted"],
                    )
                )
            story.append(Spacer(1, 6))

        relationships = connector.get("relationships") or []
        if relationships:
            story.append(Paragraph("How your connected tables link together", styles["h3"]))
            rel_rows = [["From", "Field", "Likely links to"]] + [
                [r["from_entity"], r["field"], r["likely_target_entity"]] for r in relationships
            ]
            story.append(_data_table(rel_rows))
            story.append(Spacer(1, 6))

    # --- Knowledge graph highlights --------------------------------------
    story.append(Paragraph("Strongest business relationships", styles["h2"]))
    if not knowledge:
        story.append(Paragraph("Not enough history yet to surface relationships.", styles["muted"]))
    else:
        rows = [["From", "Relationship", "To", "Weight"]]
        for edge in knowledge:
            rows.append(
                [
                    f"{edge['from']['type']}: {edge['from']['key']}",
                    edge["relationship"].replace("_", " "),
                    f"{edge['to']['type']}: {edge['to']['key']}",
                    _fmt_money(edge.get("weight"), currency),
                ]
            )
        story.append(_data_table(rows))

    # --- Recommendations -------------------------------------------------
    story.append(Paragraph("Open recommendations", styles["h2"]))
    if not recommendations:
        story.append(Paragraph("No open recommendations right now.", styles["muted"]))
    else:
        story.append(
            ListFlowable(
                [
                    ListItem(Paragraph(f"<b>{r['title']}</b> \u2014 {r['message']}", styles["body"]))
                    for r in recommendations
                ],
                bulletType="bullet",
            )
        )

    # --- Recent notifications --------------------------------------------
    story.append(Paragraph("Recent notifications", styles["h2"]))
    if not notifications:
        story.append(Paragraph("No notifications yet.", styles["muted"]))
    else:
        rows = [["When", "Severity", "Title"]]
        for n in notifications:
            rows.append([_fmt_dt(n.get("created_at")), n.get("severity", ""), n.get("title", "")])
        story.append(_data_table(rows))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=_RULE, thickness=1))
    story.append(
        Paragraph(
            "Generated by the Orbit Intelligence Engine. Every figure above is computed deterministically "
            "from your ledger and connected systems - nothing here is a model guess, and the same inputs "
            "will always produce the same report.",
            styles["muted"],
        )
    )

    doc.build(story)
    return buf.getvalue()


def _label(key: str) -> str:
    return key.replace("_", " ").title()


def _data_table(rows: list[list[str]]) -> Table:
    t = Table(rows, hAlign="LEFT", colWidths=None)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efece4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), _INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, _RULE),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, _RULE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t
