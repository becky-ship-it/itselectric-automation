# web/

React + TypeScript + Tailwind frontend for the It's Electric automation server.

Built with Vite. Served as static files from `web/dist/` by the FastAPI server at `http://localhost:8000`.

## Pages

| Route | Page |
|-------|------|
| `/` | Dashboard — pipeline run controls, pending/unparsed counts |
| `/inbox` | Contact list with All / Pending / Unparsed tabs; detail panel with email preview and send/fix controls |
| `/history` | Full contact table with search and CSV/JSON download |
| `/config` | Email template editor + decision tree editor |
| `/logs` | Live log stream (SSE) |
| `/guide/templates` | Email template authoring guide |
| `/guide/decision-tree` | Decision tree syntax reference |

## Development

```bash
npm install
npm run dev        # dev server at http://localhost:5173 (proxies /api to :8000)
npm test           # Vitest unit tests
npm run build      # production build → dist/
```

The `../run_server.sh` script runs `npm install && npm run build` automatically before starting the Python server, so manual builds are only needed during frontend development.

## E2E tests

```bash
npx playwright test           # run headless (server must be running on :8000)
npx playwright test --ui      # interactive UI mode
npx playwright show-report    # view last results
```

Tests live in `e2e/app.spec.ts`. 18 tests covering all pages.
