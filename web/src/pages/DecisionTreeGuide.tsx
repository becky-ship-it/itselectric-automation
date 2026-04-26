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

function Pill({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-medium ${color}`}>
      {children}
    </span>
  )
}

export default function DecisionTreeGuide() {
  return (
    <div className="max-w-2xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Decision Tree Guide</h1>
          <p className="text-sm text-gray-500 mt-1">How to route contacts to the right email template.</p>
        </div>
        <Link to="/config" className="text-sm text-blue-600 hover:underline">← Back to Config</Link>
      </div>

      <Section title="How it works">
        <p className="text-sm text-gray-700 leading-relaxed">
          When the pipeline processes a contact, the decision tree evaluates conditions about
          that contact (their distance to the nearest charger, their state, the charger's city, etc.)
          and selects which email template to send. It's a nested if/then/else structure — each
          node checks one condition and branches to either a template or another condition.
        </p>
      </Section>

      <Section title="Available fields">
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full text-sm divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Field', 'Type', 'Description'].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100 text-sm">
              {[
                ['distance_miles', 'number', 'Miles from contact\'s address to the nearest charger'],
                ['driver_state', 'string', 'US state code from the contact\'s address (e.g. NY, CA)'],
                ['charger_state', 'string', 'US state code where the nearest charger is located'],
                ['charger_city', 'string', 'City name where the nearest charger is located'],
              ].map(([f, t, d]) => (
                <tr key={f}>
                  <td className="px-4 py-2 font-mono text-orange-600">{f}</td>
                  <td className="px-4 py-2 text-gray-500">{t}</td>
                  <td className="px-4 py-2 text-gray-700">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Operators">
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full text-sm divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Operator', 'Meaning', 'Example'].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100 text-sm">
              {[
                ['lte', 'Less than or equal to', 'distance_miles lte 0.5'],
                ['lt', 'Less than', 'distance_miles lt 1'],
                ['gte', 'Greater than or equal to', 'distance_miles gte 5'],
                ['gt', 'Greater than', 'distance_miles gt 100'],
                ['eq', 'Equal to', 'charger_state eq NY'],
                ['in', 'Value is in a comma-separated list', 'driver_state in NY,NJ,CT'],
              ].map(([op, m, ex]) => (
                <tr key={op}>
                  <td className="px-4 py-2"><Pill color="bg-blue-50 text-blue-700">{op}</Pill></td>
                  <td className="px-4 py-2 text-gray-700">{m}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{ex}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Node structure">
        <p className="text-sm text-gray-700 leading-relaxed">
          Each node has a <Code>condition</Code>, a <Code>then</Code> branch, and an <Code>else</Code> branch.
          A branch can be either a <strong>template</strong> (leaf — stops here and sends that email)
          or another <strong>condition node</strong> (continues evaluating).
        </p>
        <Block>{`condition:
  field: distance_miles
  op: lte
  value: "0.5"
then:
  template: nearby_charger          # send this template if true
else:
  condition:                        # evaluate another condition if false
    field: driver_state
    op: in
    value: "NY,NJ,CT"
  then:
    template: tri_state_waitlist
  else:
    template: general_waitlist`}</Block>
      </Section>

      <Section title="Visual editor tips">
        <ul className="text-sm text-gray-700 space-y-2 list-disc list-inside">
          <li>Use <strong>+ condition</strong> on any branch to nest another check inside it.</li>
          <li>
            The <strong>then</strong> and <strong>else</strong> dropdowns show all available templates —
            create templates first in the Templates section above, then reference them here.
          </li>
          <li>
            Click <strong>Test</strong> to run every existing contact through the tree and see which
            template they'd receive — useful for validating changes before saving.
          </li>
          <li>
            Use <strong>Advanced (YAML)</strong> to paste or edit the tree directly if the
            visual editor becomes unwieldy for complex trees.
          </li>
          <li>
            Changes are not applied until you click <strong>Save</strong>.
          </li>
        </ul>
      </Section>

      <Section title="Example: full tree">
        <p className="text-sm text-gray-500">A tree that handles nearby contacts, out-of-state contacts, and everyone else:</p>
        <Block>{`condition:
  field: distance_miles
  op: lte
  value: "0.5"
then:
  template: general_car_info       # very close — ask for car info
else:
  condition:
    field: distance_miles
    op: gt
    value: "100"
  then:
    template: waitlist             # far away — add to waitlist
  else:
    condition:
      field: driver_state
      op: in
      value: "NY,NJ"
    then:
      template: tell_me_more_brooklyn
    else:
      condition:
        field: charger_state
        op: eq
        value: "DC"
      then:
        template: tell_me_more_dc
      else:
        template: tell_me_more_general`}</Block>
      </Section>

      <Section title="Downloading & restoring">
        <p className="text-sm text-gray-700 leading-relaxed">
          Use <strong>↓ Download YAML</strong> to back up the current tree. To restore,
          paste the YAML into the <strong>Advanced (YAML)</strong> panel and click <strong>Save</strong>.
          The YAML format is identical to what's shown in the examples above.
        </p>
      </Section>
    </div>
  )
}
