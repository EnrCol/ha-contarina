"""Constants for the unofficial Contarina SOL integration."""
from datetime import timedelta

DOMAIN = "contarina"
API_BASE = "https://solapi.servizicontarina.it"
CONF_TOKEN = "access_token"
CONF_ACCOUNT = "account_id"
CONF_CONTRACTS = "contracts"
CONF_HORIZON = "calendar_horizon_days"
CONF_POLL_HOURS = "poll_interval_hours"
CONF_BILL_HOURS = "billing_interval_hours"
CONF_CONDOS = "include_condominium"
CONF_NOTIFY = "notify_service"
EVENT_SESSION_EXPIRED = "contarina_session_expired"

DEFAULT_HORIZON = 60
DEFAULT_POLL_HOURS = 6
DEFAULT_BILL_HOURS = 12
# SOL JWT lifetime is 3300 s and an expired JWT cannot be refreshed (401).
# Keep-alive every 10 min, unconditional unless the token is <5 min old:
# remaining validity never drops below ~45 min while HA is online.
TOKEN_REFRESH_INTERVAL = timedelta(minutes=10)
KEEPALIVE_SKIP_IF_FRESHER_SECONDS = 3300 - 5 * 60
# Data calls refresh on demand only when less than this is left.
TOKEN_REFRESH_MARGIN_SECONDS = 30 * 60
MAX_PAGES = 25
REQUEST_TIMEOUT_SECONDS = 30

# Material names are returned by the authenticated SOL endpoint.
FALLBACK_MATERIALS = {"S": "Secco", "E": "Vegetale", "U": "Umido", "V": "VPL", "C": "Carta"}
