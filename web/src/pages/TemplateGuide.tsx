import { Link } from 'react-router-dom'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-gray-900 border-b border-gray-200 pb-2">{title}</h2>
      {children}
    </section>
  )
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-sm font-mono">
      {children}
    </code>
  )
}

function Block({ children }: { children: string }) {
  return (
    <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm font-mono text-gray-800 whitespace-pre-wrap overflow-x-auto">
      {children}
    </pre>
  )
}

export default function TemplateGuide() {
  return (
    <div className="max-w-2xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Email Template Guide</h1>
          <p className="text-sm text-gray-500 mt-1">How to write and format outbound email templates.</p>
        </div>
        <Link to="/config" className="text-sm text-blue-600 hover:underline">← Back to Config</Link>
      </div>

      <Section title="Overview">
        <p className="text-sm text-gray-700 leading-relaxed">
          Templates are written in <strong>Markdown</strong> and automatically wrapped in the
          it's electric branded email layout (header, footer, styling) when previewed or sent.
          Write the body content only — no need to add a header or sign-off boilerplate to the template itself.
        </p>
      </Section>

      <Section title="Template Variables">
        <p className="text-sm text-gray-700 leading-relaxed">
          Use curly braces to insert contact data into the template. These are replaced with the
          actual values when an email is queued for a contact.
        </p>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full text-sm divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Variable', 'Value'].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {[
                ['{name}', "Contact's full name"],
                ['{address}', "Contact's street address"],
                ['{city}', 'City of the nearest charger'],
                ['{state}', "Contact's state (from their address)"],
              ].map(([v, d]) => (
                <tr key={v}>
                  <td className="px-4 py-2 font-mono text-orange-600">{v}</td>
                  <td className="px-4 py-2 text-gray-700">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Block>{`Hi {name},

We have a charger near you in {city}! ...`}</Block>
      </Section>

      <Section title="Text Formatting">
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full text-sm divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Markdown', 'Result'].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {[
                ['**bold text**', <strong>bold text</strong>],
                ['*italic text*', <em>italic text</em>],
                ['# Heading 1', <span className="text-lg font-bold">Heading 1</span>],
                ['## Heading 2', <span className="text-base font-bold">Heading 2</span>],
                ['--- (on its own line)', <hr className="border-gray-300 w-24" />],
              ].map(([md, result], i) => (
                <tr key={i}>
                  <td className="px-4 py-2 font-mono text-gray-700 text-xs">{md}</td>
                  <td className="px-4 py-2 text-gray-900">{result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Lists">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Markdown</p>
            <Block>{`- First item
- Second item
- Third item

1. Step one
2. Step two
3. Step three`}</Block>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Renders as</p>
            <div className="bg-white border border-gray-200 rounded-lg p-4 text-sm text-gray-800 space-y-3">
              <ul className="list-disc list-inside space-y-1">
                <li>First item</li><li>Second item</li><li>Third item</li>
              </ul>
              <ol className="list-decimal list-inside space-y-1">
                <li>Step one</li><li>Step two</li><li>Step three</li>
              </ol>
            </div>
          </div>
        </div>
      </Section>

      <Section title="Links">
        <p className="text-sm text-gray-700">
          Syntax: <Code>[link text](https://example.com)</Code>
        </p>
        <Block>{`Sign up on [our waitlist](https://itselectric.us/waitlist) to stay updated.`}</Block>
        <p className="text-sm text-gray-500">
          Links render in orange to match the it's electric brand.
        </p>
      </Section>

      <Section title="Images">
        <p className="text-sm text-gray-700 leading-relaxed">
          Images must be publicly hosted at an accessible URL. There are two ways to add them.
        </p>

        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Option 1 — Markdown syntax (simple, no size control)</p>
          <Block>{`![Map of chargers](https://example.com/charger-map.png)`}</Block>
          <p className="text-sm text-gray-500">Images inserted this way fill the full email width by default.</p>
        </div>

        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Option 2 — HTML tag (use this to control size)</p>
          <Block>{`<img src="https://example.com/charger-map.png" width="300" alt="Map of chargers">`}</Block>
          <p className="text-sm text-gray-500">
            Use the <Code>width</Code> attribute (in pixels) to set image size. This works reliably across all email clients.
            Do <strong>not</strong> use a CSS <Code>style</Code> attribute — many email clients strip inline styles from images.
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
          <strong>To resize an image:</strong> replace the <Code>![alt](url)</Code> Markdown line with an{' '}
          <Code>{'<img src="url" width="300">'}</Code> tag. Don't keep both — they'll show as two separate images.
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          <strong>Hosting tip:</strong> Google Drive, Dropbox (with a direct link), Imgur, or any CDN
          work well. The URL must be publicly accessible — no login required.
        </div>
      </Section>

      <Section title="Full example">
        <Block>{`Hi {name},

Thanks for signing up with it's electric! We have chargers near you in **{city}**.

Here's what you need to know:

- Charging is Level 2 (220V) — plug in when you get home, wake up full
- Bring your own portable cable (Type 1 or Type 2)
- No app needed — just plug in

![Charger photo](https://itselectric.us/charger-photo.jpg)

[View chargers near you](https://itselectric.us/map)

All the best,
Becky`}</Block>
      </Section>
    </div>
  )
}
