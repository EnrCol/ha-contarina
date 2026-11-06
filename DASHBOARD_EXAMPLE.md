# Card Lovelace Contarina — esempi da copiare

Le card non vengono create automaticamente dall'integrazione. Puoi aggiungerle a una dashboard privata in Home Assistant con **Modifica dashboard → Aggiungi scheda → Manuale**.

Sostituisci `CONTRACT` con il suffisso del tuo contratto come appare negli `entity_id`. Per i contenitori, sostituisci `SECCO_CODE` con il suffisso completo del sensore **Svuotamenti anno - Secco**. Esempio: se l'entità è `sensor.contarina_123456_svuotamenti_anno_s654321`, usa `CONTRACT=123456` e `SECCO_CODE=s654321`.

## 1. Raccolta e svuotamenti

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Raccolte Contarina
    entities:
      - entity: sensor.contarina_CONTRACT_rifiuti_oggi
        name: Oggi
      - entity: sensor.contarina_CONTRACT_rifiuti_domani
        name: Domani
      - entity: sensor.contarina_CONTRACT_prossima_raccolta
        name: Prossima raccolta
      - entity: sensor.contarina_CONTRACT_svuotamenti_anno_SECCO_CODE
        name: Svuotamenti Secco
  - type: markdown
    title: Minimo Secco
    content: >-
      {% set e = 'sensor.contarina_CONTRACT_svuotamenti_anno_SECCO_CODE' %}
      {% set minimo = state_attr(e, 'minimo_annuo_stimato') %}
      {% if minimo is number and states(e) not in ['unknown', 'unavailable'] %}
      **{{ states(e) }} su {{ minimo }}** prese minime fatturate.
      **{{ state_attr(e, 'svuotamenti_prima_eccedenza') }}** prima dell'eccedenza.
      {% else %}
      Stima non disponibile per questa utenza o versione.
      {% endif %}
```

**Nota:** la quota minima del Secco da 120 L per utenze domestiche è una quantità **fatturata**, non un numero di prese gratuite. Il calcolo utilizza i componenti attualmente comunicati da SOL; la fattura può fare riferimento al nucleo al 31 dicembre precedente.

## 2. Storico fatture (solo dashboard privata)

Lo storico delle fatture non richiede sensori aggiuntivi: legge l'attributo `storico_fatture` di `sensor.contarina_CONTRACT_fatture_disponibili`.

```yaml
type: markdown
title: Storico fatture Contarina
content: >-
  {% set righe = state_attr('sensor.contarina_CONTRACT_fatture_disponibili', 'storico_fatture') or [] %}
  {% set ns = namespace(lines=['| Emissione | Importo | Stato SOL |', '| :--- | ---: | :--- |']) %}
  {% for f in righe %}
    {% set em = f.emissione[8:10] ~ '/' ~ f.emissione[5:7] ~ '/' ~ f.emissione[:4] if f.emissione else '—' %}
    {% set imp = ('%.2f' | format(f.importo | float)).replace('.', ',') ~ ' €' if f.importo is not none else '—' %}
    {% set stato = 'Pagata' if f.stato == 'paid' else 'Da verificare' if f.stato in ['due', 'unpaid', 'partially_paid'] else (f.stato or '—') %}
    {% set ns.lines = ns.lines + ['| ' ~ em ~ ' | ' ~ imp ~ ' | ' ~ stato ~ ' |'] %}
  {% endfor %}
  {{ ns.lines | join('\n') if righe else 'Nessuna fattura disponibile.' }}
```

La label «Da verificare» **non significa necessariamente insoluto**: per il saldo reale usa il portale SOL. Non pubblicare questa scheda in una dashboard accessibile a ospiti.

## 3. Calendario nativo

```yaml
type: calendar
title: Calendario raccolte
entities:
  - calendar.contarina_CONTRACT_raccolta_rifiuti
```

Le date visualizzate come testo dai sensori hanno anche l'attributo `data_iso` (`AAAA-MM-GG`) per le automazioni. Il calendario usa invece normali eventi Home Assistant.