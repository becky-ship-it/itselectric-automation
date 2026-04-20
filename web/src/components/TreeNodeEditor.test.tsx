import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import TreeNodeEditor from './TreeNodeEditor'
import type { TreeNode } from './TreeNodeEditor'

const TEMPLATES = ['general_car_info', 'waitlist', 'tell_me_more_dc', 'close', 'far']

test('renders leaf node with template dropdown', () => {
  const leaf: TreeNode = { template: 'waitlist' }
  render(<TreeNodeEditor node={leaf} onChange={() => {}} templates={TEMPLATES} />)
  expect(screen.getByDisplayValue('waitlist')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /convert to condition/i })).toBeInTheDocument()
})

test('selecting a template calls onChange with updated leaf', async () => {
  const leaf: TreeNode = { template: '' }
  const onChange = vi.fn()
  render(<TreeNodeEditor node={leaf} onChange={onChange} templates={TEMPLATES} />)
  await userEvent.selectOptions(screen.getByRole('combobox'), 'waitlist')
  expect(onChange).toHaveBeenCalledWith({ template: 'waitlist' })
})

test('clicking convert to condition replaces leaf with a condition node', async () => {
  const leaf: TreeNode = { template: 'waitlist' }
  const onChange = vi.fn()
  render(<TreeNodeEditor node={leaf} onChange={onChange} templates={TEMPLATES} />)
  await userEvent.click(screen.getByRole('button', { name: /convert to condition/i }))
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
    condition: expect.objectContaining({ field: 'distance_miles' }),
  }))
})

test('renders condition node with field, op, and value controls', () => {
  const node: TreeNode = {
    condition: { field: 'distance_miles', op: 'lte', value: '5' },
    then: { template: 'close' },
    else: { template: 'far' },
  }
  render(<TreeNodeEditor node={node} onChange={() => {}} templates={TEMPLATES} />)
  expect(screen.getByRole('combobox', { name: /condition field/i })).toHaveValue('distance_miles')
  expect(screen.getByRole('combobox', { name: /condition operator/i })).toHaveValue('lte')
  expect(screen.getByRole('textbox', { name: /condition value/i })).toHaveValue('5')
  expect(screen.getByRole('button', { name: /remove condition/i })).toBeInTheDocument()
})

test('changing field calls onChange with updated condition', async () => {
  const node: TreeNode = {
    condition: { field: 'distance_miles', op: 'lte', value: '5' },
    then: { template: 'close' },
    else: { template: 'far' },
  }
  const onChange = vi.fn()
  render(<TreeNodeEditor node={node} onChange={onChange} templates={TEMPLATES} />)
  await userEvent.selectOptions(
    screen.getByRole('combobox', { name: /condition field/i }),
    'driver_state'
  )
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
    condition: expect.objectContaining({ field: 'driver_state' }),
  }))
})

test('clicking remove converts condition to empty leaf', async () => {
  const node: TreeNode = {
    condition: { field: 'distance_miles', op: 'lte', value: '5' },
    then: { template: 'close' },
    else: { template: 'far' },
  }
  const onChange = vi.fn()
  render(<TreeNodeEditor node={node} onChange={onChange} templates={TEMPLATES} />)
  await userEvent.click(screen.getByRole('button', { name: /remove condition/i }))
  expect(onChange).toHaveBeenCalledWith({ template: '' })
})

test('renders then and else branches for condition node', () => {
  const node: TreeNode = {
    condition: { field: 'distance_miles', op: 'lte', value: '5' },
    then: { template: 'close' },
    else: { template: 'far' },
  }
  render(<TreeNodeEditor node={node} onChange={() => {}} templates={TEMPLATES} />)
  expect(screen.getByText('then')).toBeInTheDocument()
  expect(screen.getByText('else')).toBeInTheDocument()
  expect(screen.getByDisplayValue('close')).toBeInTheDocument()
  expect(screen.getByDisplayValue('far')).toBeInTheDocument()
})
