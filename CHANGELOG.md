# Changelog — Contarina SOL

Le versioni `b*` sono **beta**: l'API Contarina SOL non è pubblica e può cambiare. Le release GitHub sono il riferimento per installazione e downgrade.

## [0.2.5b2] — Documentazione per distribuzione beta

- Riscritto README per primo login facilitato, installazione, limitazioni e supporto.
- Aggiornate le istruzioni Marketplace, desktop/smartphone e riconnessione; aggiunte FAQ, privacy/sicurezza, contributi e guida al branding.
- Rivisti esempi Lovelace, specifica tecnica e test plan con distinzione tra collaudo reale e simulato.
- Aggiunto il collegamento diretto **My Home Assistant → Marketplace**.
- **Nessuna modifica alle logiche runtime, entità, API SOL, token o dati.**
- **Nota aperta:** l'icona è presente nel pacchetto, ma la visualizzazione su Marketplace e in alcune schermate di Home Assistant non è ancora confermata; vedi [FAQ](docs/FAQ.md#licona-non-compare-nel-marketplace-o-nelle-integrazioni).

## [0.2.5b1] — Primo collegamento facilitato e smartphone

- Primo collegamento via browser oltre a riconnessione/reauth, senza inserire manualmente il JWT.
- Abbinamento da un altro browser o smartphone tramite codice monouso.
- Notifica persistente, evento `contarina_session_expired` e push `notify.*` opzionale su scadenza.
- Nuova pagina mobile per creare il preferito e collegare SOL.
- Aggiunto `brand/logo.png`; test con Home Assistant isolato e Chrome, validazione HACS/hassfest.
- Test su un contratto domestico reale: rimozione/reinstallazione con 23 `entity_id` invariati.

## [0.2.4b1] — Sessione e riconnessione

- Keepalive del JWT circa ogni 10 minuti mentre HA è online, con rinnovo all'avvio quando possibile.
- Riconnessione via browser e preferito monouso; alternativa per incollare manualmente il token.
- Protezioni `Origin` su schema/host/porta, controllo proxy fidati e trattamento di Nabu Casa.
- Workflow di release vincolato a unit test, test Home Assistant, HACS e hassfest.

## [0.2.3b1] — Branding e guida iniziale

- Aggiunti esempi Lovelace, documentazione del bookmarklet e del Marketplace.
- Ripristinata icona locale verde con C bianca; documentazione per la beta.

## [0.2.2b1] — Soglia Secco

- Attributi sul sensore Secco per stima annuale dei minimi su una sola utenza domestica con bidone attivo da 120 L.
- Contatori prima dell'eccedenza e oltre il minimo, senza nuove entità.

## [0.2.1b1] e precedenti — Prima implementazione

- Lettura calendario, contratti, contenitori e storico svuotamenti da SOL.
- Fatture e importi annuali aggregati, stato dei documenti da verificare.
- Modello di entità Home Assistant e calendario nativo.

I riferimenti completi sono nelle [release GitHub](https://github.com/EnrCol/ha-contarina/releases).
