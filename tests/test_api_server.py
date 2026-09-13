"""
Automated Unit Tests for QuantFlow API Server
Tests endpoints: /api/signals, /api/health, /api/backtest-data, /api/backups, and SPA static routing.
"""

import os
import sys
import json
import unittest
import threading
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.server import QuantFlowRequestHandler
from http.server import ThreadingHTTPServer

TEST_PORT = 8999

class TestAPIServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Starts a test HTTP server on TEST_PORT in a daemon thread."""
        server_address = ("127.0.0.1", TEST_PORT)
        cls.httpd = ThreadingHTTPServer(server_address, QuantFlowRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        """Shuts down the test HTTP server."""
        if hasattr(cls, 'httpd') and cls.httpd:
            cls.httpd.shutdown()
            cls.httpd.server_close()

    def _get(self, path: str):
        url = f"http://127.0.0.1:{TEST_PORT}{path}"
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=5) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
            return status, content_type, data

    def _post(self, path: str, payload: dict, timeout: int = 45):
        url = f"http://127.0.0.1:{TEST_PORT}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        with urlopen(req, timeout=timeout) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
            return status, content_type, data

    def test_get_signals_endpoint(self):
        """Verify /api/signals returns valid market regime and signals structure."""
        status, ct, body = self._get("/api/signals")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ct)
        payload = json.loads(body.decode("utf-8"))

        self.assertIn("market_regime", payload)
        self.assertIn("breadth_pct", payload["market_regime"])
        self.assertIn("gate_open", payload["market_regime"])
        self.assertIn("all_signals_unified", payload)
        self.assertIn("portfolio_summary", payload)
        self.assertIn("active_positions", payload)

    def test_get_health_endpoint(self):
        """Verify /api/health returns database status, constituents, holidays, and backups."""
        status, ct, body = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ct)
        payload = json.loads(body.decode("utf-8"))

        self.assertIn(payload["status"], ["HEALTHY", "DEGRADED"])
        self.assertIn("database", payload)
        self.assertTrue(payload["database"]["integrity_ok"])
        self.assertIn("universe", payload)
        self.assertEqual(payload["universe"]["total_constituents"], 750)
        self.assertIn("nse_holidays_2026", payload)
        self.assertGreater(len(payload["nse_holidays_2026"]), 10)
        self.assertIn("backups", payload)

    def test_get_backtest_data_endpoint(self):
        """Verify /api/backtest-data returns KPIs, equity curve, and trade history."""
        status, ct, body = self._get("/api/backtest-data")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ct)
        payload = json.loads(body.decode("utf-8"))

        self.assertIn("kpis", payload)
        self.assertIn("equity_curve", payload)
        self.assertIn("trades", payload)
        self.assertIsInstance(payload["trades"], list)

    def test_get_backups_endpoint(self):
        """Verify /api/backups returns snapshot list."""
        status, ct, body = self._get("/api/backups")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ct)
        payload = json.loads(body.decode("utf-8"))

        self.assertIn("snapshots", payload)
        self.assertIn("total", payload)

    def test_post_refresh_screener(self):
        """Verify /api/refresh with screener mode executes successfully."""
        from unittest.mock import patch
        with patch("src.api.server.run_all_screeners", return_value={"status": "mocked", "total_triggers": 2}):
            status, ct, body = self._post("/api/refresh", {"mode": "screener"})
            self.assertEqual(status, 200)
            payload = json.loads(body.decode("utf-8"))
            self.assertTrue(payload.get("success"))
            self.assertEqual(payload.get("mode"), "screener")

    def test_spa_fallback(self):
        """Verify root path / returns HTML."""
        status, ct, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ct)
        self.assertGreater(len(body), 50)

    def test_pwa_manifest_and_sw(self):
        """Verify PWA manifest.webmanifest and sw.js are served correctly."""
        status_m, ct_m, body_m = self._get("/manifest.webmanifest")
        self.assertEqual(status_m, 200)
        self.assertIn("manifest", ct_m)
        manifest = json.loads(body_m.decode("utf-8"))
        self.assertEqual(manifest.get("name"), "QuantFlow Trading Intelligence")

        status_sw, ct_sw, body_sw = self._get("/sw.js")
        self.assertEqual(status_sw, 200)
        self.assertIn("javascript", ct_sw)
        self.assertGreater(len(body_sw), 100)

if __name__ == "__main__":
    unittest.main()
