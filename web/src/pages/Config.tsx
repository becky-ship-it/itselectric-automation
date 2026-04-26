import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import yaml from 'js-yaml'
import {
  listTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  getDecisionTree,
  updateDecisionTree,
  testDecisionTree,
  getConfig,
  updateConfig,
  previewTemplateHtml,
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
  const [newName, setNewName] = useState('')
  const [newNameError, setNewNameError] = useState<string | null>(null)
  const [previewHtml, setPreviewHtml] = useState<string>('')

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

  const [configData, setConfigData] = useState<Record<string, string>>({})
  const [configSaving, setConfigSaving] = useState(false)
  const [configSaved, setConfigSaved] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [showToken, setShowToken] = useState(false)

  const fetchPreview = useCallback((md: string) => {
    previewTemplateHtml(md).then(setPreviewHtml).catch(() => {})
  }, [])

  useEffect(() => {
    const id = setTimeout(() => fetchPreview(bodyMd), 400)
    return () => clearTimeout(id)
  }, [bodyMd, fetchPreview])

  useEffect(() => {
    Promise.all([listTemplates(), getDecisionTree(), getConfig()])
      .then(([tmpls, rawTree, cfg]) => {
        setTemplates(tmpls as Template[])
        if (rawTree && typeof rawTree === 'object') {
          setTree(rawTree as TreeNode)
          setTreeYaml(yaml.dump(rawTree))
        }
        setConfigData(cfg.data ?? {})
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
    fetchPreview(t.body_md ?? '')
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

  async function handleCreateTemplate() {
    const name = newName.trim()
    if (!name) return
    setNewNameError(null)
    try {
      const created = await createTemplate(name, { subject: '', body_md: '' })
      setTemplates((ts) => [...ts, created].sort((a, b) => a.name.localeCompare(b.name)))
      setNewName('')
      selectTemplate(created.name)
    } catch (err) {
      setNewNameError(String(err))
    }
  }

  async function handleDeleteTemplate(name: string) {
    if (!window.confirm(`Delete template "${name}"? This cannot be undone.`)) return
    await deleteTemplate(name)
    setTemplates((ts) => ts.filter((t) => t.name !== name))
    if (selectedName === name) {
      setSelectedName(null)
      setSubject('')
      setBodyMd('')
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

  async function handleSaveConfig() {
    setConfigSaving(true)
    setConfigError(null)
    try {
      const res = await updateConfig(configData)
      setConfigData(res.data ?? {})
      setConfigSaved(true)
    } catch (err) {
      setConfigError(String(err))
    } finally {
      setConfigSaving(false)
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
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Templates</h2>
            <Link
              to="/guide/templates"
              className="text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded px-2 py-0.5 transition-colors"
              title="Template writing guide"
            >
              Guide
            </Link>
          </div>
          <button
            onClick={() => download(JSON.stringify(templates, null, 2), 'templates.json', 'application/json')}
            disabled={templates.length === 0}
            className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40 transition-colors"
          >
            ↓ Download JSON
          </button>
        </div>
        <div className="flex border border-gray-200 rounded-lg overflow-hidden min-h-64">
          <div className="w-52 shrink-0 border-r border-gray-200 flex flex-col">
            <div className="overflow-y-auto flex-1">
              {loading ? (
                <div className="p-3 text-sm text-gray-400">Loading…</div>
              ) : loadError ? (
                <div className="p-3 text-sm text-red-600">{loadError}</div>
              ) : templates.length === 0 ? (
                <div className="p-3 text-sm text-gray-400">No templates.</div>
              ) : (
                templates.map((t) => (
                  <div key={t.name} className="relative group border-b border-gray-100">
                    <button
                      onClick={() => selectTemplate(t.name)}
                      className={`w-full text-left px-3 py-2.5 text-sm truncate transition-colors pr-7 ${
                        selectedName === t.name
                          ? 'bg-blue-50 text-blue-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {t.name}
                    </button>
                    <button
                      aria-label={`Delete template ${t.name}`}
                      onClick={() => void handleDeleteTemplate(t.name)}
                      className="absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100
                                 text-gray-400 hover:text-red-600 transition-all p-0.5 text-base leading-none"
                    >
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
            <div className="border-t border-gray-200 p-2 space-y-1">
              <input
                type="text"
                value={newName}
                onChange={(e) => { setNewName(e.target.value); setNewNameError(null) }}
                onKeyDown={(e) => { if (e.key === 'Enter') void handleCreateTemplate() }}
                placeholder="new_template_name"
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded
                           focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
              {newNameError && <p className="text-xs text-red-600 truncate">{newNameError}</p>}
              <button
                onClick={() => void handleCreateTemplate()}
                disabled={!newName.trim()}
                className="w-full py-1 text-xs font-medium text-blue-600 border border-blue-300
                           rounded hover:bg-blue-50 disabled:opacity-40 transition-colors"
              >
                + New template
              </button>
            </div>
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
                    onKeyDown={(e) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                        e.preventDefault()
                        void handleSaveTemplate()
                      }
                    }}
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Body (Markdown)</label>
                  <textarea
                    key={selectedName ?? ''}
                    defaultValue={bodyMd}
                    onChange={(e) => { setBodyMd(e.target.value); setTmplSaved(false) }}
                    onKeyDown={(e) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                        e.preventDefault()
                        void handleSaveTemplate()
                      }
                    }}
                    rows={8}
                    className="w-full px-3 py-1.5 text-sm font-mono border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                    placeholder="Write email body in Markdown. **Bold**, *italic*, [links](url)."
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Preview</label>
                  <iframe
                    srcDoc={previewHtml}
                    sandbox="allow-same-origin"
                    onLoad={(e) => {
                      const el = e.currentTarget
                      const h = el.contentDocument?.body?.scrollHeight
                      if (h) el.style.height = h + 32 + 'px'
                    }}
                    title="Template preview"
                    className="w-full border border-gray-200 rounded-lg bg-white min-h-[480px]"
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
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Decision Tree</h2>
            <Link
              to="/guide/decision-tree"
              className="text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded px-2 py-0.5 transition-colors"
              title="Decision tree guide"
            >
              Guide
            </Link>
          </div>
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
      <section>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Settings</h2>
        <div className="border border-gray-200 rounded-lg p-4 space-y-4 max-w-lg">
          {[
            { key: 'label', label: 'Pipeline label', type: 'text', placeholder: 'e.g. Production' },
            { key: 'spreadsheet_id', label: 'Google Sheets ID', type: 'text', placeholder: 'Spreadsheet ID from URL' },
            { key: 'max_messages', label: 'Max messages per run', type: 'number', placeholder: '50' },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <input
                type={type}
                value={configData[key] ?? ''}
                onChange={(e) => {
                  setConfigData((d) => ({ ...d, [key]: e.target.value }))
                  setConfigSaved(false)
                }}
                placeholder={placeholder}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">HubSpot access token</label>
            <div className="flex gap-2">
              <input
                type={showToken ? 'text' : 'password'}
                value={configData['hubspot_access_token'] ?? ''}
                onChange={(e) => {
                  setConfigData((d) => ({ ...d, hubspot_access_token: e.target.value }))
                  setConfigSaved(false)
                }}
                placeholder="pat-na1-..."
                className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowToken((v) => !v)}
                className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-300
                           rounded-lg hover:bg-gray-50 transition-colors"
              >
                {showToken ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="auto_send"
              type="checkbox"
              checked={configData['auto_send'] === 'true'}
              onChange={(e) => {
                setConfigData((d) => ({ ...d, auto_send: e.target.checked ? 'true' : 'false' }))
                setConfigSaved(false)
              }}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="auto_send" className="text-sm text-gray-700">Auto-send emails after pipeline run</label>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={() => void handleSaveConfig()}
              disabled={configSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                         hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {configSaving ? 'Saving…' : 'Save'}
            </button>
            {configSaved && <span className="text-sm text-green-700">Saved.</span>}
            {configError && <span className="text-sm text-red-600">{configError}</span>}
          </div>
        </div>
      </section>
    </div>
  )
}
