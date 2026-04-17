import React, { useRef, useState, useCallback, useEffect } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useAuthStore } from '../stores/authStore'

interface WarehouseStock {
  warehouse_id: number
  warehouse_name: string
  physical_qty: number
  reserved_qty: number
  available_qty: number
  is_below_alarm: boolean
}

interface ProductStock {
  product_id: number
  sku: string
  name: string
  unit: string
  warehouses: WarehouseStock[]
}

interface StockPage {
  items: ProductStock[]
  total: number
  page: number
  per_page: number
  pages: number
}

interface ProductRow {
  rowKey: string
  product_id: number
  sku: string
  name: string
  unit: string
  warehouses: WarehouseStock[]
}

interface WarehouseInfo {
  warehouse_id: number
  warehouse_name: string
}

function toProductRows(pages: StockPage[]): ProductRow[] {
  return pages.flatMap((page) =>
    page.items.map((product) => ({
      rowKey: String(product.product_id),
      product_id: product.product_id,
      sku: product.sku,
      name: product.name,
      unit: product.unit,
      warehouses: product.warehouses,
    }))
  )
}

function collectWarehouses(pages: StockPage[]): WarehouseInfo[] {
  const map = new Map<number, string>()
  for (const page of pages) {
    for (const product of page.items) {
      for (const w of product.warehouses) {
        if (!map.has(w.warehouse_id)) {
          map.set(w.warehouse_id, w.warehouse_name)
        }
      }
    }
  }
  return Array.from(map.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([warehouse_id, warehouse_name]) => ({ warehouse_id, warehouse_name }))
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debouncedValue
}

const VIRTUAL_THRESHOLD = 500
const ROW_ESTIMATE_HEIGHT = 48

export const ProductStockPage: React.FC = () => {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 300)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  const isOperator = user?.role === 'operator'

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    refetch,
  } = useInfiniteQuery<StockPage, Error>({
    queryKey: ['products', debouncedSearch],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({
        page: String(pageParam as number),
        per_page: '50',
      })
      if (debouncedSearch) params.set('search', debouncedSearch)
      const response = await apiClient.get<StockPage>(`/products?${params}`)
      return response.data
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined,
  })

  const rows: ProductRow[] = data ? toProductRows(data.pages) : []
  const allWarehouses: WarehouseInfo[] = data ? collectWarehouses(data.pages) : []
  const total = data?.pages[0]?.total ?? 0
  const useVirtual = rows.length > VIRTUAL_THRESHOLD

  const columnCount = isOperator ? 5 : 2 + allWarehouses.length * 3

  const virtualizer = useVirtualizer({
    count: useVirtual ? rows.length : 0,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => ROW_ESTIMATE_HEIGHT,
    overscan: 10,
  })

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current
    if (!el || isFetchingNextPage || !hasNextPage) return
    const { scrollTop, scrollHeight, clientHeight } = el
    if (scrollHeight - scrollTop - clientHeight < 200) {
      fetchNextPage()
    }
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) return
    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const getRowAlarm = (row: ProductRow): boolean => {
    if (isOperator) {
      return (
        row.warehouses.find((w) => w.warehouse_id === user?.warehouse_id)
          ?.is_below_alarm ?? false
      )
    }
    return row.warehouses.some((w) => w.is_below_alarm)
  }

  return (
    <div>
      <header>
        <span>
          {user?.email} ({user?.role})
        </span>
        <button type="button" onClick={handleLogout}>
          Wyloguj
        </button>
      </header>
      <main>
        <h1>Stany magazynowe</h1>
        <input
          type="search"
          placeholder="Szukaj produktu..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Szukaj"
        />

        {isLoading && (
          <div role="status" aria-label="Ładowanie">
            Ładowanie...
          </div>
        )}

        {isError && (
          <div role="alert">
            <p>Wystąpił błąd podczas ładowania danych.</p>
            <button type="button" onClick={() => refetch()}>
              Odśwież
            </button>
          </div>
        )}

        {!isLoading && !isError && total === 0 && <p>Brak produktów</p>}

        {!isLoading && !isError && total > 0 && (
          <div
            ref={scrollContainerRef}
            style={{ height: '600px', overflow: 'auto' }}
            data-testid="stock-scroll-container"
          >
            {useVirtual ? (
              <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
                {virtualizer.getVirtualItems().map((virtualItem) => {
                  const row = rows[virtualItem.index]
                  const isAlarm = getRowAlarm(row)
                  const warehouseMap = new Map(row.warehouses.map((w) => [w.warehouse_id, w]))
                  const ownStock = isOperator
                    ? warehouseMap.get(user?.warehouse_id ?? -1)
                    : undefined

                  return (
                    <div
                      key={row.rowKey}
                      data-index={virtualItem.index}
                      ref={virtualizer.measureElement}
                      className={isAlarm ? 'alarm-row' : undefined}
                      style={{
                        position: 'absolute',
                        top: 0,
                        transform: `translateY(${virtualItem.start}px)`,
                        width: '100%',
                        display: 'grid',
                        gridTemplateColumns: `repeat(${columnCount}, 1fr)`,
                        backgroundColor: isAlarm ? '#FEF2F2' : undefined,
                        height: ROW_ESTIMATE_HEIGHT,
                        alignItems: 'center',
                      }}
                    >
                      <span>{row.sku}</span>
                      <span>{row.name}</span>
                      {isOperator ? (
                        <>
                          <span data-warehouse-id={user?.warehouse_id}>
                            {ownStock?.physical_qty ?? 0}
                          </span>
                          <span data-warehouse-id={user?.warehouse_id}>
                            {ownStock?.reserved_qty ?? 0}
                          </span>
                          <span data-warehouse-id={user?.warehouse_id}>
                            {ownStock?.available_qty ?? 0}
                          </span>
                        </>
                      ) : (
                        allWarehouses.map((wh) => {
                          const stock = warehouseMap.get(wh.warehouse_id)
                          return (
                            <React.Fragment key={wh.warehouse_id}>
                              <span data-warehouse-id={wh.warehouse_id}>
                                {stock?.physical_qty ?? 0}
                              </span>
                              <span data-warehouse-id={wh.warehouse_id}>
                                {stock?.reserved_qty ?? 0}
                              </span>
                              <span data-warehouse-id={wh.warehouse_id}>
                                {stock?.available_qty ?? 0}
                              </span>
                            </React.Fragment>
                          )
                        })
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <table>
                <thead>
                  {isOperator ? (
                    <tr>
                      <th>SKU</th>
                      <th>Nazwa</th>
                      <th>Stan fizyczny</th>
                      <th>Zarezerwowane</th>
                      <th>Dostępne</th>
                    </tr>
                  ) : (
                    <>
                      <tr>
                        <th rowSpan={2}>SKU</th>
                        <th rowSpan={2}>Nazwa</th>
                        {allWarehouses.map((wh) => (
                          <th key={wh.warehouse_id} colSpan={3}>
                            {wh.warehouse_name}
                          </th>
                        ))}
                      </tr>
                      <tr>
                        {allWarehouses.map((wh) => (
                          <React.Fragment key={wh.warehouse_id}>
                            <th>{`${wh.warehouse_name} — Stan fizyczny`}</th>
                            <th>{`${wh.warehouse_name} — Zarezerwowane`}</th>
                            <th>{`${wh.warehouse_name} — Dostępne`}</th>
                          </React.Fragment>
                        ))}
                      </tr>
                    </>
                  )}
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const isAlarm = getRowAlarm(row)
                    const warehouseMap = new Map(
                      row.warehouses.map((w) => [w.warehouse_id, w])
                    )
                    const ownStock = isOperator
                      ? warehouseMap.get(user?.warehouse_id ?? -1)
                      : undefined

                    return (
                      <tr
                        key={row.rowKey}
                        className={isAlarm ? 'alarm-row' : undefined}
                        style={isAlarm ? { backgroundColor: '#FEF2F2' } : undefined}
                      >
                        <td>{row.sku}</td>
                        <td>{row.name}</td>
                        {isOperator ? (
                          <>
                            <td data-warehouse-id={user?.warehouse_id}>
                              {ownStock?.physical_qty ?? 0}
                            </td>
                            <td data-warehouse-id={user?.warehouse_id}>
                              {ownStock?.reserved_qty ?? 0}
                            </td>
                            <td data-warehouse-id={user?.warehouse_id}>
                              {ownStock?.available_qty ?? 0}
                            </td>
                          </>
                        ) : (
                          allWarehouses.map((wh) => {
                            const stock = warehouseMap.get(wh.warehouse_id)
                            return (
                              <React.Fragment key={wh.warehouse_id}>
                                <td data-warehouse-id={wh.warehouse_id}>
                                  {stock?.physical_qty ?? 0}
                                </td>
                                <td data-warehouse-id={wh.warehouse_id}>
                                  {stock?.reserved_qty ?? 0}
                                </td>
                                <td data-warehouse-id={wh.warehouse_id}>
                                  {stock?.available_qty ?? 0}
                                </td>
                              </React.Fragment>
                            )
                          })
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}

            {isFetchingNextPage && (
              <div role="status" aria-label="Ładowanie kolejnej strony">
                Ładowanie kolejnej strony...
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
