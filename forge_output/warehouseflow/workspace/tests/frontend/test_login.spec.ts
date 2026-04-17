import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach } from 'vitest'
import { useAuthStore } from '../../src/stores/authStore'
import { apiClient } from '../../src/api/client'
import { renderApp } from './helpers'

vi.mock('../../src/api/client', () => ({
  apiClient: { post: vi.fn(), get: vi.fn() },
}))

const MOCK_USER = {
  id: 1,
  email: 'operator@warehouse.pl',
  role: 'operator' as const,
  warehouse_id: 2,
}

beforeEach(() => {
  window.localStorage.clear()
  useAuthStore.setState({ token: null, user: null, isAuthenticated: false })
  vi.clearAllMocks()
  vi.mocked(apiClient.get).mockResolvedValue({
    data: { items: [], total: 0, page: 1, per_page: 50, pages: 0 },
  })
})

it('test_successful_login_sets_store_and_redirects', async () => {
  vi.mocked(apiClient.post).mockResolvedValueOnce({
    data: { token: 'jwt-abc123', user: MOCK_USER },
  })

  renderApp('/login')

  await userEvent.type(screen.getByLabelText(/email/i), 'operator@warehouse.pl')
  await userEvent.type(screen.getByLabelText(/hasło/i), 'correctpass')
  await userEvent.click(screen.getByRole('button', { name: /zaloguj/i }))

  await waitFor(() => {
    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
    expect(state.user?.role).toBe('operator')
    expect(state.user?.warehouse_id).toBe(2)
    expect(state.token).toBe('jwt-abc123')
  })

  await waitFor(() => {
    expect(screen.queryByRole('button', { name: /zaloguj/i })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /stany magazynowe/i })).toBeInTheDocument()
  })
})

it('test_wrong_password_shows_error_message', async () => {
  vi.mocked(apiClient.post).mockRejectedValueOnce({
    response: { status: 401, data: { detail: 'Invalid credentials' } },
  })

  renderApp('/login')

  await userEvent.type(screen.getByLabelText(/email/i), 'operator@warehouse.pl')
  await userEvent.type(screen.getByLabelText(/hasło/i), 'wrongpassword')
  await userEvent.click(screen.getByRole('button', { name: /zaloguj/i }))

  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent('Nieprawidłowy email lub hasło.')
  })

  const state = useAuthStore.getState()
  expect(state.isAuthenticated).toBe(false)
  expect(state.token).toBeNull()
})

it('test_unauthenticated_direct_access_redirects_to_login', () => {
  renderApp('/products')

  expect(screen.queryByRole('heading', { name: /stany magazynowe/i })).not.toBeInTheDocument()
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
})
