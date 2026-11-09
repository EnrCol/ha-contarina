# Esempi Lovelace — Contarina SOL 0.2.6 / 0.2.7b1

La card **`custom:contarina-invoice-card`** è inclusa nell'integrazione; non richiede un secondo repository HACS. Le dashboard sono invece facoltative e non vengono create automaticamente.

**Privacy:** fatture, importi, identificativi e PDF sono dati personali. Una dashboard riservata agli amministratori nasconde le viste agli altri utenti, ma non impone permessi amministrativi all'endpoint PDF (che richiede soltanto l'autenticazione HA). Usa l'integrazione solo su istanze il cui accesso sia adeguatamente limitato e consulta [privacy e sicurezza](docs/PRIVACY_SICUREZZA.md).

## 1. Card fatture PDF (esempio minimo)

Dopo aver configurato almeno una utenza SOL, apri **Modifica dashboard → Aggiungi scheda → Manuale**:

```yaml
type: custom:contarina-invoice-card
title: Fatture Contarina
# entity: sensor.INSERISCI_ID_FATTURE_DISPONIBILI  # facoltativo, per una sola utenza
```

Senza `entity`, la card trova automaticamente tutti i sensori con attributo `contarina_metric: invoice_history`. Raggruppa per anno e offre i pulsanti **Apri PDF** e **Scarica PDF**. Se imposti `entity`, devi usare l'identificativo reale del sensore *Fatture disponibili*, ottenibile in **Strumenti per sviluppatori → Stati**; il nome dell'entità può avere prefissi diversi a seconda del dispositivo.

I PDF vengono richiesti a SOL soltanto al primo accesso e salvati in `media/contarina/fatture/UTENZA/ANNO/NUMERO_ID.pdf` quando la cartella è scrivibile. In seguito sono serviti dall'archivio locale; una sessione SOL valida è necessaria per scaricare PDF non ancora archiviati. Il visualizzatore include pdf.js 4.10.38: **nessuna CDN necessaria**, ma Home Assistant deve essere raggiungibile.

## 2. Dashboard completa (due viste)

Nell'editor **YAML dell'intera dashboard** (non nell'editor di una singola scheda) usa questa configurazione. Per una nuova dashboard, puoi crearne una in modalità storage, aprire l'editor di configurazione YAML e sostituire il contenuto iniziale.

```yaml
title: Contarina SOL
views:
  - title: Raccolta
    path: raccolta
    icon: mdi:recycle
    type: sections
    max_columns: 2
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Raccolte
            icon: mdi:calendar-check
          - type: markdown
            content: |-
              {% set ns = namespace(count=0) %}
              {% for e in integration_entities('contarina') | sort %}
              {% if e.startswith('sensor.') and
                 (e.endswith('_rifiuti_oggi') or
                  e.endswith('_rifiuti_domani') or
                  e.endswith('_prossima_raccolta')) %}
              - **{{ state_attr(e, 'friendly_name') or e }}:** {{ states(e) }}
              {% set ns.count = ns.count + 1 %}
              {% endif %}
              {% endfor %}
              {% if ns.count == 0 %}
              Nessun sensore disponibile. Completa prima il collegamento SOL.
              {% endif %}
      - type: grid
        cards:
          - type: heading
            heading: Contenitori e svuotamenti
            icon: mdi:trash-can-outline
          - type: markdown
            content: |-
              {% set ns = namespace(count=0) %}
              {% for e in integration_entities('contarina') | sort %}
              {% if e.startswith('sensor.') and 'svuotamenti_anno_' in e %}
              - **{{ state_attr(e, 'friendly_name') or e }}:** {{ states(e) }}
              {% set ns.count = ns.count + 1 %}
              {% endif %}
              {% endfor %}
              {% if ns.count == 0 %}
              Nessun contatore svuotamenti disponibile.
              {% endif %}
          - type: markdown
            content: >-
              Il minimo Secco è una stima tariffaria, non un numero
              di svuotamenti gratuiti. Verifica i dettagli su SOL.
  - title: Fatture PDF
    path: fatture
    icon: mdi:file-pdf-box
    type: sections
    max_columns: 2
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Storico e PDF
            icon: mdi:receipt-text
          - type: custom:contarina-invoice-card
            title: Fatture Contarina
            grid_options:
              columns: full
              rows: auto
      - type: grid
        cards:
          - type: heading
            heading: Riepilogo annuale
            icon: mdi:chart-bar
          - type: markdown
            content: |-
              {% set ns = namespace(count=0) %}
              {% for e in integration_entities('contarina') | sort %}
              {% if state_attr(e, 'contarina_metric') == 'invoice_history' %}
              **{{ state_attr(e, 'friendly_name') or e }}:** {{ states(e) }} fatture

              {% for anno, dati in (state_attr(e, 'riepilogo_annuale') or {}).items() | sort(reverse=true) %}
              - **{{ anno }}:** {{ dati.get('numero_fatture', 0) }} fatture · {{ '%.2f' | format(dati.get('totale_fatturato', 0) | float) }} € fatturati
              {% endfor %}
              {% set ns.count = ns.count + 1 %}
              {% endif %}
              {% endfor %}
              {% if ns.count == 0 %}
              Storico non ancora disponibile. Controlla il collegamento SOL.
              {% endif %}

              Gli importi fatturati non sono necessariamente importi da pagare.
          - type: button
            name: Archivia fatture PDF mancanti
            icon: mdi:file-download-outline
            show_state: false
            tap_action:
              action: perform-action
              perform_action: contarina.download_invoices
              confirmation:
                text: Scaricare e archiviare tutti i PDF mancanti?
```

La dashboard usa `integration_entities('contarina')`: non contiene riferimenti ai numeri di utenza reali. In presenza di più account/utenze legge tutte le entità disponibili, salvo filtri di visibilità e permessi del frontend.

## 3. Calendar e sensori nativi

Puoi aggiungere anche una **card Calendario** nativa, ma devi scegliere l'entità `calendar.*` reale da **Strumenti per sviluppatori → Stati**. Lo stesso vale per i singoli sensori Secco, contenitori, fatture e raccolte. Il suffisso è indicativo, **non è garantito** un prefisso fisso `sensor.contarina_NUMERO`.

Per il **minimo annuo Secco**, consulta gli attributi del relativo sensore svuotamenti. La stima è prevista soltanto per una utenza domestica con un unico contenitore Secco attivo da 120 L: gli svuotamenti minimi sono **fatturati**, non gratuiti.

## 4. Azione di archiviazione

Il pulsante della dashboard chiama `contarina.download_invoices`, che archivia i PDF mancanti per tutte le utenze configurate. È possibile anche eseguire l'azione manualmente da **Strumenti per sviluppatori → Azioni**. Il parametro facoltativo `invoice_id` limita l'operazione a un identificativo SOL.

**Attenzione:** l'archivio Media conserva i PDF anche quando la relativa integrazione viene rimossa. Non usare l'azione su una istanza condivisa senza aver valutato chi può accedere ai file e ai backup.

## 5. Se la card non compare

1. Verifica che l'integrazione risulti **Caricata** e che il sensore *Fatture disponibili* contenga l'attributo `storico_fatture`.
2. In **Impostazioni → Dashboard → Risorse** verifica la presenza del modulo `/contarina_static/contarina-invoice-card.js?v=0.2.6` (l'indirizzo viene registrato automaticamente).
3. Aggiorna la pagina ignorando la cache; dopo l'installazione di un nuovo componente è normalmente necessario riavviare Home Assistant.
4. Non usare una URL pubblica per i PDF: la card effettua richieste autenticate tramite il frontend HA.

Per altri problemi: [FAQ](docs/FAQ.md), [installazione](MARKETPLACE.md).

## 6. Scadenza ultima fattura (beta 0.2.7b1)

La beta aggiunge **un sensore nativo di tipo data per ogni utenza**: *Scadenza ultima fattura*. Il suo stato è una data ISO `YYYY-MM-DD` (oppure non disponibile, se SOL non fornisce una scadenza valida). Sono presenti gli attributi `emissione`, `importo` (totale fattura, non residuo), `stato` (classificazione SOL) e `tipo_importo`.

Il sensore fa riferimento alla **fattura più recente per data di emissione**, anche se già pagata: **non** è necessariamente la prossima bolletta da pagare. `stato: due` o un importo non dimostrano da soli l'esistenza di un debito; verifica sul portale ufficiale.

Per riepilogare più utenze senza conoscere gli `entity_id`, aggiungi una card Markdown:

```yaml
type: markdown
title: Contarina — Scadenze ultime fatture
content: |-
  {% set ns = namespace(count=0) %}
  {% for e in integration_entities('contarina') | sort %}
  {% if e.startswith('sensor.') and e.endswith('_scadenza_ultima_fattura') %}
  - **{{ state_attr(e, 'friendly_name') or e }}**:
    {{ states(e) if has_value(e) else 'Non disponibile' }}
    · Totale: {{ ('%.2f €' | format(state_attr(e, 'importo') | float)) if is_number(state_attr(e, 'importo')) else '—' }}
    · Stato SOL: {{ state_attr(e, 'stato') or 'Sconosciuto' }}
  {% set ns.count = ns.count + 1 %}
  {% endif %}
  {% endfor %}
  {% if ns.count == 0 %}
  Nessun sensore Scadenza ultima fattura disponibile.
  {% endif %}
```

Per inserirlo in una card `entities` con altre utenze/fornitori, usa l'`entity_id` effettivo da **Strumenti per sviluppatori → Stati**. Non supporre un prefisso fisso.
