# Contarina SOL 0.2.6b1

## Fatture PDF
- Nuova card Lovelace inclusa, `custom:contarina-invoice-card`, registrata automaticamente come risorsa: storico per anno (una sezione per utenza) con **Apri PDF** (visualizzatore in finestra, adatto all'app Companion, con pdf.js 4.10.38 incluso: nessuna CDN, funziona offline) e **Scarica PDF**. Stesso modello della card ATS.
- PDF scaricati da SOL (`GET /api/contracts/{utenza}/bill/{id}/file`) solo su richiesta, con controllo di tipo, dimensione massima (20 MB) e firma `%PDF-`.
- Archivio locale nella cartella Media di Home Assistant: `contarina/fatture/UTENZA/ANNO/NUMERO_ID.pdf`, univoco per utenza e id SOL. Creazione atomica ed esclusiva (`os.link`, ripiego `O_EXCL`): mai sovrascritture, nemmeno in concorrenza. Protezione da percorsi esterni e link simbolici. Il primo utilizzo scarica e archivia; i successivi non contattano SOL.
- Endpoint autenticato `/api/contarina/invoice/{utenza}/{id}` (anche `?download=1`): solo fatture degli account configurati e con PDF disponibile. Errori chiari per sessione SOL scaduta (409) o servizio non disponibile (503).
- Azione `contarina.download_invoices` (facoltativo `invoice_id`): archivia tutte le fatture mancanti.
- Sensore **Fatture disponibili**: lo storico include `id`, `numero`, `anno`, `pdf_disponibile`, più `utenza` e `riepilogo_annuale`; questi attributi sono esclusi dal Recorder.
- pdf.js 4.10.38 (`pdfjs-dist` da npm, Apache-2.0) in `www/pdfjs` con `LICENSE` e `SHA256SUMS`.

## Compatibilità
- Nuove dipendenze dichiarate: `frontend`, `lovelace` (oltre a `http`).
- CI: installazione del pacchetto frontend richiesto dalla versione di Home Assistant del harness.

## Test
- Unit test: percorso univoco per utenza/id, file creato tra controllo e pubblicazione, 16 scrittori concorrenti (un solo vincitore, file completo), filesystem senza hard link, pdf.js incluso con hash e card senza URL esterni, storico con identificativi, `file_esistente = -1` non considerato disponibile, validazione del PDF (stato, tipo, dimensione, firma), archivio atomico e anti-escape.
- Test Home Assistant: stesse fatture (numero e id) su due utenze senza condivisione di PDF, 8 richieste concorrenti con un solo download da SOL, visualizzatore in Chrome con ogni richiesta esterna bloccata (2 pagine renderizzate), autenticazione obbligatoria, id sconosciuti/senza PDF/malformati, scarico al primo accesso e servizio dall'archivio, Media non scrivibile, errori SOL senza dettagli, azione di download, attributi del sensore e Recorder, risorsa Lovelace.
- Collaudo su HA 2026.11.0 reale (SOL e PDF simulati in locale), con tutte le richieste esterne bloccate: card in dashboard su desktop e Pixel 7, visualizzatore con 2 pagine e navigazione, download, archivio per utenza creato, 2 sole richieste PDF a SOL, nessuna richiesta esterna.
