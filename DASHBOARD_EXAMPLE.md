# Home Assistant example dashboard — display-only, opt-in

The device page automatically orders entities by name; it cannot be reordered by this repository.
Use a separate dashboard **Entities** card to show the requested order.

Replace `CONTRACT` in the sample with the stable contract suffix of your installed
Contarina entities (see Settings → Devices & services → Contarina → Entities).
Keep the current waste automations untouched until the integration is tested.

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Raccolta rifiuti
    entities:
      - entity: sensor.contarina_CONTRACT_rifiuti_oggi
        name: Oggi
      - entity: sensor.contarina_CONTRACT_rifiuti_domani
        name: Domani
      - entity: sensor.contarina_CONTRACT_prossima_raccolta
        name: Prossima raccolta
  - type: calendar
    title: Calendario raccolte
    entities:
      - calendar.contarina_CONTRACT_raccolta_rifiuti
```

The native calendar exposes all published upcoming SOL events (currently only until
the end of its published year). It does not need another custom calendar entity.

**Date note:** The next-collection and last-emptying sensors show `GG-MM-AAAA`
as text. Use their `data_iso` attribute for automation date comparisons.
