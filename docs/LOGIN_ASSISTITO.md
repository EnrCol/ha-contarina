# Accesso assistito al portale SOL

## Metodo consigliato: «Riconnetti dal browser» (0.2.4b1)

Da **Impostazioni → Dispositivi e servizi → Contarina SOL → ⋮ → Riconfigura** (oppure dalla notifica di riautenticazione) scegli **Riconnetti dal browser**:

1. Home Assistant apre una pagina di riconnessione. **Solo la prima volta** trascina il pulsante *Invia token a Home Assistant* nella barra dei preferiti.
2. Clicca **Apri Contarina SOL** e accedi: il browser può compilare le credenziali salvate.
3. Sulla pagina SOL autenticata clicca il preferito *Invia token a Home Assistant*. Home Assistant verifica il token con SOL, controlla che appartenga allo stesso account e si ricollega. Nessun copia-incolla.

Sicurezza:

- Il preferito contiene **solo l'indirizzo** del tuo Home Assistant, nessun segreto.
- La riconnessione è autorizzata da un codice casuale monouso (256 bit), legato al singolo flusso avviato in Home Assistant, valido 10 minuti e salvato solo nel browser che l'ha avviata (nella scheda, con ripiego per flusso se usi il preferito in un'altra scheda). Dopo 5 tentativi errati viene annullato.
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
