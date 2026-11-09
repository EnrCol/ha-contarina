# Contarina SOL v0.2.7 — Stabile: scadenza ultima fattura

Questa versione promuove la beta **v0.2.7b1** dopo il collaudo su Home Assistant TEST. **Nessuna modifica alle logiche runtime** della beta: lettura SOL, gestione JWT, archivio PDF e card PDF rimangono invariati.

## Sensore Scadenza ultima fattura

- Un sensore nativo Home Assistant **`device_class: date`** per ogni utenza SOL configurata.
- Stato **ISO `YYYY-MM-DD`**, ottenuto dal campo SOL `scadenza` della fattura più recente per **data di emissione**.
- Attributi `emissione` (data ISO), `importo` (totale fattura, non residuo), `stato` (classificazione SOL) e `tipo_importo`.
- Non vengono inventate scadenze se il campo SOL è assente o non valido.
- Nessun cambiamento agli identificativi dei sensori esistenti; nessuna nuova chiamata API SOL.

**Nota:** la scadenza dell'ultima fattura **non** è necessariamente la prossima scadenza non pagata. Stato `due` e importo totale non costituiscono da soli una conferma del debito residuo o del pagamento.

## Dashboard ed esempi

- [README](README.md): esempio di card Markdown che riepiloga le scadenze di tutte le utenze senza identificativi privati.
- [Guida dashboard](DASHBOARD_EXAMPLE.md): esempio a **due tile (scadenza e importo)** più dettagli emissione/stato e dashboard completa con sezione scadenze.
- Card personalizzata `custom:contarina-invoice-card` inclusa **senza modifiche** rispetto alla beta.

## Collaudo e validazioni

- Home Assistant **2026.11.0 TEST**, integrazione beta caricata, nuovo sensore nativo `date` disponibile, attributi emissione/importo/stato verificati con SOL e sezione di collaudo Lovelace aggiunta e riletta dopo il salvataggio.
- Nessun errore Contarina riscontrato nei log dell'istanza TEST durante la verifica.
- Verifiche automatizzate GitHub: unit test Python, test Home Assistant/browser, HACS e hassfest; la pubblicazione stabile è subordinata al loro successo sul commit di release.

## Privacy e limiti invariati

- L'endpoint PDF richiede autenticazione HA, **non** autorizzazione amministratore.
- I PDF archiviati nella cartella Media e nei backup non sono cancellati automaticamente.
- Il fallback per filesystem senza hard link conserva le limitazioni di permessi e atomicità descritte nella [guida privacy](docs/PRIVACY_SICUREZZA.md).

**Non è una release di sicurezza.** Integrazione indipendente e non ufficiale, non affiliata a Contarina S.p.A. Le API SOL non sono pubbliche e possono cambiare.
