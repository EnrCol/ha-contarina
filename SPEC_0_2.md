# Contarina SOL — specifica tecnica (0.2.5b2)

**Stato:** integrazione personalizzata beta per Home Assistant 2026.11+, con primo login e una utenza domestica verificati in ambiente reale. Non è un prodotto ufficiale Contarina S.p.A. Nessuna scrittura sui servizi del gestore.

## Architettura

- `custom_components/contarina/` contiene manifest, config flow, API, sessione, coordinator, entità, calendario, avvisi e pagine per il collegamento da browser.
- L'autenticazione avviene sul portale SOL. Il config flow accetta il JWT, valida il profilo e presenta i contratti; lo memorizza nella config entry di HA e lo rinnova quando possibile.
- La configurazione può selezionare più contratti sullo stesso account SOL. Ogni contratto selezionato espone un dispositivo Home Assistant con sensori, binary sensor e calendario; gli `unique_id` sono deterministici.
- `DataUpdateCoordinator` pianifica polling e cache; le API di Contarina vengono consultate tramite GET con limite di concorrenza.

## Interfacce SOL osservate (non pubbliche)

| Endpoint GET | Funzione |
| --- | --- |
| `/api/contracts?active=all` | Elenco contratti |
| `/api/contracts/{ref}` | Dettagli e componenti |
| `/api/users/areas/{ref}` | Area per calendario |
| `/api/sol/ecocalendars` | Identificativi calendari |
| `/api/sol/emptying-types` | Tipologie rifiuti |
| `/api/sol/ecocalendar-emptyings` | Eventi raccolta |
| `/api/services/equipment/contract/{ref}` | Contenitori |
| `/api/users/{ref}/emptyings/{codice}` | Svuotamenti |
| `/api/users/{ref}/accounting` | Documenti contabili |
| `/api/users/{ref}/check-balance` | Indicazione aggregata di saldo |
| `/api/users/refresh-token` | Rinnovo JWT |

La struttura non è documentata ufficialmente da Contarina. Qualsiasi endpoint può cambiare senza preavviso.

## Sessione

- JWT SOL: durata osservata circa **3300 secondi (55 minuti)**. Dopo la scadenza, SOL risponde 401 e non rinnova il token.
- Keepalive ogni circa 10 minuti mentre HA è operativo, e rinnovo all'avvio quando necessario; il limite assoluto dei rinnovi successivi non è noto.
- Il flusso `user` offre **Collega dal browser** o **Incolla JWT**. Gli step `reauth` e `reconfigure` riutilizzano il flusso browser.
- Il pairing utilizza uno stato casuale di 256 bit, monouso, valido 10 minuti, con controlli di tentativi. Per altro browser/dispositivo è disponibile un codice di 8 caratteri monouso, con limite globale ai tentativi errati.
- Il token arriva alla pagina HA tramite frammento URL, poi POST same-origin, validato tramite `Origin` (schema/host/porta, con `trusted_proxies`) e dal backend SOL. Non si memorizzano password.
- La scadenza genera il flusso native reauth, una notifica persistente, l'evento `contarina_session_expired` con `entry_id` e `url` e un push `notify.*` opzionale. Niente avvisi duplicati finché lo stato non torna operativo.

## Modello dati

- Raccolta: calendario nativo ed entità oggi/domani/prossima raccolta.
- Svuotamenti: conteggio annuale distinto dalla data di ultimo svuotamento storico; eventuale troncamento dello storico dichiarato negli attributi.
- Secco 120 L: per **un solo contenitore domestico attivo** con componenti e quantità validi, `minimo_annuo_stimato = componenti + 1`, `svuotamenti_prima_eccedenza` e `svuotamenti_oltre_minimo`. Non extrapolare ad altri casi.
- Fatture: classificazioni SOL, scadenze, fatturato annuo lordo e storico ridotto (fino agli ultimi 60 documenti nell'attributo); non confondere con pagato o saldo dovuto.
- Date visualizzate `GG-MM-AAAA`; attributo `data_iso` per automazioni. I `unique_id` restano invariati per le entità esistenti.

## Sicurezza e limiti

Le richieste al portale sono di sola lettura; il JWT è una credenziale privata della config entry e dei backup HA. Le diagnostiche escludono token e documenti individuali e restituiscono aggregati. Vedi [Privacy e sicurezza](docs/PRIVACY_SICUREZZA.md).

**Non ancora convalidati su un insieme rappresentativo di utenze:** contratti condominiali e commerciali, più contenitori omogenei, durata di sessione su molte settimane, tutte le famiglie di browser e push mobile reale.

## Verifiche

La CI include unit test Python, Node bookmarklet, test Home Assistant con browser Chrome, hassfest e HACS. Su HA 2026.11 reale è stata completata una prima configurazione da browser SOL autentico, poi la rimozione e ricreazione di un contratto domestico senza cambiamento di 23 identificativi di entità. Per la matrice e i casi ancora aperti vedi [TEST_PLAN.md](TEST_PLAN.md).

Il rendering dell'icona nel Marketplace/HACS e nel frontend HA è un problema distinto dalle API SOL: i file brand locali sono inclusi, ma la visualizzazione non è ancora verificata su tutte le schermate.
