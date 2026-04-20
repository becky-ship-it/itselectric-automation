import { useState, useEffect } from 'react'
import yaml from 'js-yaml'
import { marked } from 'marked'
import {
  listTemplates,
  updateTemplate,
  getDecisionTree,
  updateDecisionTree,
  testDecisionTree,
} from '../api/client'
import type { Template, DecisionTreeTestResult } from '../api/client'
import TreeNodeEditor from '../components/TreeNodeEditor'
import type { TreeNode } from '../components/TreeNodeEditor'

export default function Config() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [subject, setSubject] = useState('')
  const [bodyMd, setBodyMd] = useState('')
  const [tmplSaving, setTmplSaving] = useState(false)
  const [tmplSaved, setTmplSaved] = useState(false)
  const [tmplError, setTmplError] = useState<string | null>(null)

  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [tree, setTree] = useState<TreeNode | null>(null)
  const [treeYaml, setTreeYaml] = useState('')
  const [yamlError, setYamlError] = useState<string | null>(null)
  const [yamlExpanded, setYamlExpanded] = useState(false)
  const [treeSaving, setTreeSaving] = useState(false)
  const [treeSaved, setTreeSaved] = useState(false)
  const [treeTesting, setTreeTesting] = useState(false)
  const [treeError, setTreeError] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<DecisionTreeTestResult[] | null>(null)

  useEffect(() => {
    Promise.all([listTemplates(), getDecisionTree()])
      .then(([tmpls, rawTree]) => {
        setTemplates(tmpls as Template[])
        if (rawTree && typeof rawTree === 'object') {
          setTree(rawTree as TreeNode)
          setTreeYaml(yaml.dump(rawTree))
        }
      })
      .catch(() => setLoadError('Failed to load config. Is the server running?'))
      .finally(() => setLoading(false))
  }, [])

  function selectTemplate(name: string) {
    const t = templates.find((t) => t.name === name)
    if (!t) return
    setSelectedName(name)
    setSubject(t.subject ?? '')
    setBodyMd(t.body_md ?? '')
    setTmplSaved(false)
    setTmplError(null)
  }

  function handleTreeChange(newTree: TreeNode) {
    setTree(newTree)
    setTreeYaml(yaml.dump(newTree))
    setYamlError(null)
    setTreeSaved(false)
  }

  function handleYamlChange(newYaml: string) {
    setTreeYaml(newYaml)
    setTreeSaved(false)
    try {
      const parsed = yaml.load(newYaml)
      if (parsed && typeof parsed === 'object') {
        setTree(parsed as TreeNode)
        setYamlError(null)
      }
    } catch (err) {
      setYamlError(String(err))
    }
  }

  async function handleSaveTemplate() {
    if (!selectedName) return
    setTmplSaving(true)
    setTmplError(null)
    try {
      const updated = await updateTemplate(selectedName, { subject, body_md: bodyMd })
      setTemplates((ts) => ts.map((t) => (t.name === selectedName ? updated : t)))
      setTmplSaved(true)
    } catch (err) {
      setTmplError(String(err))
    } finally {
      setTmplSaving(false)
    }
  }

  function download(content: string, filename: string, mime: string) {
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([content], { type: mime }))
    a.download = filename
    a.click()
  }

  async function handleSaveTree() {
    if (!tree) return
    setTreeSaving(true)
    setTreeError(null)
    try {
      await updateDecisionTree(tree as Record<string, unknown>)
      setTreeSaved(true)
    } catch (err) {
      setTreeError(String(err))
    } finally {
      setTreeSaving(false)
    }
  }

  async function handleTestTree() {
    setTreeTesting(true)
    setTreeError(null)
    setTestResults(null)
    try {
      const res = await testDecisionTree()
      setTestResults(res.results)
    } catch (err) {
      setTreeError(String(err))
    } finally {
      setTreeTesting(false)
    }
  }

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-semibold text-gray-900">Config</h1>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Templates</h2>
          <button
            onClick={() => download(JSON.stringify(templates, null, 2), 'templates.json', 'application/json')}
            disabled={templates.length === 0}
            className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40 transition-colors"
          >
            ↓ Download JSON
          </button>
        </div>
        <div className="flex border border-gray-200 rounded-lg overflow-hidden min-h-64">
          <div className="w-52 shrink-0 border-r border-gray-200 overflow-y-auto">
            {loading ? (
              <div className="p-3 text-sm text-gray-400">Loading…</div>
            ) : loadError ? (
              <div className="p-3 text-sm text-red-600">{loadError}</div>
            ) : templates.length === 0 ? (
              <div className="p-3 text-sm text-gray-400">No templates.</div>
            ) : (
              templates.map((t) => (
                <button
                  key={t.name}
                  onClick={() => selectTemplate(t.name)}
                  className={`w-full text-left px-3 py-2.5 text-sm border-b border-gray-100 truncate transition-colors ${
                    selectedName === t.name
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {t.name}
                </button>
              ))
            )}
          </div>

          <div className="flex-1 p-4 space-y-3">
            {!selectedName ? (
              <p className="text-sm text-gray-400">Select a template to edit.</p>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => { setSubject(e.target.value); setTmplSaved(false) }}
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Body (Markdown)</label>
                  <textarea
                    value={bodyMd}
                    onChange={(e) => { setBodyMd(e.target.value); setTmplSaved(false) }}
                    rows={8}
                    className="w-full px-3 py-1.5 text-sm font-mono border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                    placeholder="Write email body in Markdown. **Bold**, *italic*, [links](url)."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Preview</label>
                  <iframe
                    srcDoc={marked(bodyMd) as string}
                    sandbox=""
                    title="Template preview"
                    className="w-full h-48 border border-gray-200 rounded-lg bg-white"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <button
                    aria-label="Save template"
                    onClick={() => void handleSaveTemplate()}
                    disabled={tmplSaving}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                               hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {tmplSaving ? 'Saving…' : 'Save'}
                  </button>
                  {tmplSaved && <span className="text-sm text-green-700">Saved.</span>}
                  {tmplError && <span className="text-sm text-red-600">{tmplError}</span>}
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Decision Tree</h2>
          <button
            onClick={() => download(treeYaml, 'decision_tree.yaml', 'text/yaml')}
            disabled={!tree}
            className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40 transition-colors"
          >
            ↓ Download YAML
          </button>
        </div>
        <div className="space-y-4">
          {/* Visual editor */}
          <div className="p-4 border border-gray-200 rounded-lg min-h-24">
            {tree ? (
              <TreeNodeEditor
                node={tree}
                onChange={handleTreeChange}
                templates={templates.map((t) => t.name)}
              />
            ) : (
              <button
                onClick={() => handleTreeChange({
                  condition: { field: 'distance_miles', op: 'lte', value: '' },
                  then: { template: '' },
                  else: { template: '' },
                })}
                className="text-sm text-blue-600 hover:underline"
              >
                + Add root node
              </button>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <button
              aria-label="Save decision tree"
              onClick={() => void handleSaveTree()}
              disabled={treeSaving || !tree}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                         hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {treeSaving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => void handleTestTree()}
              disabled={treeTesting}
              className="px-4 py-2 bg-gray-100 text-gray-700 border border-gray-300 rounded-lg text-sm font-medium
                         hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              {treeTesting ? 'Testing…' : 'Test'}
            </button>
            {treeSaved && <span className="text-sm text-green-700">Saved.</span>}
            {treeError && <span className="text-sm text-red-600">{treeError}</span>}
          </div>

          {/* Advanced YAML panel */}
          <div>
            <button
              aria-expanded={yamlExpanded}
              onClick={() => setYamlExpanded((v) => !v)}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <span>{yamlExpanded ? '▼' : '▶'}</span>
              <span>Advanced (YAML)</span>
            </button>
            {yamlExpanded && (
              <div className="mt-2 space-y-1">
                <textarea
                  aria-label="Decision tree YAML"
                  value={treeYaml}
                  onChange={(e) => handleYamlChange(e.target.value)}
                  rows={12}
                  className="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg
                             focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                />
                {yamlError && <p className="text-xs text-red-600">{yamlError}</p>}
              </div>
            )}
          </div>

          {/* Test results table */}
          {testResults !== null && (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Name', 'Address', 'Template'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {testResults.map((r) => (
                    <tr key={r.id}>
                      <td className="px-4 py-3 text-gray-900">{r.name ?? '(unparsed)'}</td>
                      <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{r.address ?? '—'}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">{r.template ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
