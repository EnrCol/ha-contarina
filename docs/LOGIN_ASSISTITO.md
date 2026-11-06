# Accesso assistito al portale SOL

## Metodo consigliato: collegamento dal browser (0.2.5b1)

Vale per il **primo collegamento** (*Aggiungi integrazione → Contarina SOL → Collega dal browser*), per la **riautenticazione** (notifica «sessione scaduta») e per **Riconfigura** (*Impostazioni → Dispositivi e servizi → Contarina SOL → ⋮ → Riconfigura → Riconnetti dal browser*).

1. Home Assistant mostra un **codice di abbinamento** (es. `K7P4-QXMR`) e il pulsante **Apri sito web**, che apre la pagina di collegamento.
2. **Solo la prima volta** crea il preferito *Invia token a Home Assistant*:
   - computer: trascina il pulsante nella barra dei preferiti;
   - smartphone: tocca **Copia codice del preferito**, poi crea un preferito qualsiasi e sostituiscine l'indirizzo con il codice copiato (istruzioni per iPhone e Android nella pagina).
3. Clicca **Apri Contarina SOL** e accedi: il browser può compilare le credenziali salvate.
4. Sulla pagina SOL autenticata usa il preferito. Se stai usando lo stesso browser da cui hai aperto Home Assistant il collegamento è immediato; da **un altro browser o dal telefono** la pagina chiede il codice di abbinamento mostrato da Home Assistant.
5. Home Assistant verifica il token con SOL e controlla l'account. Al primo collegamento chiede poi quali utenze monitorare; nella riautenticazione si ricollega da solo.

Esempio tipico: Home Assistant aperto sul PC, login a SOL dal telefono → sul telefono usi il preferito e inserisci il codice che vedi sul PC.

Il telefono deve raggiungere Home Assistant all'indirizzo contenuto nel preferito (rete locale o URL remoto, es. Nabu Casa).

## Avviso di sessione scaduta

Se Home Assistant resta offline più di ~45 minuti la sessione SOL scade. In quel caso l'integrazione:

- crea una **notifica persistente** con il link diretto all'integrazione (oltre alla segnalazione in *Impostazioni → Riparazioni* che Home Assistant crea da sé);
- invia, se configurato in *Opzioni → Notifica push quando la sessione scade*, una **notifica push** (es. `notify.mobile_app_telefono`) che, toccata, apre l'integrazione nell'app Companion;
- genera l'evento **`contarina_session_expired`** per automazioni personalizzate:

```yaml
- id: contarina_sessione_scaduta
  alias: "Contarina - Avviso sessione scaduta"
  triggers:
    - trigger: event
      event_type: contarina_session_expired
  actions:
    - action: notify.mobile_app_telefono
      data:
        title: "Contarina SOL"
        message: "Sessione scaduta: tocca per riconnettere."
        data:
          url: /config/integrations/integration/contarina
          clickAction: /config/integrations/integration/contarina
```

L'avviso viene inviato una sola volta per scadenza e si azzera quando l'integrazione torna operativa.

Sicurezza:

- Il preferito contiene **solo l'indirizzo** del tuo Home Assistant, nessun segreto.
- Nello stesso browser il collegamento è autorizzato da un codice casuale monouso (256 bit), legato al singolo flusso avviato in Home Assistant, valido 10 minuti e salvato solo nel browser che l'ha avviato (nella scheda, con ripiego per flusso se usi il preferito in un'altra scheda). Dopo 5 tentativi errati viene annullato.
- Da un altro browser o dispositivo serve il codice di abbinamento: 8 caratteri (~40 bit), visibile solo nell'interfaccia di Home Assistant e nella pagina aperta da essa, monouso, valido 10 minuti. Dopo 10 codici errati (su tutti i flussi) l'inserimento viene bloccato per 10 minuti, rendendo impraticabile qualsiasi tentativo di indovinarlo.
- La consegna del token è accettata solo da pagine con la stessa origine di Home Assistant: schema (http/https), host e porta devono coincidere (header `Origin`). Dietro reverse proxy valgono solo le intestazioni `X-Forwarded-*` dei proxy configurati come fidati in Home Assistant (`use_x_forwarded_for`, `trusted_proxies`).
- L'indirizzo della pagina di riconnessione è quello da cui stai usando Home Assistant (header `HA-Frontend-Base`, come per i login OAuth); in mancanza si usa l'URL configurato in *Impostazioni → Sistema → Rete*.
- Il token passa dalla pagina SOL a Home Assistant nella parte dell'indirizzo dopo `#`, che non viene inviata in rete; la pagina di Home Assistant lo cancella subito dalla barra degli indirizzi e lo consegna con una richiesta allo stesso indirizzo.
- Usa Home Assistant in **HTTPS** quando possibile. In HTTP il token viaggia in chiaro sulla rete locale, esattamente come quando lo incolli nel modulo.
- Il preferito va ricreato se apri Home Assistant da un indirizzo diverso (es. IP locale e URL remoto).
- Se qualcosa non va, il flusso passa automaticamente al copia-incolla.

## Metodo alternativo: copia-incolla

L'integrazione Home Assistant non acquisisce username/password e non prova a eseguire reCAPTCHA. Il primo JWT si ottiene esclusivamente **dopo un login normale sul sito ufficiale Contarina SOL**.

### Preferito «Copia token Contarina»

1. Apri [https://sol.servizicontarina.it/](https://sol.servizicontarina.it/) e accedi normalmente.
2. Crea un nuovo preferito nel browser e chiamalo **Copia token Contarina**.
3. Modifica l'**indirizzo/URL** del preferito: incolla **l'intera riga** contenuta in [`tools/BOOKMARKLET.txt`](../tools/BOOKMARKLET.txt), incluso `javascript:` iniziale. Non inserire l'indirizzo in una ricerca web.
4. Mentre sei ancora sulla pagina autenticata di **sol.servizicontarina.it**, clicca il preferito. Se il token è visibile alla pagina ed è valido, il browser conferma la copia negli appunti.
5. Apri **Impostazioni → Dispositivi e servizi → Contarina SOL** di Home Assistant e incolla il token nel campo richiesto (anche nella procedura di riautenticazione).

Il bookmarklet copia il token **solo negli appunti locali**, non lo invia a server. Controlla sempre che il codice letto dal preferito provenga dal [repository ufficiale del progetto](https://github.com/EnrCol/ha-contarina) e non da link di sconosciuti.

Se il browser impedisce la copia, viene offerto un campo per **copia manuale**. Non lasciare il token visibile sullo schermo e non copiarlo in chat, issue o screenshot. Ricorda che gli appunti possono essere sincronizzati con altri dispositivi: cancella il token dagli appunti dopo averlo incollato in Home Assistant.

## Esiti ancora da verificare

- Verificato su sessione reale: `accessToken` è non-HttpOnly e leggibile con `document.cookie` dalla pagina SOL.
- Alcuni browser o estensioni possono bloccare i bookmarklet oppure l'API degli appunti.
- Il token scade dopo circa **55 minuti** e non può essere rinnovato una volta scaduto. Se il bookmarklet segnala sessione scaduta, riesegui il login su SOL.
- Non è un login automatico persistente: la funzione è **solo un ausilio per copiare il token** dopo l'autenticazione effettuata dall'utente.

## Sicurezza

Il codice [`tools/contarina_token_bookmarklet.js`](../tools/contarina_token_bookmarklet.js) rifiuta qualsiasi pagina diversa da `https://sol.servizicontarina.it`, cerca esclusivamente il cookie `accessToken`, verifica la presenza di un JWT e che restino almeno due minuti di validità. Non usa `fetch`, `XMLHttpRequest`, `sendBeacon`, storage, server esterni o logging del token. **Non verifica la firma crittografica**: questa verifica viene demandata al backend SOL quando Home Assistant utilizza il token.

Il codice del preferito è stato testato con JWT **fittizi**, non con credenziali reali. La procedura tradizionale che recupera manualmente il cookie dagli strumenti sviluppatore resta il fallback.
