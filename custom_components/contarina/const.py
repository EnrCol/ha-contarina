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

DEFAULT_HORIZON = 60
DEFAULT_POLL_HOURS = 6
DEFAULT_BILL_HOURS = 12
TOKEN_REFRESH_INTERVAL = timedelta(minutes=15)
TOKEN_REFRESH_MARGIN_SECONDS = 30 * 60
MAX_PAGES = 25
REQUEST_TIMEOUT_SECONDS = 30

# Material names are returned by the authenticated SOL endpoint.
FALLBACK_MATERIALS = {"S": "Secco", "E": "Vegetale", "U": "Umido", "V": "VPL", "C": "Carta"}
