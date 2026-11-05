"""Read-only API contract tests using synthetic HTTP responses (no network)."""
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
for module_name in ("const", "models", "api"):
    name = f"{PACKAGE}.{module_name}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / (module_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
api = sys.modules[f"{PACKAGE}.api"]

class MockResponse:
    def __init__(self, payload, status=200, content_type="application/json"):
        self.status = status
        self.content_type = content_type
        self._payload = payload
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return None
    async def text(self):
        return self._payload if isinstance(self._payload, str) else json.dumps(self._payload)

class MockSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)
    def post(self, *args, **kwargs):
        raise AssertionError("POST must not be used")

class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_contracts_and_pagination(self):
        session = MockSession([
            MockResponse({"contracts": [{"reference_code": "100"}], "page": 1, "totalPages": 2}),
            MockResponse({"contracts": [{"reference_code": "200"}], "page": 2, "totalPages": 2}),
        ])
        client = api.ContarinaApi(session)
        data = await client.get_contracts("a.jwt.token")
        self.assertEqual([d["reference_code"] for d in data], ["100", "200"])
        self.assertTrue(all("Authorization" in k[1]["headers"] for k in session.calls))
        self.assertTrue(all(k[1]["params"]["active"] == "all" for k in session.calls))
        self.assertEqual(session.calls[0][1]["params"], {"active": "all"})
        self.assertEqual(len(session.calls), 2)

    async def test_401_causes_auth_error(self):
        client = api.ContarinaApi(MockSession([MockResponse({}, status=401)]))
        with self.assertRaises(api.ContarinaAuthError):
            await client.get("/api/contracts", "jwt")

    async def test_200_application_error_detected(self):
        client = api.ContarinaApi(MockSession([MockResponse({"Code": 400, "Message": "invalid"})]))
        with self.assertRaises(api.ContarinaConnectionError):
            await client.get("/api/users/ref/emptyings/bin", "jwt")

    async def test_json_bool_with_html_content_type(self):
        client = api.ContarinaApi(MockSession([MockResponse("false", content_type="text/html")]))
        self.assertFalse(await client.check_balance("100", "jwt"))

    async def test_untrusted_path_identifier_rejected(self):
        client = api.ContarinaApi(MockSession([]))
        with self.assertRaises(api.ContarinaConnectionError):
            await client.contract_detail("../../secret", "jwt")

if __name__ == "__main__":
    unittest.main()
