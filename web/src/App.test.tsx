import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'

test('renders sidebar nav links', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
  expect(screen.getByText('Inbox')).toBeInTheDocument()
})
