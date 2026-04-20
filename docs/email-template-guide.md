# Email Template Guide

Templates live in a single Google Doc. The pipeline fetches them at runtime via the Drive API.

**Doc ID:** `1MQOhCOSRZ9zi7-XWVEh-7e-BCjHjeCgjg2l-IxJskp4`

Set in `config.yaml`:
```yaml
google_doc_id: "1MQOhCOSRZ9zi7-XWVEh-7e-BCjHjeCgjg2l-IxJskp4"
```

---

## Doc Structure

Each template is a **Heading 1** section. The heading text must exactly match the template name in `decision_tree.yaml`.

```
[Heading 1]  tell_me_more_general
[Paragraph]  Subject line goes here
[Paragraph]  Hi {name}, ...
[Paragraph]  More body content...

[Heading 1]  waitlist
[Paragraph]  Subject line goes here
[Paragraph]  Body content...
```

Rules:
- **Heading 1** = template name (must match decision tree exactly, case-sensitive)
- **First non-empty paragraph** under the heading = email subject
- **Everything after** = HTML email body
- Formatting (bold, italic, links, images) is preserved from the doc

---

## Supported Placeholders

Use these anywhere in the subject or body:

| Placeholder | Value |
|-------------|-------|
| `{name}` | Driver's full name from their form submission |
| `{address}` | Driver's address from their form submission |
| `{city}` | Nearest It's Electric charger city |
| `{state}` | Driver's state (extracted from their address) |

---

## Template Names

These must match what the decision tree routes to:

| Name | When used |
|------|-----------|
| `tell_me_more_general` | Driver near a charger, prompts for vehicle info |
| `tell_me_more_massachusetts` | MA driver near MA charger |
| `tell_me_more_dc` | DC driver near DC charger |
| `tell_me_more_brooklyn` | NY driver near Brooklyn charger |
| `general_car_info` | Driver already right next to a charger |
| `waitlist` | Driver too far from any charger, or outside priority states |

---

## Auth Note

The pipeline needs `drive.readonly` scope to fetch the doc. If you add `google_doc_id` to `config.yaml` for the first time, delete `token.json` and re-run — it will prompt a one-time re-auth in the browser.
