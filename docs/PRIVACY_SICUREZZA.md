# Privacy e sicurezza — Contarina SOL

**Integrazione non ufficiale** e indipendente da Contarina S.p.A. Descrizione della versione 0.2.5b2, non un'informativa di Contarina né una garanzia sulla sicurezza dei servizi esterni.

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
