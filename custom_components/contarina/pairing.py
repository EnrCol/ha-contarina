"""Browser reconnect pairing: one-time state store, bookmarklet and static pages.

Pure Python (no Home Assistant imports) so it can be unit-tested in isolation.

Security model (mirrors Home Assistant's own OAuth2 external-step callback):
- the reconnect is started by an authenticated HA user inside a config flow;
- the flow creates a random 256-bit state, bound to that flow, valid 10 minutes,
  consumed on first use and discarded after 5 wrong attempts;
- the state reaches only the browser of that HA user (external-step URL) and is
  kept in that browser's localStorage for the HA origin, never in the bookmarklet;
- the bookmarklet holds no secret: only the HA origin. It moves the SOL JWT to the
  HA receive page inside the URL fragment (never sent over the network);
- the receive page posts {flow_id, state, token} same-origin; the flow then validates
  the JWT with SOL and checks it belongs to the configured account.
"""
from __future__ import annotations

import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlsplit

PENDING_TTL_SECONDS = 600
MAX_BAD_ATTEMPTS = 5
MAX_BODY_BYTES = 8192

BASE_PATH = "/api/contarina/reconnect"
START_PATH = f"{BASE_PATH}/start"
RECEIVE_PATH = f"{BASE_PATH}/receive"
SOL_URL = "https://sol.servizicontarina.it/"
STORAGE_KEY = "contarina_reconnect"

FLOW_ID_RE = re.compile(r"[A-Za-z0-9]{16,64}")
STATE_RE = re.compile(r"[A-Za-z0-9_-]{40,64}")
JWT_RE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
}


@dataclass
class _Pending:
    state: str
    entry_id: str
    expires: float
    bad_attempts: int = 0
    outcome: str | None = None


@dataclass
class PendingStore:
    """In-memory, per-flow one-time states. Lost on restart (flows are too)."""

    clock: Callable[[], float] = time.monotonic
    _items: dict[str, _Pending] = field(default_factory=dict)

    def _purge(self) -> None:
        now = self.clock()
        for flow_id in [k for k, v in self._items.items() if v.expires <= now]:
            del self._items[flow_id]

    def create(self, flow_id: str, entry_id: str) -> str:
        if not FLOW_ID_RE.fullmatch(flow_id):
            raise ValueError("invalid flow id")
        self._purge()
        state = secrets.token_urlsafe(32)
        self._items[flow_id] = _Pending(state, entry_id, self.clock() + PENDING_TTL_SECONDS)
        return state

    def _match(self, flow_id: str, state: str) -> _Pending | None:
        self._purge()
        if not FLOW_ID_RE.fullmatch(flow_id or "") or not STATE_RE.fullmatch(state or ""):
            return None
        item = self._items.get(flow_id)
        if item is None:
            return None
        if not hmac.compare_digest(item.state, state):
            item.bad_attempts += 1
            if item.bad_attempts >= MAX_BAD_ATTEMPTS:
                del self._items[flow_id]
            return None
        return item

    def is_valid(self, flow_id: str, state: str) -> bool:
        """Check without consuming (start page)."""
        return self._match(flow_id, state) is not None

    def consume(self, flow_id: str, state: str) -> str | None:
        """Single use: returns entry_id and invalidates the state."""
        item = self._match(flow_id, state)
        if item is None or item.state == "":
            return None
        entry_id = item.entry_id
        item.state = ""  # consumed; entry kept only to carry the outcome
        return entry_id

    def set_outcome(self, flow_id: str, outcome: str) -> None:
        if flow_id in self._items:
            self._items[flow_id].outcome = outcome

    def pop_outcome(self, flow_id: str) -> str | None:
        item = self._items.pop(flow_id, None)
        return item.outcome if item else None

    def discard(self, flow_id: str) -> None:
        self._items.pop(flow_id, None)


_DEFAULT_PORTS = {"http": 80, "https": 443}


def _origin_tuple(scheme: str, netloc: str) -> tuple[str, str, int] | None:
    """(scheme, hostname, port) with default ports made explicit; None if malformed."""
    scheme = (scheme or "").lower()
    if scheme not in _DEFAULT_PORTS or not netloc or re.search(r"[/?#@\s]", netloc):
        return None
    try:
        parts = urlsplit(f"{scheme}://{netloc}")
        hostname, port = parts.hostname, parts.port
    except ValueError:
        return None
    if not hostname:
        return None
    return scheme, hostname.lower().rstrip("."), port if port is not None else _DEFAULT_PORTS[scheme]


def origin_allowed(origin: str | None, request_scheme: str, request_host: str) -> bool:
    """Strict same-origin check (scheme + host + port) for the receive POST.

    `request_scheme`/`request_host` must be the values Home Assistant already resolved for
    this request: HA's forwarded middleware applies X-Forwarded-Proto/Host only from
    configured trusted proxies (and rejects them otherwise), so forwarded headers are never
    read here. A missing or opaque ("null") Origin is refused: browsers always send Origin on
    a fetch POST. Defence in depth on top of the one-time state.
    """
    if not origin or origin == "null":
        return False
    m = re.fullmatch(r"(https?)://([^/?#@\s]+)", origin.strip(), flags=re.IGNORECASE)
    if not m:
        return False
    got = _origin_tuple(m.group(1), m.group(2))
    expected = _origin_tuple(request_scheme, request_host)
    return got is not None and got == expected


def parse_receive_body(raw: bytes) -> tuple[str, str, str] | None:
    """Validate the POST body shape; never echo its content."""
    if not raw or len(raw) > MAX_BODY_BYTES:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    flow_id, state, token = data.get("flow_id"), data.get("state"), data.get("token")
    if not all(isinstance(x, str) for x in (flow_id, state, token)):
        return None
    if not (FLOW_ID_RE.fullmatch(flow_id) and STATE_RE.fullmatch(state) and JWT_RE.fullmatch(token)):
        return None
    return flow_id, state, token


# Bookmarklet: runs on the authenticated SOL page. __HA_ORIGIN__ is replaced in the
# browser (start page) with JSON.stringify(location.origin). It holds no secret.
BOOKMARKLET_TEMPLATE = (
    "(function(){"
    "var ha=__HA_ORIGIN__;"
    "if(location.protocol!=='https:'||location.hostname!=='sol.servizicontarina.it')"
    "{alert('Apri prima https://sol.servizicontarina.it/ e accedi.');return;}"
    "var c=document.cookie.split(';').map(function(s){return s.trim();})"
    ".filter(function(s){return s.indexOf('accessToken=')===0;})[0];"
    "if(!c){alert('Accesso SOL non rilevato: esegui il login e riprova.');return;}"
    "var t;try{t=decodeURIComponent(c.slice(12));}catch(e){alert('Token SOL non leggibile.');return;}"
    "var p=t.split('.');"
    "if(p.length!==3||!p.every(function(x){return /^[A-Za-z0-9_-]+$/.test(x);}))"
    "{alert('Token SOL in formato inatteso.');return;}"
    "var exp;try{var b=p[1].replace(/-/g,'+').replace(/_/g,'/');"
    "while(b.length%4){b+='=';}exp=JSON.parse(atob(b)).exp;}"
    "catch(e){alert('Scadenza del token non leggibile.');return;}"
    "if(!(typeof exp==='number'&&exp*1000-Date.now()>120000))"
    "{alert('Sessione SOL scaduta: rifai il login.');return;}"
    f"location.href=ha+'{RECEIVE_PATH}#'+t;"
    "})();"
)

_PAGE_STYLE = (
    "body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;"
    "line-height:1.5;color:#222}a.bm{display:inline-block;padding:.5rem 1rem;border:2px dashed #1976d2;"
    "border-radius:8px;text-decoration:none;font-weight:600}a.go{display:inline-block;padding:.6rem 1.2rem;"
    "background:#1976d2;color:#fff;border-radius:8px;text-decoration:none}.err{color:#b00020}"
    ".ok{color:#2e7d32}code{background:#eee;padding:0 .2rem}"
)


def start_page(valid: bool) -> str:
    if not valid:
        return _page("Contarina SOL", "<p class='err'>Link di riconnessione scaduto o già usato. "
                     "Riavvia <b>Riconnetti</b> da Home Assistant.</p>", "")
    body = f"""
<h2>Riconnetti Contarina SOL</h2>
<ol>
<li><b>Solo la prima volta</b>: trascina questo pulsante nella barra dei preferiti
(non cliccarlo qui): <a class="bm" id="bm" href="#">Invia token a Home Assistant</a><br>
<small>Il preferito contiene solo l'indirizzo di questo Home Assistant, nessun segreto.
Va ricreato se apri Home Assistant da un indirizzo diverso.</small></li>
<li>Apri Contarina SOL e accedi (il browser può compilare le credenziali salvate).</li>
<li>Sulla pagina di SOL, clicca il preferito <b>Invia token a Home Assistant</b>.</li>
</ol>
<p><a class="go" href="{SOL_URL}" rel="noreferrer" target="_self">Apri Contarina SOL</a></p>
<p><small>Il collegamento vale 10 minuti, solo in questo browser e una sola volta.
Apri SOL da questo pulsante, nella stessa scheda.</small></p>
"""
    script = f"""
(function(){{
  var q=new URLSearchParams(location.search);
  var flow=q.get('flow_id'), state=q.get('state');
  history.replaceState(null,'',location.pathname);
  var rec={{flow_id:flow,state:state,ts:Date.now()}};
  try{{
    sessionStorage.setItem({json.dumps(STORAGE_KEY)},JSON.stringify(rec));
    var m={{}};try{{m=JSON.parse(localStorage.getItem({json.dumps(STORAGE_KEY)})||'{{}}')||{{}};}}catch(e){{m={{}};}}
    for(var k in m){{if(!m[k]||Date.now()-m[k].ts>{PENDING_TTL_SECONDS * 1000}){{delete m[k];}}}}
    m[flow]=rec;localStorage.setItem({json.dumps(STORAGE_KEY)},JSON.stringify(m));
  }}catch(e){{document.body.insertAdjacentHTML('beforeend','<p class="err">Il browser blocca la memoria locale: usa il copia-incolla.</p>');}}
  var tpl={json.dumps(BOOKMARKLET_TEMPLATE)};
  var code=tpl.replace('__HA_ORIGIN__',JSON.stringify(location.origin));
  var bm=document.getElementById('bm');
  bm.setAttribute('href','javascript:'+encodeURIComponent(code));
  bm.addEventListener('click',function(ev){{ev.preventDefault();alert('Trascina il pulsante nella barra dei preferiti.');}});
}})();
"""
    return _page("Riconnetti Contarina SOL", body, script)


def receive_page() -> str:
    body = "<h2>Contarina SOL</h2><p id='msg'>Invio del token a Home Assistant…</p>"
    script = f"""
(function(){{
  var msg=document.getElementById('msg');
  function show(text,cls){{msg.textContent=text;msg.className=cls||'';}}
  var token=location.hash.slice(1);
  history.replaceState(null,'',location.pathname);
  var KEY={json.dumps(STORAGE_KEY)}, TTL={PENDING_TTL_SECONDS * 1000};
  function fresh(r){{return r&&r.flow_id&&r.state&&Date.now()-r.ts<=TTL;}}
  var pending=null, map={{}};
  try{{pending=JSON.parse(sessionStorage.getItem(KEY)||'null');sessionStorage.removeItem(KEY);}}catch(e){{}}
  try{{map=JSON.parse(localStorage.getItem(KEY)||'{{}}')||{{}};}}catch(e){{map={{}};}}
  var live=Object.keys(map).filter(function(k){{return fresh(map[k]);}});
  if(!fresh(pending)){{
    pending=null;
    if(live.length===1){{pending=map[live[0]];}}
    else if(live.length>1){{token='';show('Ci sono più riconnessioni aperte: usa il preferito nella scheda aperta da Home Assistant, oppure chiudi le altre e riprova.','err');return;}}
  }}
  if(pending){{delete map[pending.flow_id];}}
  try{{if(Object.keys(map).length){{localStorage.setItem(KEY,JSON.stringify(map));}}else{{localStorage.removeItem(KEY);}}}}catch(e){{}}
  if(!token){{show('Nessun token ricevuto. Usa il preferito sulla pagina di SOL dopo il login.','err');return;}}
  if(!pending){{
    token='';show('Nessuna riconnessione attiva in questo browser per questo indirizzo di Home Assistant. Avvia Riconnetti dalle impostazioni dell\\'integrazione.','err');return;}}
  fetch({json.dumps(RECEIVE_PATH)},{{method:'POST',credentials:'same-origin',referrerPolicy:'no-referrer',cache:'no-store',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{flow_id:pending.flow_id,state:pending.state,token:token}})}})
  .then(function(r){{return r.json().catch(function(){{return {{}};}}).then(function(j){{return [r.status,j];}});}})
  .then(function(x){{token='';
    if(x[0]===200&&x[1].result==='ok'){{show('Contarina ricollegata. Puoi chiudere questa scheda e tornare a Home Assistant.','ok');}}
    else{{show(x[1].message||'Riconnessione non riuscita. Riprova da Home Assistant oppure usa il copia-incolla.','err');}}}})
  .catch(function(){{token='';show('Home Assistant non raggiungibile da questo browser.','err');}});
}})();
"""
    return _page("Contarina SOL", body, script)


def _page(title: str, body: str, script: str) -> str:
    return (
        "<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='referrer' content='no-referrer'>"
        f"<title>{title}</title><style>{_PAGE_STYLE}</style></head><body>{body}"
        f"<script>{script}</script></body></html>"
    )


OUTCOME_MESSAGES = {
    "ok": "Contarina ricollegata.",
    "invalid_auth": "Token SOL non valido o scaduto: rifai il login su SOL e riprova.",
    "wrong_account": "Il token appartiene a un altro account SOL.",
    "cannot_connect": "Contarina SOL non raggiungibile: riprova tra poco.",
    "expired": "Riconnessione scaduta o già usata: riavviala da Home Assistant.",
    "forbidden_origin": "Richiesta non proveniente da questo Home Assistant.",
    "bad_request": "Richiesta non valida.",
}
