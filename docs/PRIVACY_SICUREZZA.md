# Privacy e sicurezza — Contarina SOL

**Integrazione non ufficiale** e indipendente da Contarina S.p.A. Descrizione della versione 0.2.7 stabile (stessa gestione JWT/PDF della 0.2.6, più un sensore nativo per la scadenza della fattura più recente), non un'informativa di Contarina né una garanzia sulla sicurezza dei servizi esterni.

## Dati trattati

- **JWT di accesso SOL:** necessario a interrogare il portale e a mantenerne la sessione. È una credenziale sensibile; Home Assistant lo memorizza nella propria configurazione delle integrazioni e lo aggiorna durante il rinnovo. I backup della configurazione possono contenerlo.
- **Dati dell'utenza:** contratti selezionati, quantità/componenti, calendari, codici contenitore, date e conteggi degli svuotamenti, informazioni di fatturazione e pagamenti presentate da SOL. Questi dati sono visibili in entità e attributi, comprese le dashboard a cui l'utente concede accesso.
- **Codici temporanei di abbinamento:** mantenuti in memoria nel processo di Home Assistant durante il flusso, non come credenziali riutilizzabili.

## Destinazioni e richieste

L'integrazione interroga **SOL** (server del gestore) con richieste GET e autorizzazione Bearer tramite JWT. Non invia credenziali a server dell'autore dell'integrazione e non implementa tracking o telemetria propri. Per installazione/aggiornamento il Marketplace può usare i propri servizi GitHub e catalogo, indipendenti dal traffico dell'integrazione. Le notifiche push sono delegate ai servizi `notify.*` configurati dall'utente, che possono coinvolgere fornitori di notifiche esterni.

## Primo login e riconnessione

- Username, password e reCAPTCHA vengono gestiti **solo nel sito ufficiale SOL**.
- Il preferito **Invia token a Home Assistant** contiene l'indirizzo scelto per Home Assistant, non un JWT fisso.
- La pagina SOL autenticata legge il JWT dal cookie `accessToken`, quindi apre il percorso Home Assistant con il JWT nel **frammento** `#` dell'URL, non spedito nella richiesta HTTP iniziale. La pagina di ricezione cancella il frammento e usa una richiesta POST all'origine di HA.
- Il server controlla **schema, host e porta** dell'`Origin` con le informazioni risolte da Home Assistant (inclusi i soli proxy fidati). Il token viene validato con SOL. Lo stato monouso vale 10 minuti, ed esiste un limite ai tentativi di abbinamento.
- Un accesso remoto deve usare **HTTPS**; su HTTP locale i dati possono transitare senza cifratura. Un token valido dà accesso ai dati SOL, perciò va trattato come una password.
- Il preferito alternativo **Copia token Contarina** usa gli appunti locali; alcuni servizi e dispositivi possono sincronizzarli. Evita la sincronizzazione di credenziali e cancella gli appunti dopo l'uso.

## Log, diagnostica, conservazione

L'implementazione delle API evita intenzionalmente di registrare URL, corpi di risposta e token. La diagnostica dell'integrazione espone **conteggi aggregati e stati booleani**, non i dettagli di fatture o i valori del JWT. I normali registri e backup di Home Assistant sono gestiti da Home Assistant e dalle configurazioni scelte dall'utente.

Gli attributi dei sensori e lo storico di Home Assistant possono conservare dati economici e informazioni personali anche dopo che il portale SOL li ha aggiornati. L'integrazione non controlla i criteri di conservazione del database Home Assistant e non elimina automaticamente cronologie o backup quando viene disinstallata.

## Buone pratiche prima di segnalare problemi

1. Non pubblicare **JWT, codici di abbinamento, password, header `Authorization`**, screenshot di fatture o dettagli di contratto.
2. Oscura numeri di contratto e nomi quando condividi immagini di dashboard.
3. Non dare accesso pubblico a dashboard finanziarie o a pagine che espongano il codice temporaneo.
4. Mantieni aggiornati Home Assistant, il componente e i browser; limita gli accessi amministrativi.
5. Se ritieni compromesso un JWT, effettua nuovamente il login a SOL e verifica le modalità di revoca disponibili dal gestore; non presumere che la disinstallazione da Home Assistant lo revochi lato SOL.

## Limitazioni e vulnerabilità

Le API SOL sono non pubbliche, possono cambiare e non hanno garanzie di compatibilità. Non è noto il limite assoluto di rinnovi consecutivi. La firma del JWT viene verificata **dal servizio SOL** quando il token viene usato; il bookmarklet verifica soltanto formato e scadenza apparente.

Per vulnerabilità sensibili evita di pubblicare dettagli sfruttabili in issue aperte; usa una segnalazione privata GitHub, se disponibile, oppure contatta il maintainer tramite un canale privato concordato. Consulta anche [FAQ](FAQ.md).

## PDF delle fatture (0.2.6)

- I PDF sono scaricati da SOL solo su richiesta esplicita (pulsante della card o azione `contarina.download_invoices`), mai dall'aggiornamento periodico.
- Sono salvati in locale in `media/contarina/fatture/UTENZA/ANNO/NUMERO_ID.pdf` (univoco per utenza e identificativo SOL). Il normale percorso con hard link pubblica il file completo senza sovrascriverne uno esistente. **Limitazione nota:** nel fallback per filesystem senza hard link, il file finale è aperto con `O_EXCL` e scritto direttamente: resta protetto dalla sovrascrittura, ma un lettore contemporaneo può osservare un file incompleto. Questo fallback non offre la stessa garanzia di pubblicazione atomica.
- **Permessi filesystem:** il fallback usa permessi `0644` (soggetti a umask/ACL); su sistemi multiutente gli accessi devono essere protetti anche da permessi delle directory e del volume. Non considerare la directory Media un deposito cifrato o privato per il solo fatto di trovarsi in Home Assistant.
- **Conservazione:** i PDF scaricati non vengono eliminati automaticamente alla rimozione dell'integrazione o dell'utenza; possono inoltre rimanere nei backup. La cancellazione dei documenti archiviati e delle copie di backup spetta all'amministratore.
- Il visualizzatore usa pdf.js 4.10.38 (Apache-2.0) incluso nell'integrazione (`www/pdfjs`, hash SHA-256 verificati dai test), servito da Home Assistant: nessun codice di terze parti caricato da CDN, `isEvalSupported` disattivato.
- L'endpoint `/api/contarina/invoice/{utenza}/{id}` richiede un utente Home Assistant **autenticato**, ma **non controlla il ruolo amministratore e non applica permessi per singola utenza**: un utente HA autenticato può potenzialmente leggere le fatture di qualsiasi account SOL caricato nell'istanza, se ne conosce o ricava utenza e identificativo. Gli ID delle fatture sono presenti negli attributi correnti dei sensori. Limitare una dashboard agli amministratori **non limita l'accesso diretto all'endpoint**. Non concedere accesso all'istanza a utenti che non devono poter consultare questi dati; valuta una istanza separata. Il server rifiuta percorsi fuori dall'archivio e link simbolici e serve solo fatture dei contratti caricati.
- Gli attributi dello storico usati dalla card (numero, ID, importi, riepilogo annuale, codice utenza) sono esclusi dal Recorder; **rimangono tuttavia nello stato corrente** e sono esposti agli utenti HA con accesso agli stati. Il Recorder può aver già conservato dati di versioni precedenti: l'aggiornamento non rimuove lo storico precedente.
- Il codice dell'integrazione evita di scrivere token, URL SOL, identificativi e contenuti dei documenti nei propri log ed errori; non controlla eventuali log di proxy, server o strumenti di debug esterni.

## Limiti della verifica e responsabilità dell'installazione

I test automatizzati coprono validazione PDF, limiti di dimensione, accesso autenticato, concorrenza e percorsi fuori archivio. Il collaudo reale ha verificato il caricamento dell'integrazione e della card su Home Assistant TEST con un account SOL; **non equivale a un audit indipendente di sicurezza**. Le limitazioni di autorizzazione e fallback filesystem sopra indicate restano presenti nella stabile 0.2.7: rispetto alla beta 0.2.7b1, questa release non modifica il codice runtime.

Per dati sensibili valuta una istanza HA dedicata e proteggi accesso, cartella Media, file di backup ed eventuali esportazioni. Se non puoi garantire che tutti gli utenti autenticati siano autorizzati a vedere le fatture, **non attivare la funzionalità PDF su quell'istanza**.
