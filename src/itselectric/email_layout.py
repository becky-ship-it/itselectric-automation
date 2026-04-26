"""Branded email wrapper: converts Markdown body to full HTML email."""

import markdown as _md

_LOGO_URL = (
    "https://cdn.prod.website-files.com/6297984862f8ce031cbee04f"
    "/63b48312971b511607d06d8d_ItsElectric%20Logo1000.svg"
)

_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"

_HEADER = f"""\
<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background:#ffffff;padding:24px 40px;">
      <img src="{_LOGO_URL}"
           alt="it's electric"
           width="200"
           height="49"
           style="display:block;border:0;outline:none;max-width:200px;height:auto;" />
    </td>
  </tr>
</table>"""

_MARK_URL = (
    "https://cdn.prod.website-files.com/6297984862f8ce031cbee04f"
    "/65450085e370451bf4e371df_d451d9276d1e73092d67f8bab99a4180.png"
)

_FOOTER = f"""\
<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background:#0f0f0f;padding:28px 40px;">
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="vertical-align:middle;padding-right:14px;">
            <img src="{_MARK_URL}"
                 alt="it's electric mark"
                 width="36" height="36"
                 style="display:block;border:0;outline:none;" />
          </td>
          <td style="vertical-align:middle;">
            <span style="font-family:{_FONT};font-size:15px;font-weight:700;\
color:#ffffff;">it's electric</span>
          </td>
        </tr>
      </table>
      <p style="margin:12px 0 4px;font-family:{_FONT};\
font-size:12px;color:rgba(255,255,255,0.5);">The Future. It's Electric.</p>
      <p style="margin:16px 0 0;font-family:{_FONT};\
font-size:11px;color:rgba(255,255,255,0.35);">
        Questions? Reply to this email.
        &nbsp;·&nbsp;
        <a href="https://itselectric.us" style="color:rgba(255,255,255,0.35);\
text-decoration:underline;">itselectric.us</a>
      </p>
    </td>
  </tr>
</table>"""

_BODY_STYLES = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
    "font-size:15px;line-height:1.75;color:#1a1a1a;"
    "padding:36px 40px 32px;"
)

_PROSE_CSS = """
    <style>
      .prose h1,.prose h2,.prose h3{margin:0 0 12px;font-weight:700;color:#0f0f0f}
      .prose h1{font-size:22px} .prose h2{font-size:18px} .prose h3{font-size:15px}
      .prose p{margin:0 0 16px}
      .prose ul,.prose ol{margin:0 0 16px;padding-left:24px}
      .prose li{margin-bottom:6px}
      .prose a{color:#FF5F1F;text-decoration:none}
      .prose a:hover{text-decoration:underline}
      .prose strong{font-weight:700;color:#0f0f0f}
      .prose hr{border:none;border-top:1px solid #e5e5e5;margin:24px 0}
      .prose blockquote{border-left:3px solid #FF5F1F;margin:0 0 16px;
        padding:8px 16px;color:#555;font-style:italic}
      .prose img{max-width:100%;height:auto;display:block;margin:16px 0;border-radius:4px}
    </style>
"""


def render_email(body_md: str) -> str:
    """Convert a Markdown email body to a complete branded HTML email."""
    body_html = _md.markdown(body_md or "", extensions=["extra"])
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  {_PROSE_CSS}
</head>
<body style="margin:0;padding:0;background:#f5f5f5;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:4px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,0.08);">
        <tr><td style="padding:0">{_HEADER}</td></tr>
        <tr>
          <td style="{_BODY_STYLES}">
            <div class="prose">{body_html}</div>
          </td>
        </tr>
        <tr><td style="padding:0">{_FOOTER}</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
