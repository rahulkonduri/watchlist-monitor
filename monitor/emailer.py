import html as _html
import os
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List


_REQUIRED_VARS = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_TO"]


def _row_bg(has_alerts: bool) -> str:
    return "background-color:#fff3cd;" if has_alerts else ""


def build_html(
    results: List[Dict[str, Any]],
    ai_notes: Dict[str, str],
    run_date: date,
) -> str:
    total_alerts = sum(len(r["alerts"]) for r in results if not r.get("error"))
    tickers_with_alerts = sum(1 for r in results if r.get("alerts"))

    rows = []
    for r in results:
        ticker = _html.escape(r["ticker"])

        if r.get("error"):
            rows.append(
                f'<tr><td><strong>{ticker}</strong></td>'
                f'<td colspan="5" style="color:#dc3545;">Error: {_html.escape(r["error"])}</td></tr>'
            )
            continue

        price_str = f"${r['price']:.2f}" if r["price"] is not None else "—"

        if r["change_pct"] is not None:
            change_str = f"{r['change_pct']:+.2f}%"
            change_style = "color:#198754;" if r["change_pct"] >= 0 else "color:#dc3545;"
        else:
            change_str, change_style = "—", ""

        rsi_str = f"{r['rsi']:.1f}" if r["rsi"] is not None else "—"

        cross = r.get("ma_cross")
        cross_str = cross if cross else "—"
        if cross == "golden":
            cross_style = "color:#198754;font-weight:bold;"
        elif cross == "death":
            cross_style = "color:#dc3545;font-weight:bold;"
        else:
            cross_style = "color:#6c757d;"

        if r["alerts"]:
            items = "".join(f"<li>{_html.escape(a)}</li>" for a in r["alerts"])
            alert_html = f'<ul style="margin:0;padding-left:1.2em;">{items}</ul>'
        else:
            alert_html = '<span style="color:#6c757d;">—</span>'

        rows.append(
            f'<tr style="{_row_bg(bool(r["alerts"]))}">'
            f"<td><strong>{ticker}</strong></td>"
            f"<td>{price_str}</td>"
            f'<td style="{change_style}">{change_str}</td>'
            f"<td>{rsi_str}</td>"
            f'<td style="{cross_style}">{cross_str}</td>'
            f"<td>{alert_html}</td>"
            f"</tr>"
        )

    ai_section = ""
    if ai_notes:
        note_rows = "".join(
            f"<tr><td><strong>{_html.escape(t)}</strong></td>"
            f"<td>{_html.escape(note or '')}</td></tr>"
            for t, note in ai_notes.items()
            if note
        )
        if note_rows:
            ai_section = f"""
<h3 style="margin-top:28px;">AI Context Notes</h3>
<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse:collapse;width:100%;margin-bottom:16px;">
  <tr style="background:#e9ecef;"><th style="width:90px;">Ticker</th><th>Note</th></tr>
  {note_rows}
</table>
<p style="font-size:0.82em;color:#6c757d;">
  AI notes reflect publicly available context only. They are not recommendations.
</p>"""

    date_str = run_date.strftime("%B %d, %Y")
    row_html = "\n  ".join(rows)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Watchlist Monitor — {date_str}</title></head>
<body style="font-family:Arial,sans-serif;max-width:920px;margin:auto;padding:24px;color:#212529;">

<h2 style="border-bottom:2px solid #0d6efd;padding-bottom:8px;">
  Watchlist Monitor &mdash; {date_str}
</h2>
<p>
  <strong>{total_alerts} alert(s)</strong> across
  <strong>{tickers_with_alerts}</strong> ticker(s) &nbsp;|&nbsp;
  {len(results)} ticker(s) scanned
</p>

<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse:collapse;width:100%;margin-bottom:24px;">
  <tr style="background:#0d6efd;color:#fff;text-align:left;">
    <th>Ticker</th>
    <th>Price</th>
    <th>Daily&nbsp;Chg</th>
    <th>RSI&nbsp;(14)</th>
    <th>MA&nbsp;Cross</th>
    <th>Alerts</th>
  </tr>
  {row_html}
</table>
{ai_section}

<hr style="margin-top:32px;">
<p style="font-size:0.78em;color:#6c757d;line-height:1.5;">
  <strong>Disclaimer:</strong> This report is <em>informational only</em>.
  It identifies current technical conditions as of market close &mdash; it does
  <strong>not</strong> forecast prices, predict future performance, or constitute
  financial advice, investment recommendations, or a solicitation to buy or sell
  any security. Always conduct your own due diligence before making any investment
  decision.
</p>
</body>
</html>"""


def send_or_print(subject: str, html_body: str) -> None:
    """Send the HTML email via SMTP, or print it to stdout if any env var is missing (dry run)."""
    env = {k: os.environ.get(k) for k in _REQUIRED_VARS}
    missing = [k for k, v in env.items() if v is None]

    if missing:
        print(f"[DRY RUN] Missing SMTP env vars: {', '.join(missing)}", flush=True)
        print(f"[DRY RUN] Subject : {subject}", flush=True)
        print("=" * 72, flush=True)
        # Flush the text layer before writing raw bytes so ordering is preserved
        sys.stdout.flush()
        sys.stdout.buffer.write(html_body.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
        print("=" * 72, flush=True)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = env["SMTP_USER"]
    msg["To"] = env["MAIL_TO"]
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    port = int(env["SMTP_PORT"])
    if port == 465:
        with smtplib.SMTP_SSL(env["SMTP_HOST"], port) as server:
            server.login(env["SMTP_USER"], env["SMTP_PASS"])
            server.sendmail(env["SMTP_USER"], [env["MAIL_TO"]], msg.as_string())
    else:
        with smtplib.SMTP(env["SMTP_HOST"], port) as server:
            server.ehlo()
            server.starttls()
            server.login(env["SMTP_USER"], env["SMTP_PASS"])
            server.sendmail(env["SMTP_USER"], [env["MAIL_TO"]], msg.as_string())

    print(f"Email sent to {env['MAIL_TO']} — {subject}")
