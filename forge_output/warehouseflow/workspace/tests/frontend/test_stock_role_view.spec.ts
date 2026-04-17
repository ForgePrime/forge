import React from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ProductStockPage } from '../../src/pages/ProductStockPage'
import { apiClient } from '../../src/api/client'
import { useAuthStore } from '../../src/stores/authStore'

vi.mock('../../src/api/client', () => ({
  apiClient: { get: vi.fn() },
}))

const MOCK_MULTI_WAREHOUSE_PAGE = {
  items: [
    {
      product_id: 1,
      sku: 'SKU-001',
      name: 'Product A',
      unit: 'szt',
      warehouses: [
        {
          warehouse_id: 1,
          warehouse_name: 'Warszawa',
          physical_qty: 100,
          reserved_qty: 20,
          available_qty: 80,
          is_below_alarm: false,
        },
        {
          warehouse_id: 2,
          warehouse_name: 'Poznań',
          physical_qty: 50,
          reserved_qty: 10,
          available_qty: 40,
          is_below_alarm: false,
        },
        {
          warehouse_id: 3,
          warehouse_name: 'Wrocław',
          physical_qty: 30,
          reserved_qty: 5,
          available_qty: 25,
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

function renderStockPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(MemoryRouter, null, React.createElement(ProductStockPage))
    )
  )
}

beforeEach(() => {
  window.localStorage.clear()
  vi.clearAllMocks()
})

it('test_operator_sees_only_own_warehouse_columns', async () => {
  useAuthStore.setState({
    token: 'test-token',
    user: { id: 1, email: 'op@test.pl', role: 'operator', warehouse_id: 1 },
    isAuthenticated: true,
  })
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: MOCK_MULTI_WAREHOUSE_PAGE })

  const { container } = renderStockPage()

  await waitFor(() => {
    expect(screen.getByText('Stan fizyczny')).toBeInTheDocument()
  })

  const thead = container.querySelector('thead')!
  expect(within(thead).getByText('Stan fizyczny')).toBeInTheDocument()
  expect(within(thead).getByText('Zarezerwowane')).toBeInTheDocument()
  expect(within(thead).getByText('Dostępne')).toBeInTheDocument()
  expect(within(thead).queryByText(/Poznań/)).toBeNull()
  expect(within(thead).queryByText(/Wrocław/)).toBeNull()
})

it('test_director_sees_headers_for_all_warehouses', async () => {
  useAuthStore.setState({
    token: 'test-token',
    user: { id: 2, email: 'dir@test.pl', role: 'director', warehouse_id: null },
    isAuthenticated: true,
  })
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: MOCK_MULTI_WAREHOUSE_PAGE })

  const { container } = renderStockPage()

  await waitFor(() => {
    expect(screen.getByText('Warszawa')).toBeInTheDocument()
  })

  const thead = container.querySelector('thead')!
  expect(within(thead).getByText('Warszawa')).toBeInTheDocument()
  expect(within(thead).getByText('Poznań')).toBeInTheDocument()
  expect(within(thead).getByText('Wrocław')).toBeInTheDocument()
})

it('test_operator_dom_contains_no_foreign_warehouse_data', async () => {
  useAuthStore.setState({
    token: 'test-token',
    user: { id: 1, email: 'op@test.pl', role: 'operator', warehouse_id: 1 },
    isAuthenticated: true,
  })
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: MOCK_MULTI_WAREHOUSE_PAGE })

  const { container } = renderStockPage()

  await waitFor(() => {
    expect(screen.getByText('SKU-001')).toBeInTheDocument()
  })

  const foreignCells = container.querySelectorAll(
    '[data-warehouse-id]:not([data-warehouse-id="1"])'
  )
  expect(foreignCells).toHaveLength(0)
})
