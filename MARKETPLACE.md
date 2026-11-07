# Installazione e distribuzione — Contarina SOL

Versione documentata: **0.2.5b2 (beta)**. Requisito minimo **Home Assistant 2026.11.0**. Integrazione indipendente e non ufficiale.

## Installare dal Marketplace

[![Apri nel Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=EnrCol&repository=ha-contarina&category=integration)

1. In **Impostazioni → Marketplace**, scegli **Aggiungi da link** se il repository non compare nella ricerca.
2. Inserisci `https://github.com/EnrCol/ha-contarina`, categoria **Integrazione**.
3. Installa la release più recente, dopo averne letto le [note](https://github.com/EnrCol/ha-contarina/releases).
4. Riavvia Home Assistant quando richiesto, in particolare dopo gli aggiornamenti di un'integrazione già caricata.
5. Apri **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Contarina SOL (unofficial)**.
6. Seleziona **Collega dal browser**, esegui normalmente il login al portale SOL, usa il preferito **Invia token a Home Assistant** e scegli le utenze.

Il collegamento dal browser esiste anche al **primo accesso**. Da uno smartphone o altro browser si usa il codice di abbinamento mostrato da Home Assistant. [Guida dettagliata](docs/LOGIN_ASSISTITO.md).

### Aggiornamento

Marketplace → Installati → Contarina SOL → **Aggiorna**, se disponibile. Conserva una copia di sicurezza della configurazione secondo le tue normali procedure e verifica la richiesta di riavvio. Dopo l'aggiornamento verifica **Dispositivi e servizi**, le entità, le raccolte, gli svuotamenti e le fatture; una descrizione o etichette del vecchio config flow possono dipendere dalla cache delle traduzioni, per cui prova un refresh del browser e poi un riavvio Core se necessario.

### Rimozione e ripristino

Per rimuovere: **Impostazioni → Dispositivi e servizi → Contarina → Elimina**. La rimozione cancella l'entry e le entità; le card che le usano restano con riferimenti mancanti. L'integrazione non elimina automaticamente dashboard o automazioni personalizzate. La reinstallazione con lo stesso account/contratti **può** riottenere gli stessi ID, ma non è garantito per ogni configurazione: prima conserva una mappatura delle entità. Per tornare a una release precedente utilizza la cronologia delle [release GitHub](https://github.com/EnrCol/ha-contarina/releases); eventuali modifiche alla struttura dei dati richiedono verifica prima di utilizzare le vecchie dashboard.

## Distribuzione pubblica

Questo repository è **pubblico** e installabile già da URL. Per comparire nella ricerca generale del Marketplace/HACS deve essere incluso nel catalogo [`hacs/default`](https://github.com/hacs/default) tramite pull request soggetta a revisione e tempi di attesa; la semplice creazione di una GitHub Release non equivale all'ammissione nel catalogo. I workflow del repository includono test Python, Node, Home Assistant, hassfest e validazione HACS.

Per i passi ufficiali: [Home Assistant — Get into the catalog](https://contributors.home-assistant.io/marketplace/guides/catalog/).

## Icone: due meccanismi distinti

- **Integrazione installata:** Home Assistant 2026.11 carica le immagini da `custom_components/contarina/brand/icon.png` e `logo.png`, servite tramite `/api/brands/integration/contarina/icon.png`.
- **Marketplace:** per le integrazioni del catalogo, le immagini sono sincronizzate dalle release sul servizio brands. Un repository **aggiunto manualmente da link** potrebbe non comparire nel catalogo delle immagini; questo non indica che il PNG non sia nel pacchetto.

I file brand sono PNG e inclusi nella release. La loro presenza è verificata, **non** la corretta visualizzazione su ogni frontend. Se non vedi l'icona anche dopo riavvio e refresh, segui [FAQ — icona assente](docs/FAQ.md#licona-non-compare-nel-marketplace-o-nelle-integrazioni), distinguendo tra mancanza del file, 404 del proxy brand e segnaposto del catalogo. Non aggiungere ripetutamente copie degli stessi PNG per risolvere un problema del servizio che li visualizza.

## Privacy e assistenza

SOL non è un'API pubblica e Home Assistant conserva un JWT di accesso; non condividerlo. Questa integrazione è indipendente da Contarina S.p.A. Per i problemi tecnici usa [le issue GitHub](https://github.com/EnrCol/ha-contarina/issues/new) dopo aver letto [privacy](docs/PRIVACY_SICUREZZA.md) e [FAQ](docs/FAQ.md).
