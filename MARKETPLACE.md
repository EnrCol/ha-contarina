# Marketplace install instructions — beta 0.2.1b1

Repository: https://github.com/EnrCol/ha-contarina (public, custom integration).

1. Home Assistant 2026.11+: Settings → Marketplace → Add from link.
2. Paste the repository URL. If requested, authorize GitHub access.
3. Choose Contarina SOL (unofficial) and install. Restart if requested.
4. Settings → Devices & services → Add integration → Contarina SOL.
5. Provide a fresh accessToken obtained by logging into SOL in your personal browser. Do not share tokens outside Home Assistant.
6. Select one or more contracts. The existing waste system remains enabled.

Only the initial token and subsequent reauth require browser login; the integration otherwise refreshes JWTs while HA remains connected. The token expires after 55 minutes, so a prolonged outage requires reauth.

**Beta warning:** the custom integration is not yet tested on an isolated HA instance; do not install in production without first verifying GitHub Actions and the test plan.

Rollback: remove the Contarina config entry and uninstall the custom repository from Marketplace. Existing waste integrations and automations are unaffected.

After an approved update, verify the new `Fatture in scadenza`, `Fatture scadute da verificare` and `Totale fatturato anno` sensors. Existing entity IDs are intentionally kept. The updated last-emptying and next-collection sensors are display strings (DD-MM-YYYY) with `data_iso` attributes. To return to beta 0.2.0b1, reinstall the previously tested commit `a463eb17e65ed981c84a2aeaee9caa97f29e9594`; preserve the configuration and check the old data format before re-enabling automations.
