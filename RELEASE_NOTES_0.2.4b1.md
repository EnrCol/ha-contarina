# Contarina SOL 0.2.4b1

## Sessione
- Keep-alive del JWT ogni 10 minuti, incondizionato: il residuo non scende mai sotto ~45 minuti (prima ~25). Un'interruzione di Home Assistant o della rete fino a ~45 minuti non richiede più la riautenticazione.
- Verificato che SOL non dispone di refresh token, sessioni lato server o cookie di rinnovo: un JWT scaduto riceve 401 e serve un nuovo login dal browser.

## Riconnessione
- Nuovo **Riconfigura** nelle impostazioni dell'integrazione e nuova riautenticazione con due scelte: *Riconnetti dal browser* (consigliato) o *Incolla il token*.
- *Riconnetti dal browser*: step esterno nativo di Home Assistant, stato casuale monouso legato al flusso (10 min, 5 tentativi), preferito senza segreti, token trasportato nel frammento URL e verificato con SOL e con l'account configurato. In caso di errore il flusso passa al copia-incolla.
- Nessuna credenziale SOL salvata; nessun login automatico né gestione di reCAPTCHA.

## Revisione
- Keep-alive anche all'avvio: un token parzialmente usato viene rinnovato subito (residuo pieno dal primo minuto).
- Rimosso l'update listener: le opzioni ricaricano tramite `OptionsFlowWithReload`; riautenticazione e riconfigurazione tramite `async_update_reload_and_abort` (compatibile con HA 2026.12).
- URL dello step esterno assoluto (`HA-Frontend-Base`, ripiego su URL configurato, altrimenti copia-incolla): il frontend HA scarta gli URL relativi.
- Codice monouso in `sessionStorage` (per scheda) con ripiego per flusso; controllo `Origin` same-origin rigoroso (schema, host e porta, confrontati con quelli che Home Assistant ha già risolto, che considera le intestazioni inoltrate solo dai proxy fidati); `credentials: same-origin` per proxy con cookie.
- CI e workflow di release su Python 3.14; la release beta parte solo dopo test Python, Node, Home Assistant, hassfest e HACS, con note ricavate dalla versione del manifest.

## Test
- Unit test per lo store monouso, la validazione delle richieste e le pagine.
- Test Node del bookmarklet di riconnessione.
- Test con Home Assistant (pytest-homeassistant-custom-component, HA 2026.10.4 / Python 3.14): keep-alive, setup, opzioni, riconfigurazione e reauth, URL assoluto e ripieghi, Origin (schema, porta, host, proxy fidato e non fidato), account errato, replay, flusso chiuso, token scaduto, end-to-end in Chrome (stessa scheda e scheda diversa).
- Collaudo su istanza reale HA 2026.11.0 con frontend: Riconfigura → Riconnetti dal browser → apertura pagina → SOL (simulato in locale) → preferito → "Contarina reconnected", entry caricata.
