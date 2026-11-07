# Esempi Lovelace — Contarina SOL

Le card sono **opzionali** e **non vengono installate automaticamente**. Apri una dashboard privata → **Modifica → Aggiungi scheda → Manuale** e incolla uno degli esempi. Non servono card personalizzate.

## Identificare i sensori

Apri **Impostazioni → Dispositivi e servizi → Contarina → Entità**.

Negli esempi sostituisci:
- `CONTRATTO` con il numero che compare nei tuoi `entity_id` (es. in `sensor.contarina_123456_rifiuti_oggi`, il codice è `123456`).
- `SECCO` con il codice del contenitore Secco attivo (es. `s654321` in `sensor.contarina_123456_svuotamenti_anno_s654321`).

Non condividere gli `entity_id` reali se contengono identificativi personali.

## 1. Raccolte e minimo Secco

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Contarina — Raccolte
    entities:
      - entity: sensor.contarina_CONTRATTO_rifiuti_oggi
        name: Oggi
      - entity: sensor.contarina_CONTRATTO_rifiuti_domani
        name: Domani
      - entity: sensor.contarina_CONTRATTO_prossima_raccolta
        name: Prossima raccolta
      - entity: sensor.contarina_CONTRATTO_svuotamenti_anno_SECCO
        name: Secco — svuotamenti anno
  - type: markdown
    title: Secco — soglia annuale
    content: >-
      {% set e = 'sensor.contarina_CONTRATTO_svuotamenti_anno_SECCO' %}
      {% set minimo = state_attr(e, 'minimo_annuo_stimato') %}
      {% if minimo is number and states(e) not in ['unknown', 'unavailable'] %}
      **{{ states(e) }} / {{ minimo }}** svuotamenti minimi fatturati.

      **{{ state_attr(e, 'svuotamenti_prima_eccedenza') }}** prima dell'eccedenza.

      **{{ state_attr(e, 'svuotamenti_oltre_minimo') }}** oltre il minimo.
      {% else %}
      Minimo annuo non disponibile per questo contratto o contenitore.
      {% endif %}
```

Il minimo è una **stima** solo per un unico contenitore Secco domestico attivo da 120 L; è la quantità **fatturata**, non un numero di prese gratuite. I componenti SOL possono differire da quelli presi a riferimento sulla fattura.

## 2. Fatture — dashboard privata

I dati sono nell'attributo `storico_fatture` del sensore **Fatture disponibili**, senza database o sensori aggiuntivi. Non mostrare la card a utenti ospiti.

```yaml
type: markdown
title: Contarina — Storico fatture
content: >-
  {% set fatture = state_attr('sensor.contarina_CONTRATTO_fatture_disponibili', 'storico_fatture') or [] %}
  {% set ns = namespace(righe=['| Emissione | Totale | Stato SOL |', '| :--- | ---: | :--- |']) %}
  {% for f in fatture %}
  {% set em = f.emissione[8:10] ~ '/' ~ f.emissione[5:7] ~ '/' ~ f.emissione[:4] if f.emissione else '—' %}
  {% set totale = ('%.2f' | format(f.importo | float)).replace('.', ',') ~ ' €' if f.importo is not none else '—' %}
  {% set stato = 'Pagata' if f.stato == 'paid' else 'Da verificare' if f.stato in ['due', 'unpaid', 'partially_paid'] else (f.stato or '—') %}
  {% set ns.righe = ns.righe + ['| ' ~ em ~ ' | ' ~ totale ~ ' | ' ~ stato ~ ' |'] %}
  {% endfor %}
  {{ ns.righe | join('\n') if fatture else 'Nessuna fattura disponibile.' }}
```

**«Da verificare» non equivale a «da pagare».** Il totale fatturato non è un saldo residuo: controlla il portale Contarina per lo stato reale.

## 3. Calendario nativo

```yaml
type: calendar
title: Contarina — Calendario raccolte
entities:
  - calendar.contarina_CONTRATTO_raccolta_rifiuti
```

Il calendario offre eventi Home Assistant nativi. Nei sensori testuali delle date, per automazioni e confronti usa l'attributo `data_iso` anziché analizzare la stringa `GG-MM-AAAA`.

## 4. Contatori fatture

```yaml
type: entities
title: Contarina — Fatture
entities:
  - entity: sensor.contarina_CONTRATTO_ultima_fattura
    name: Ultima fattura
  - entity: sensor.contarina_CONTRATTO_fatture_disponibili
    name: Fatture nello storico
  - entity: sensor.contarina_CONTRATTO_fatture_in_scadenza
    name: In scadenza
  - entity: sensor.contarina_CONTRATTO_fatture_scadute_da_verificare
    name: Scadute da verificare
  - entity: sensor.contarina_CONTRATTO_totale_fatturato_anno
    name: Totale fatturato nell'anno
```

Anche le voci «in scadenza» e «scadute da verificare» indicano **classificazioni da confrontare con SOL**, non una richiesta di pagamento verificata.

Per eventuali problemi di entità mancanti dopo una reinstallazione: [FAQ](docs/FAQ.md). Per l'installazione: [MARKETPLACE.md](MARKETPLACE.md).
