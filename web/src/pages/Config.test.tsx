import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import Config from './Config'

vi.mock('../api/client', () => ({
  listTemplates: vi.fn().mockResolvedValue([
    { name: 'general_car_info', subject: 'Hello!', body_html: '<p>Hi there</p>', updated_at: '2026-04-20T10:00:00Z' },
    { name: 'waitlist', subject: 'Join the waitlist', body_html: '<p>Waitlist</p>', updated_at: '2026-04-20T10:00:00Z' },
  ]),
  updateTemplate: vi.fn().mockImplementation((name: string, body: { subject: string; body_html: string }) =>
    Promise.resolve({ name, subject: body.subject, body_html: body.body_html, updated_at: new Date().toISOString() })
  ),
  getDecisionTree: vi.fn().mockResolvedValue(null),
  updateDecisionTree: vi.fn().mockResolvedValue({}),
  testDecisionTree: vi.fn().mockResolvedValue({
    results: [
      { id: 'msg1', name: 'Alice Smith', address: '123 Main St DC', parsed: true, template: 'general_car_info' },
      { id: 'msg2', name: null, address: null, parsed: false, template: null },
    ],
  }),
}))

test('shows template names after load', async () => {
  render(<Config />)
  expect(await screen.findByRole('button', { name: 'general_car_info' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'waitlist' })).toBeInTheDocument()
})

test('clicking template shows subject and body in editor', async () => {
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: 'general_car_info' }))
  expect(screen.getByDisplayValue('Hello!')).toBeInTheDocument()
  expect(screen.getByDisplayValue('<p>Hi there</p>')).toBeInTheDocument()
})

test('saving template calls updateTemplate and shows Saved feedback', async () => {
  const { updateTemplate } = await import('../api/client')
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: 'general_car_info' }))
  const subjectInput = screen.getByDisplayValue('Hello!')
  await userEvent.clear(subjectInput)
  await userEvent.type(subjectInput, 'New Subject')
  await userEvent.click(screen.getByRole('button', { name: /save template/i }))
  expect(updateTemplate).toHaveBeenCalledWith(
    'general_car_info',
    expect.objectContaining({ subject: 'New Subject' })
  )
  expect(await screen.findByText('Saved.')).toBeInTheDocument()
})

test('decision tree YAML textarea is empty when no tree saved', async () => {
  render(<Config />)
  const textarea = await screen.findByRole('textbox', { name: /decision tree yaml/i })
  expect(textarea).toHaveValue('')
})

test('clicking Save decision tree calls updateDecisionTree', async () => {
  const { updateDecisionTree } = await import('../api/client')
  render(<Config />)
  const textarea = await screen.findByRole('textbox', { name: /decision tree yaml/i })
  await userEvent.type(textarea, 'template: general_car_info')
  await userEvent.click(screen.getByRole('button', { name: /save decision tree/i }))
  expect(updateDecisionTree).toHaveBeenCalled()
  expect(await screen.findByText('Saved.')).toBeInTheDocument()
})

test('clicking Test calls testDecisionTree and shows results table', async () => {
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: /test/i }))
  expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
  expect(screen.getAllByText('general_car_info').length).toBeGreaterThan(0)
})

test('invalid YAML shows parse error on decision tree save', async () => {
  render(<Config />)
  const textarea = await screen.findByRole('textbox', { name: /decision tree yaml/i })
  fireEvent.change(textarea, { target: { value: ': missing_key' } })
  await userEvent.click(screen.getByRole('button', { name: /save decision tree/i }))
  expect(await screen.findByText(/YAMLException/)).toBeInTheDocument()
})

test('API failure on save template shows error message', async () => {
  const { updateTemplate } = await import('../api/client')
  vi.mocked(updateTemplate).mockRejectedValueOnce(new Error('500 Internal Server Error'))
  render(<Config />)
  await screen.findByRole('button', { name: 'general_car_info' })
  await userEvent.click(screen.getByRole('button', { name: 'general_car_info' }))
  await userEvent.click(screen.getByRole('button', { name: /save template/i }))
  expect(await screen.findByText(/500 Internal Server Error/i)).toBeInTheDocument()
})
