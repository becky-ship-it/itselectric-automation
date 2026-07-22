# Email Template Guide

Templates are stored in the app database and edited in the web UI. After starting the server, open [Config](http://localhost:8000/config), choose a template, edit its subject and Markdown body, then select **Save**.

Template names must match the names used by the decision tree. The first startup seeds empty templates from the leaf names in `decision_tree.yaml`; after that, the database is the source of truth.

## Placeholders

Use these in a subject or body:

| Placeholder | Value |
|-------------|-------|
| `{name}` | Contact's extracted name |
| `{address}` | Contact's extracted address |
| `{city}` | Nearest charger's city |
| `{state}` | Contact's state |

Unknown placeholders are left unchanged.

## Markdown

Template bodies support standard Markdown, including headings, bold text, italic text, links, lists, and images. Write only message content: the app applies the email layout when it previews or sends the message.

```markdown
Hi {name},

We have a charger near you in **{city}**.

[Learn more](https://itselectric.us/)
```

See the in-app [Email Template Guide](http://localhost:8000/guide/templates) for formatting examples.
