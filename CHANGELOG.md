# Changelog — Contarina SOL

Le versioni con suffisso `b*` sono **beta**; la 0.2.6 è la prima versione **stabile** del progetto. L'API Contarina SOL resta non pubblica e può cambiare. Le release GitHub sono il riferimento per installazione e downgrade.

## [0.2.7b1] — Sensore nativo scadenza ultima fattura

- Un nuovo sensore `date` **Scadenza ultima fattura** per ogni utenza, con valore derivato dal campo SOL `scadenza` della fattura emessa più di recente.
- Attributi `emissione`, `importo` totale, `stato` SOL e `tipo_importo`; nessuna deduzione automatica di saldo, debito o data del pagamento.
- Nessun nuovo endpoint o chiamata SOL, nessun cambio agli `entity_id` dei sensori esistenti e nessuna modifica alla card PDF.
- Test del tipo data nativo, dei valori reali simulati, di assenza/invalidità e della scelta per data di emissione.
- Le limitazioni privacy della versione 0.2.6 rimangono invariate.

## [0.2.6] — Prima versione stabile · documentazione e privacy

- Prima release stabile, derivata dalla beta 0.2.6b1 collaudata su Home Assistant TEST 2026.11.0 con una utenza SOL reale.
- README e guida Lovelace aggiornati con card fatture PDF e dashboard a due viste (raccolta, svuotamenti, storico e archiviazione).
- Documentati esplicitamente i limiti di accesso ai PDF da parte di qualunque utente HA autenticato, le regole di conservazione dell'archivio Media e il fallback non atomico in assenza di hard link.
- Aggiornati i riferimenti alla versione, la risorsa frontend e la pipeline per distinguere una release stabile dalle beta.
- **Nessuna modifica alla logica delle API SOL, all'accesso ai PDF, agli account o alla gestione JWT.** I limiti di sicurezza dichiarati restano aperti.

## [0.2.6b1] — PDF delle fatture (beta)

- Card fatture con visualizzatore pdf.js incluso, storico annuale e pulsanti Apri/Scarica PDF.
- Archivio locale in Media distinto per utenza, anno, numero e ID; endpoint autenticato e azione `contarina.download_invoices`.
- Test HACS, hassfest, Python, Home Assistant e browser; dettagli in [note beta](RELEASE_NOTES_0.2.6b1.md).

## [0.2.5b4] — Identità visiva per la raccolta rifiuti

- Nuova icona con **bidone dei rifiuti e simbolo del riciclo** su fondo verde, senza testo per rimanere riconoscibile nelle dimensioni piccole del frontend.
- Nuovo logo coordinato che aggiunge la dicitura **Contarina SOL**.
- Immagini PNG 256×256 verificate mediante il controllo automatico di integrità.
- Nessuna modifica ai flussi SOL, entità, JWT o automazioni.

## [0.2.5b3] — Correzione dei PNG

- Ripristinati `icon.png` e `logo.png` integri dopo la regressione di integrità nella `0.2.4b1`.
- Aggiunto il test che controlla CRC dei chunk, firma PNG, dimensioni e fine file.

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
