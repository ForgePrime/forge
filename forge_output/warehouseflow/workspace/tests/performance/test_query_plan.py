"""
Performance tests for T-006.

AC-0: The query used by StockService for a specific warehouse must use
      idx_stock_warehouse_product (Index Scan, not Seq Scan) on stock_levels.

AC-1: GET /api/products with 2000 products × 3 warehouses must respond
      in < 500 ms for a single synchronous request (measured by pytest-benchmark).
"""
from sqlalchemy import text


def _collect_plan_nodes(node: dict) -> list[dict]:
    """Recursively flatten all nodes from a PostgreSQL EXPLAIN JSON plan tree."""
    result = [node]
    for child in node.get("Plans", []):
        result.extend(_collect_plan_nodes(child))
    return result


def test_stock_query_uses_index_scan(db_conn, perf_setup):
    """
    EXPLAIN (ANALYZE, FORMAT JSON) on the exact StockService query for a known
    warehouse_id must show idx_stock_warehouse_product on stock_levels, not Seq Scan.

    SET LOCAL enable_seqscan = OFF forces the planner to use an index if one exists;
    if the migration has not run, the assertion on Index Name will fail explicitly.
    """
    warehouse_id = perf_setup["warehouse_ids"][0]

    db_conn.execute(text("SET LOCAL enable_seqscan = OFF"))

    plan_json = db_conn.execute(
        text("""
            EXPLAIN (ANALYZE, FORMAT JSON)
            SELECT
                p.id,
                p.sku,
                p.name,
                p.unit,
                w.id  AS warehouse_id,
                w.name AS warehouse_name,
                COALESCE(sl.physical_qty, 0),
                COALESCE(sl.reserved_qty, 0),
                COALESCE(sl.physical_qty, 0) - COALESCE(sl.reserved_qty, 0),
                (COALESCE(sl.physical_qty, 0) - COALESCE(sl.reserved_qty, 0))
                    < COALESCE(sl.min_alarm_qty, 0)
            FROM products p
            CROSS JOIN (SELECT id, name FROM warehouses WHERE id = :wid) w
            LEFT JOIN stock_levels sl
                   ON sl.product_id = p.id AND sl.warehouse_id = w.id
            ORDER BY p.id
            LIMIT 50 OFFSET 0
        """),
        {"wid": warehouse_id},
    ).scalar_one()

    all_nodes = _collect_plan_nodes(plan_json[0]["Plan"])
    sl_nodes = [n for n in all_nodes if n.get("Relation Name") == "stock_levels"]

    assert sl_nodes, (
        "EXPLAIN plan contains no nodes for stock_levels — "
        "table may be missing or query shape changed"
    )

    index_nodes = [
        n for n in sl_nodes if n.get("Index Name") == "idx_stock_warehouse_product"
    ]
    assert index_nodes, (
        f"idx_stock_warehouse_product is not used on stock_levels. "
        f"Actual stock_levels nodes: "
        f"{[(n.get('Node Type'), n.get('Index Name')) for n in sl_nodes]}"
    )


def test_stock_query_without_warehouse_filter_does_not_use_compound_index(db_conn, perf_setup):
    """
    Edge case: a query on stock_levels filtered only by product_id (NOT warehouse_id)
    must NOT use idx_stock_warehouse_product, because warehouse_id is the leading column
    of the compound index. Without the leading column, PostgreSQL cannot use the index
    efficiently via an index scan on that predicate.

    This validates that the index is correctly designed for warehouse-first queries and
    does not create false positives in the AC-0 test methodology.
    """
    product_id = perf_setup["product_ids"][0]

    plan_json = db_conn.execute(
        text("""
            EXPLAIN (FORMAT JSON)
            SELECT * FROM stock_levels WHERE product_id = :pid
        """),
        {"pid": product_id},
    ).scalar_one()

    all_nodes = _collect_plan_nodes(plan_json[0]["Plan"])
    sl_nodes = [n for n in all_nodes if n.get("Relation Name") == "stock_levels"]

    compound_index_nodes = [
        n for n in sl_nodes if n.get("Index Name") == "idx_stock_warehouse_product"
    ]
    assert not compound_index_nodes, (
        f"idx_stock_warehouse_product should NOT be used for a product_id-only filter "
        f"(warehouse_id is the leading column). "
        f"Actual stock_levels nodes: "
        f"{[(n.get('Node Type'), n.get('Index Name')) for n in sl_nodes]}"
    )


def test_product_list_single_request_under_500ms(perf_client, perf_setup, benchmark):
    """
    A single GET /api/products with 2000 products × 3 warehouses in the DB must
    complete in < 500 ms. Measured with pytest-benchmark (pedantic, 1 round).

    benchmark.pedantic captures timing for the report; time.perf_counter() provides
    the explicit assertion value because benchmark.stats dict layout changed in 4.x.
    """
    import time

    def _call():
        return perf_client.get("/api/products", params={"per_page": 50, "page": 1})

    t0 = time.perf_counter()
    response = benchmark.pedantic(_call, rounds=1, iterations=1)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json()
    assert data["total"] >= 2000, (
        f"Expected total >= 2000 products, got {data['total']}"
    )
    assert elapsed_ms < 500, (
        f"GET /api/products took {elapsed_ms:.1f} ms — expected < 500 ms"
    )
