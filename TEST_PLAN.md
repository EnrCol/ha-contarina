# Contarina 0.2 — Test plan

## Offline

- [x] Pure parser and API tests prepared (synthetic fixtures only).
- [x] Source syntax and JSON checks performed for the original beta package.
- [ ] Verify published code using GitHub Actions after repository commit.

## Home Assistant isolated test

- [ ] hassfest and Marketplace validation on GitHub.
- [ ] Config flow and multi-contract selection.
- [ ] Entity registry, calendar, sensors and multiple devices.
- [ ] Normal token refresh, restart with valid token and reauth after 401.
- [ ] Compare collected dates with SOL and the existing ICS schedule.
- [ ] Compare annual emptying totals with SOL including midnight/DST boundaries.
- [ ] Compare invoice status and outstanding-balance flag with SOL.
- [ ] HTTP 200 error objects, outage, timeout, year boundary, and calendar API range.
- [ ] Seven-day sliding-refresh soak test and privacy audit.
- [ ] Graceful removal of the test config entry and Marketplace integration.

## Live migration (separate approval required)

- [ ] Re-read all current consumers of calendar.rifiuti, sensor.rifiuti_oggi, sensor.rifiuti_domani, sensor.prossimi_rifiuti.
- [ ] Migrate packages/awtrix3/awtrix_rifiuti.yaml and packages/raccolta_differenziata_2025.yaml.
- [ ] Migrate CASA dashboard cards and verify no stale references.
- [ ] Remove Waste Collection Schedule only after equivalence tests and an approved rollback plan.
