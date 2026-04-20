"""Hard-coded email wrapper: converts Markdown body to full HTML email."""

import markdown as _md

_HEADER = """\
<div style="background:#0f172a;padding:24px 32px;text-align:center;">
  <span style="font-family:sans-serif;font-size:22px;font-weight:700;color:#ffffff;">
    It's Electric
  </span>
</div>"""

_FOOTER = """\
<div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:24px 32px;\
text-align:center;font-family:sans-serif;font-size:13px;color:#64748b;">
  <p style="margin:0 0 8px;">It's Electric EV Charging · Washington DC Area</p>
  <p style="margin:0;">Questions? Reply to this email.</p>
</div>"""


def render_email(body_md: str) -> str:
    """Convert a Markdown email body to a complete HTML email with header and footer."""
    body_html = _md.markdown(body_md, extensions=["extra"])
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f1f5f9;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;">
        <tr><td>{_HEADER}</td></tr>
        <tr><td style="padding:32px;font-family:sans-serif;font-size:15px;\
line-height:1.7;color:#1e293b;">{body_html}</td></tr>
        <tr><td>{_FOOTER}</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
