# Contarina SOL v0.2.6 · Prima release stabile

Questa versione promuove la beta **v0.2.6b1**, collaudata con Home Assistant TEST 2026.11.0 e un account Contarina SOL reale. **La logica di lettura SOL, JWT, fatture e PDF è invariata.**

## Novità della versione stabile

- README e [dashboard completa d'esempio](DASHBOARD_EXAMPLE.md) aggiornati: raccolte, svuotamenti, riepiloghi annuali, card `custom:contarina-invoice-card` e azione `contarina.download_invoices`.
- Guida per il primo collegamento aggiornata, incluso l'utilizzo dei Preferiti in Safari.
- [Privacy e sicurezza](docs/PRIVACY_SICUREZZA.md) resa esplicita: JWT e dati SOL in Home Assistant, endpoint PDF autenticato ma **non limitato agli amministratori**, PDF nella cartella Media e nei backup, assenza di cancellazione automatica.
- Aggiornamento del numero di versione e della URL cache della card; workflow di rilascio aggiornato per pubblicare **release stabili senza flag prerelease**.

## Funzioni già presenti dalla beta v0.2.6b1

- Sensori raccolta, contenitori, svuotamenti e fatturazione annuale.
- Card PDF con archivio per utenza/anno/fattura, pulsanti Apri e Scarica, visualizzatore pdf.js 4.10.38 incorporato e nessuna dipendenza CDN.
- Download su richiesta dei PDF mancanti tramite `contarina.download_invoices`.
- Login e riconnessione dal browser mediante preferito; nessuna password SOL memorizzata dall'integrazione.

## Sicurezza: limitazioni note non corrette in questa versione

- **Accesso ai documenti:** qualsiasi utente HA autenticato può richiedere PDF delle utenze caricate, se ne conosce gli identificativi; il ruolo amministratore non è controllato dall'endpoint. Non affidarti alla sola visibilità della dashboard come barriera.
- **Filesystem senza hard link:** il ripiego `O_EXCL` impedisce sovrascritture ma scrive sul percorso finale; non offre pubblicazione atomica per lettori concorrenti e usa modalità file `0644` prima di umask/ACL.
- **Conservazione:** PDF, backup e cronologie precedenti non vengono rimossi automaticamente con la disinstallazione.

**Non è una release di sicurezza.** Per dati sensibili, usare esclusivamente istanze HA con accesso controllato. Consulta la [guida privacy](docs/PRIVACY_SICUREZZA.md).

## Test e compatibilità

- Home Assistant **2026.11.0 o successivo**.
- Beta v0.2.6b1: test automatici Python, frontend/browser, Home Assistant, HACS e hassfest superati.
- TEST reale: connessione SOL riuscita, sensori e storico (11 fatture) disponibili, card dichiarata funzionante durante il collaudo.
- La pipeline di questa release deve superare di nuovo tutti i controlli prima della pubblicazione.

Integrazione indipendente e non ufficiale; non affiliata a Contarina S.p.A. L'API SOL non è pubblica e può cambiare.
