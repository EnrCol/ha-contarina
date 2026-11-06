"""Reconnect pairing: one-time state, body validation and static pages (no Home Assistant)."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "contarina"
PACKAGE = "_isolated_contarina"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package
name = f"{PACKAGE}.pairing"
if name not in sys.modules:
    spec = importlib.util.spec_from_file_location(name, ROOT / "pairing.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
pairing = sys.modules[name]

FLOW = "0123456789abcdef0123456789abcdef"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjF9.c2ln"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class PendingStoreTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.store = pairing.PendingStore(clock=self.clock)

    def test_state_is_random_and_long(self):
        a = self.store.create(FLOW, "e1")
        b = self.store.create(FLOW, "e1")
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(b), 40)

    def test_single_use(self):
        state = self.store.create(FLOW, "e1")
        self.assertTrue(self.store.is_valid(FLOW, state))
        self.assertEqual(self.store.consume(FLOW, state), "e1")
        self.assertIsNone(self.store.consume(FLOW, state))
        self.assertFalse(self.store.is_valid(FLOW, state))

    def test_expiry(self):
        state = self.store.create(FLOW, "e1")
        self.clock.t += pairing.PENDING_TTL_SECONDS + 1
        self.assertIsNone(self.store.consume(FLOW, state))

    def test_wrong_state_and_lockout(self):
        state = self.store.create(FLOW, "e1")
        wrong = "x" * 43
        for _ in range(pairing.MAX_BAD_ATTEMPTS):
            self.assertIsNone(self.store.consume(FLOW, wrong))
        self.assertIsNone(self.store.consume(FLOW, state))

    def test_other_flow_and_malformed_ids(self):
        state = self.store.create(FLOW, "e1")
        self.assertIsNone(self.store.consume("f" * 32, state))
        self.assertIsNone(self.store.consume("../etc", state))
        with self.assertRaises(ValueError):
            self.store.create("bad id!", "e1")

    def test_outcome_and_discard(self):
        state = self.store.create(FLOW, "e1")
        self.store.consume(FLOW, state)
        self.store.set_outcome(FLOW, "ok")
        self.assertEqual(self.store.pop_outcome(FLOW), "ok")
        self.assertIsNone(self.store.pop_outcome(FLOW))
        state = self.store.create(FLOW, "e1")
        self.store.discard(FLOW)
        self.assertFalse(self.store.is_valid(FLOW, state))


class BodyTest(unittest.TestCase):
    def body(self, **kw):
        data = {"flow_id": FLOW, "state": "s" * 43, "token": JWT}
        data.update(kw)
        return json.dumps(data).encode()

    def test_valid(self):
        self.assertEqual(pairing.parse_receive_body(self.body()), (FLOW, "s" * 43, JWT))

    def test_rejects(self):
        for raw in (b"", b"not json", b"[]", self.body(token="a.b"), self.body(token=1),
                    self.body(state="short"), self.body(flow_id="x/y"),
                    b"{" + b" " * pairing.MAX_BODY_BYTES + b"}"):
            self.assertIsNone(pairing.parse_receive_body(raw))


class OriginTest(unittest.TestCase):
    def test_same_origin_accepted(self):
        f = pairing.origin_allowed
        self.assertTrue(f("http://ha.local:8123", "http", "ha.local:8123"))
        self.assertTrue(f("https://ha.example.com", "https", "ha.example.com"))
        self.assertTrue(f("https://HA.Example.com", "https", "ha.example.com"))
        self.assertTrue(f("https://ha.example.com", "https", "ha.example.com:443"))  # default port
        self.assertTrue(f("http://192.168.1.10:8123", "http", "192.168.1.10:8123"))
        self.assertTrue(f("http://[fe80::1]:8123", "http", "[fe80::1]:8123"))

    def test_scheme_must_match(self):
        f = pairing.origin_allowed
        self.assertFalse(f("http://ha.example.com", "https", "ha.example.com"))
        self.assertFalse(f("https://ha.local:8123", "http", "ha.local:8123"))
        self.assertFalse(f("http://ha.example.com:443", "https", "ha.example.com"))

    def test_port_must_match(self):
        f = pairing.origin_allowed
        self.assertFalse(f("http://ha.local:8124", "http", "ha.local:8123"))
        self.assertFalse(f("http://ha.local", "http", "ha.local:8123"))
        self.assertFalse(f("https://ha.example.com:8443", "https", "ha.example.com"))

    def test_wrong_or_malformed(self):
        f = pairing.origin_allowed
        for origin in (None, "", "null", "https://evil.example", "https://ha.local.evil.example",
                       "https://ha.local:8123/x", "https://user@ha.local:8123", "ftp://ha.local:8123",
                       "https://ha.local:99999", "https://"):
            self.assertFalse(f(origin, "https", "ha.local:8123"), origin)
        self.assertFalse(f("https://ha.local", "https", ""))
        self.assertFalse(f("https://ha.local", "gopher", "ha.local"))


class PagesTest(unittest.TestCase):
    def test_bookmarklet_has_no_secret_and_fixed_targets(self):
        tpl = pairing.BOOKMARKLET_TEMPLATE
        self.assertIn("__HA_ORIGIN__", tpl)
        self.assertIn("sol.servizicontarina.it", tpl)
        self.assertIn(pairing.RECEIVE_PATH + "#", tpl)
        for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "state", "flow_id", "?"):
            self.assertNotIn(forbidden, tpl)

    def test_pages_do_not_embed_request_data(self):
        page = pairing.start_page(True)
        self.assertIn("history.replaceState", page)
        self.assertIn(pairing.STORAGE_KEY, page)
        self.assertNotIn("</script><script", page)
        self.assertIn("scaduto", pairing.start_page(False))
        receive = pairing.receive_page()
        self.assertIn("location.hash", receive)
        self.assertIn("credentials:'same-origin'", receive)
        self.assertIn("sessionStorage", receive)
        self.assertIn("sessionStorage", page)
        self.assertIn("removeItem", receive)

    def test_security_headers(self):
        h = pairing.SECURITY_HEADERS
        self.assertEqual(h["Referrer-Policy"], "no-referrer")
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"])
        self.assertEqual(h["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
