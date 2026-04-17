import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ProductStockPage } from '../../src/pages/ProductStockPage'
import { apiClient } from '../../src/api/client'
import { useAuthStore } from '../../src/stores/authStore'

vi.mock('../../src/api/client', () => ({
  apiClient: { get: vi.fn() },
}))

const MOCK_USER = {
  id: 1,
  email: 'operator@warehouse.pl',
  role: 'operator' as const,
  warehouse_id: 1,
}

const MOCK_STOCK_PAGE = {
  items: [
    {
      product_id: 1,
      sku: 'SKU-001',
      name: 'Product A',
      unit: 'szt',
      warehouses: [
        {
          warehouse_id: 1,
          warehouse_name: 'Magazyn Główny',
          physical_qty: 100,
          reserved_qty: 20,
          available_qty: 80,
          is_below_alarm: true,
        },
        {
          warehouse_id: 2,
          warehouse_name: 'Magazyn Pomocniczy',
          physical_qty: 5,
          reserved_qty: 3,
          available_qty: 2,
          is_below_alarm: false,
        },
      ],
    },
  ],
  total: 1,
  page: 1,
  per_page: 50,
  pages: 1,
}

const EMPTY_STOCK_PAGE = {
  items: [],
  total: 0,
  page: 1,
  per_page: 50,
  pages: 0,
}

function renderStockPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(
        MemoryRouter,
        null,
        React.createElement(ProductStockPage)
      )
    )
  )
}

beforeEach(() => {
  window.localStorage.clear()
  useAuthStore.setState({ token: 'test-token', user: MOCK_USER, isAuthenticated: true })
  vi.clearAllMocks()
})

it('test_table_renders_stock_columns', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: MOCK_STOCK_PAGE })

  renderStockPage()

  await waitFor(() => {
    expect(screen.getByText('Stan fizyczny')).toBeInTheDocument()
    expect(screen.getByText('Zarezerwowane')).toBeInTheDocument()
    expect(screen.getByText('Dostępne')).toBeInTheDocument()
  })

  expect(screen.getByText('100')).toBeInTheDocument()
  expect(screen.getByText('20')).toBeInTheDocument()
  expect(screen.getByText('80')).toBeInTheDocument()
})

it('test_alarm_rows_have_alarm_row_class', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: MOCK_STOCK_PAGE })

  const { container } = renderStockPage()

  await waitFor(() => {
    expect(screen.getAllByText('SKU-001').length).toBeGreaterThan(0)
  })

  const alarmRows = container.querySelectorAll('.alarm-row')
  expect(alarmRows.length).toBe(1)
  expect(alarmRows[0]).toHaveTextContent('SKU-001')
})

it('test_empty_result_shows_empty_state_message', async () => {
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: EMPTY_STOCK_PAGE })

  const { container } = renderStockPage()

  await waitFor(() => {
    expect(screen.getByText('Brak produktów')).toBeInTheDocument()
  })

  expect(container.querySelector('table')).toBeNull()
})

it('test_api_500_shows_error_with_refresh_button', async () => {
  vi.mocked(apiClient.get).mockRejectedValueOnce({
    response: { status: 500, data: { detail: 'Internal Server Error' } },
  })

  renderStockPage()

  await waitFor(() => {
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /odśwież/i })).toBeInTheDocument()
  })
})
