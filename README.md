# Contarina SOL — Home Assistant integration (prototype 0.2.1b1)

**Unofficial community integration. Not affiliated with Contarina S.p.A.**

> Development beta. Do not replace a working waste collection setup until this integration has been validated on an isolated Home Assistant installation.

## Features

- Native read-only Contarina SOL integration. No dependency on Waste Collection Schedule or other custom integrations.
- Multiple contracts per SOL account, automatically discovered and selectable during configuration.
- Waste collection calendar and today/tomorrow/next collection sensors, fetched from the authenticated SOL API.
- Bin inventory and annual recorded emptying counts, with date and material attributes.
- Latest invoice, invoice status, open invoice count, and outstanding-balance indicator.
- Automatic sliding JWT refresh checked every 15 minutes, with the renewed token stored privately by Home Assistant.
- Italian and English setup translations; aggregate-only diagnostics.

## Authentication and limitations

SOL uses a browser login with reCAPTCHA v3. **Username/password automatic login is not supported.** The beta setup requires a fresh accessToken JWT from your own authenticated SOL browser session, entered in the private Home Assistant integration setup UI. **Never share this token in chat, issues or public files.** It is a bearer credential that contains personal information.

Access tokens expire after 55 minutes. The integration refreshes them while Home Assistant is running; an interruption beyond the remaining JWT lifetime requires browser reauthentication. The absolute maximum length of a refresh chain is not yet proven.

## Install from Home Assistant Marketplace (2026.11+)

1. Open **Settings → Marketplace → Add from link**.
2. Enter **https://github.com/EnrCol/ha-contarina** and add it as a custom integration repository.
3. Install **Contarina SOL (unofficial)**. Restart Home Assistant if required.
4. Open **Settings → Devices & services → Add integration → Contarina SOL**.
5. Sign in to https://sol.servizicontarina.it/ in your browser and obtain a fresh `accessToken`; enter it **only** in the Home Assistant configuration form.
6. Select the contracts you want to monitor.

**This is an untested beta.** Retain your existing garbage collection and notification automations during validation.

## Verified source and current limits

The API endpoint shapes originate from a sanitized, authenticated SOL session audit on 5 November 2026. They have not yet been exercised by this code inside Home Assistant. The API is undocumented and may change without notice.

Not yet implemented: an easy browser-assisted initial login, invoice balance-due amount, tariff/emptying-cost estimates, automatically adding newly assigned bins without a reload. Next-year calendar publication and non-domestic/condominium cases require additional tests.

## Security

All operations are HTTP GET and read-only. No financial transactions or contract changes. Tokens and raw API responses are not included in diagnostics or source files. Secure Home Assistant config storage and backups as they contain the access token.

## Development and tests

Run offline tests with `python -m pip install aiohttp && python -m unittest discover -s tests -v`. GitHub Actions runs tests, hassfest and HACS validation. The results must be checked before asserting Marketplace compatibility.

See [SPEC_0_2.md](SPEC_0_2.md), [TEST_PLAN.md](TEST_PLAN.md), and [MARKETPLACE.md](MARKETPLACE.md).

License: MIT.

## Beta 0.2.1 — visible data improvements

- Upcoming collection and last-emptying sensors display `GG-MM-AAAA` as text, with `data_iso` for machine-readable use. The native calendar is unchanged. These two sensor types no longer expose `device_class: date`; automations expecting date entities must use `data_iso` rather than comparing the text state as a date.
- Existing unique IDs for bin-emptying and last-emptying sensors are preserved. Their display names now use the waste material instead of the container code; the original `COD_CONTENITORE` is exposed as `codice_contenitore` in attributes. Existing `entity_id` values can still contain the old codes because Home Assistant's registry keeps them stable.
- Last emptying is now searched across the container's recorded lifetime. When SOL omits its activation date, the search falls back to the last ten years and marks the attributes `storico_completo: false`.
- Invoice summaries distinguish **due soon**, **overdue for review** and **other unsettled status**, without treating an upcoming bill as an overdue balance. Existing `fatture_da_verificare` unique ID is preserved.
- The new `Totale fatturato anno` sensor sums known, regular SOL invoices by **issue year**, not payments made during the year. Cancelled, refunded, compensated and unknown-status documents are excluded, and the excluded count is explicit. Credit-note netting and the exact amount owed remain unverified; this is **not a spending or cash-flow sensor**.
- `Fatture disponibili` retains the count and exposes an issuance-year summary plus a bounded list of invoice details in attributes (up to 60 entries). These attributes are private Home Assistant data and may be recorded by Recorder; do not expose the sensor publicly.
- To display **Rifiuti oggi** before **Rifiuti domani** and show upcoming collection dates, use the explicit dashboard configuration in [DASHBOARD_EXAMPLE.md](DASHBOARD_EXAMPLE.md). The alphabetical auto-generated device list cannot be reordered by this integration.

All changes are limited to the GitHub source. Installing an update in Home Assistant is a separate operation requiring approval.
