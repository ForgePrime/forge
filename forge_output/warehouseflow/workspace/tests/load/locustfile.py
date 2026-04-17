"""
Locust load test for GET /api/products.

JWT token is injected via the LOAD_TEST_JWT_TOKEN environment variable,
which test_load_kpi.py sets before spawning this file as a subprocess.
"""
import os

from locust import HttpUser, between, task


class StockUser(HttpUser):
    # Brief think-time between requests keeps the 30-user concurrency realistic.
    wait_time = between(0.05, 0.15)

    def on_start(self):
        token = os.environ.get("LOAD_TEST_JWT_TOKEN", "")
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task
    def list_products(self):
        self.client.get("/api/products?page=1&per_page=50", name="/api/products")
