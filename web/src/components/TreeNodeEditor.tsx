const FIELDS = ['distance_miles', 'driver_state', 'charger_state', 'charger_city'] as const
const OPS = ['lt', 'lte', 'gt', 'gte', 'eq', 'ne', 'in'] as const
const MAX_DEPTH = 12

export type LeafNode = { template: string }
export type ConditionNode = {
  condition: { field: string; op: string; value: string | number }
  then: TreeNode
  else: TreeNode
}
export type TreeNode = LeafNode | ConditionNode

export function isLeaf(node: TreeNode | null | undefined): node is LeafNode {
  if (!node || typeof node !== 'object') return true
  return 'template' in node
}

const BLANK_CONDITION: ConditionNode = {
  condition: { field: 'distance_miles', op: 'lte', value: '' },
  then: { template: '' },
  else: { template: '' },
}

interface Props {
  node: TreeNode
  onChange: (node: TreeNode) => void
  templates: string[]
  depth?: number
}

export default function TreeNodeEditor({ node, onChange, templates, depth = 0 }: Props) {
  if (depth >= MAX_DEPTH) {
    return <div className="text-xs text-red-500">Max depth reached</div>
  }

  if (isLeaf(node)) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-gray-400">→ template:</span>
        <select
          value={node.template}
          onChange={(e) => onChange({ template: e.target.value })}
          className="text-sm border border-gray-300 rounded px-2 py-1
                     focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">— choose —</option>
          {templates.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <button
          aria-label="Convert to condition"
          onClick={() => onChange({ ...BLANK_CONDITION })}
          className="text-xs text-blue-600 hover:underline"
        >
          + condition
        </button>
      </div>
    )
  }

  const { condition, then, else: elseNode } = node
  const thenNode: TreeNode = then ?? { template: '' }
  const elseNodeSafe: TreeNode = elseNode ?? { template: '' }

  function updateCondition(patch: Partial<typeof condition>) {
    onChange({ ...node, condition: { ...condition, ...patch } })
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">if</span>
        <select
          aria-label="Condition field"
          value={condition.field}
          onChange={(e) => updateCondition({ field: e.target.value })}
          className="text-sm border border-gray-300 rounded px-2 py-1
                     focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <select
          aria-label="Condition operator"
          value={condition.op}
          onChange={(e) => updateCondition({ op: e.target.value })}
          className="text-sm border border-gray-300 rounded px-2 py-1
                     focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {OPS.map((op) => <option key={op} value={op}>{op}</option>)}
        </select>
        <input
          aria-label="Condition value"
          type="text"
          value={String(condition.value)}
          onChange={(e) => updateCondition({ value: e.target.value })}
          className="text-sm border border-gray-300 rounded px-2 py-1 w-24
                     focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="value"
        />
        <button
          aria-label="Remove condition"
          onClick={() => onChange({ template: '' })}
          className="text-xs text-red-500 hover:underline"
        >
          × remove
        </button>
      </div>
      <div className="pl-6 border-l-2 border-gray-100 space-y-3">
        <div>
          <span className="text-xs font-semibold text-green-600 uppercase tracking-wide">then</span>
          <div className="mt-1">
            <TreeNodeEditor
              node={thenNode}
              onChange={(n) => onChange({ ...node, then: n })}
              templates={templates}
              depth={depth + 1}
            />
          </div>
        </div>
        <div>
          <span className="text-xs font-semibold text-red-500 uppercase tracking-wide">else</span>
          <div className="mt-1">
            <TreeNodeEditor
              node={elseNodeSafe}
              onChange={(n) => onChange({ ...node, else: n })}
              templates={templates}
              depth={depth + 1}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
