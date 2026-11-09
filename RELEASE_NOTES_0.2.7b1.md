# Contarina SOL 0.2.7b1 — Scadenza ultima fattura

Beta sviluppata dalla stabile `v0.2.6`.

## Nuova entità

- Per ogni utenza SOL configurata viene creato un sensore **Scadenza ultima fattura**.
- È un vero sensore Home Assistant con `device_class: date`: lo stato è la data ISO `YYYY-MM-DD` tratta dal campo SOL `scadenza` dell'ultima fattura **per data di emissione**.
- Attributi aggiuntivi: `emissione` (data ISO), `importo` (totale fattura, non residuo), `stato` (classificazione SOL), `tipo_importo` (`totale_fattura_non_residuo`).
- Se non ci sono fatture o la scadenza non è valida, il sensore non inventa una data.
- Lo `unique_id` è distinto e stabile per account/utenza; gli identificativi dei sensori esistenti non cambiano.

**Attenzione:** la scadenza dell'ultima fattura non indica necessariamente la prossima scadenza ancora da saldare. Anche l'eventuale importo pagato riportato da SOL non è una conferma autonoma dello stato reale.

## Esempio dashboard

Vedi [DASHBOARD_EXAMPLE.md](DASHBOARD_EXAMPLE.md#6-scadenza-ultima-fattura-beta-027b1) per una card Markdown che individua automaticamente i nuovi sensori e riepiloga scadenze, importi e stato SOL senza riferimenti a utenze reali.

## Compatibilità

- Home Assistant 2026.11.0 o successivo.
- Nessuna nuova chiamata API, dipendenza o modifica della card PDF.
- Si può aggiornare dalla stabile `v0.2.6`, poi riavviare Home Assistant per caricare il componente aggiornato.

## Test e limiti

- Test automatici: nuovo sensore nativo `date`, attributi, fatture mancanti, scadenza invalida e selezione dell'ultima fattura per emissione; più l'intera suite Python, Home Assistant/browser, HACS e hassfest della release.
- Le limitazioni di sicurezza del PDF (accesso per utenti HA autenticati, conservazione in Media e fallback su filesystem) non sono cambiate. Consulta [privacy e sicurezza](docs/PRIVACY_SICUREZZA.md).

Integrazione non ufficiale e indipendente da Contarina S.p.A.
