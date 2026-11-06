## Contarina SOL 0.2.3b1 (beta)

### Miglioramenti
- Ripristinata l'icona della community integration (C bianca su verde), `custom_components/contarina/brand/icon.png`.
- README aggiornato con installazione Marketplace, stato di collaudo verificato, limitazioni e card Lovelace di esempio.
- Esempi aggiuntivi per calendario, svuotamenti Secco e tabella storica delle fatture.
- Prototipo opzionale di bookmarklet per copiare **localmente** `accessToken` dopo il normale login SOL, con documentazione e test unitari sintetici. Nessuna modifica al config flow e nessun login automatico.

### Limiti
- Il bookmarklet non è ancora stato verificato su un browser autenticato reale; il cookie potrebbe non essere visibile in alcune configurazioni.
- Un JWT scaduto non può essere rinnovato; dopo un'interruzione superiore al tempo residuo serve riautenticarsi via browser.
- La visualizzazione delle icone nel Marketplace può essere soggetta a cache e a limiti del frontend.

Nessun cambiamento alle entità esistenti, al calendario o all'interfaccia API della versione 0.2.2b1.