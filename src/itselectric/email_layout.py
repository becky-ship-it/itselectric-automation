"""Branded email wrapper: converts Markdown body to full HTML email."""

import markdown as _md

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
        <tr>
          <td style="{_BODY_STYLES}">
            <div class="prose">{body_html}</div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
