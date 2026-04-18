"""
Baseline load test for GET /projects.

Starts a minimal FastAPI server backed by forge's JSONFileStorage,
runs concurrent HTTP load with aiohttp, captures p50/p95/p99 and rps,
writes perf_baseline.json.

Note: Server omits forge-api auth and ContractValidationMiddleware;
latency understates the full stack by ~1-3ms but accurately measures
the JSON storage backend -- the component being optimised by caching.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

FORGE_ROOT = str(Path(__file__).parent.parent.parent)
OUTPUT_FILE = Path(__file__).parent / "perf_baseline.json"
SERVER_FILE = Path(__file__).parent / "_perf_server.py"
PORT = 18765
HEALTH_URL = "http://127.0.0.1:{}/health".format(PORT)
ENDPOINT = "http://127.0.0.1:{}/projects".format(PORT)

CONCURRENCY = 10
TOTAL_REQUESTS = 200
WARMUP_REQUESTS = 20


def write_server_file() -> None:
    forge_root_escaped = FORGE_ROOT.replace("\\", "/")
    data_dir = (Path(FORGE_ROOT) / "forge_output").as_posix()
    code = (
        "import sys\n"
        "sys.path.insert(0, '{forge_root}')\n"
        "import asyncio\n"
        "from fastapi import FastAPI\n"
        "from core.storage import JSONFileStorage\n"
        "\n"
        "app = FastAPI()\n"
        "storage = JSONFileStorage('{data_dir}')\n"
        "\n"
        "@app.get('/health')\n"
        "async def health():\n"
        "    return {{'ok': True}}\n"
        "\n"
        "@app.get('/projects')\n"
        "async def list_projects():\n"
        "    slugs = await asyncio.to_thread(storage.list_projects)\n"
        "    return {{'projects': slugs}}\n"
    ).format(forge_root=forge_root_escaped, data_dir=data_dir)
    SERVER_FILE.write_text(code)


async def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    connector = aiohttp.TCPConnector(limit=2)
    async with aiohttp.ClientSession(connector=connector) as session:
        while time.monotonic() < deadline:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=1)) as r:
                    if r.status < 500:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.2)
    return False


async def run_worker(session: aiohttp.ClientSession, n: int) -> list:
    latencies = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            async with session.get(ENDPOINT, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                await resp.read()
                latencies.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            print("  request error: {}".format(e), flush=True)
    return latencies


async def load_test() -> dict:
    connector = aiohttp.TCPConnector(limit=CONCURRENCY + 5)
    async with aiohttp.ClientSession(connector=connector) as session:
        print("  Warmup ({} req)...".format(WARMUP_REQUESTS), flush=True)
        warmup_tasks = [
            run_worker(session, max(1, WARMUP_REQUESTS // CONCURRENCY))
            for _ in range(CONCURRENCY)
        ]
        await asyncio.gather(*warmup_tasks)

        print("  Measurement ({} req, concurrency={})...".format(TOTAL_REQUESTS, CONCURRENCY), flush=True)
        per_worker = TOTAL_REQUESTS // CONCURRENCY
        t_start = time.perf_counter()
        tasks = [run_worker(session, per_worker) for _ in range(CONCURRENCY)]
        results = await asyncio.gather(*tasks)
        t_total = time.perf_counter() - t_start

    all_ms = sorted(lat for worker in results for lat in worker)
    if not all_ms:
        raise RuntimeError("No successful requests")

    def pct(data, p):
        idx = min(int(len(data) * p / 100), len(data) - 1)
        return round(data[idx], 2)

    return {
        "p50": pct(all_ms, 50),
        "p95": pct(all_ms, 95),
        "p99": pct(all_ms, 99),
        "rps": round(len(all_ms) / t_total, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_requests": len(all_ms),
        "concurrency": CONCURRENCY,
        "endpoint": "GET /projects",
        "server": "minimal FastAPI + JSONFileStorage (forge core)",
        "note": "Excludes auth/ContractValidationMiddleware; understates full stack by ~1-3ms",
    }


async def main():
    write_server_file()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "_perf_server:app",
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--log-level", "error",
    ]
    env = os.environ.copy()

    print("Starting test server...", flush=True)
    proc = subprocess.Popen(
        cmd,
        cwd=str(SERVER_FILE.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        ready = await wait_for_server(HEALTH_URL)
        if not ready:
            stderr_text = ""
            if proc.stderr:
                proc.stderr.read().decode(errors="replace")
            print("Server failed to start:\n{}".format(stderr_text), flush=True)
            proc.terminate()
            sys.exit(1)

        print("  Server ready.", flush=True)
        stats = await load_test()

        print("\nResults:", flush=True)
        for k in ("p50", "p95", "p99", "rps", "total_requests"):
            print("  {:<20} {}".format(k, stats[k]), flush=True)

        OUTPUT_FILE.write_text(json.dumps(stats, indent=2))
        print("\nWritten: {}".format(OUTPUT_FILE), flush=True)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        if SERVER_FILE.exists():
            SERVER_FILE.unlink()


if __name__ == "__main__":
    asyncio.run(main())
