# Accesso assistito al portale SOL (prototipo)

L'integrazione Home Assistant non acquisisce username/password e non prova a eseguire reCAPTCHA. Il primo JWT si ottiene esclusivamente **dopo un login normale sul sito ufficiale Contarina SOL**.

## Metodo sperimentale: preferito «Copia token Contarina»

1. Apri [https://sol.servizicontarina.it/](https://sol.servizicontarina.it/) e accedi normalmente.
2. Crea un nuovo preferito nel browser e chiamalo **Copia token Contarina**.
3. Modifica l'**indirizzo/URL** del preferito: incolla **l'intera riga** contenuta in [`tools/BOOKMARKLET.txt`](../tools/BOOKMARKLET.txt), incluso `javascript:` iniziale. Non inserire l'indirizzo in una ricerca web.
4. Mentre sei ancora sulla pagina autenticata di **sol.servizicontarina.it**, clicca il preferito. Se il token è visibile alla pagina ed è valido, il browser conferma la copia negli appunti.
5. Apri **Impostazioni → Dispositivi e servizi → Contarina SOL** di Home Assistant e incolla il token nel campo richiesto (anche nella procedura di riautenticazione).

Il bookmarklet copia il token **solo negli appunti locali**, non lo invia a server. Controlla sempre che il codice letto dal preferito provenga dal [repository ufficiale del progetto](https://github.com/EnrCol/ha-contarina) e non da link di sconosciuti.

Se il browser impedisce la copia, viene offerto un campo per **copia manuale**. Non lasciare il token visibile sullo schermo e non copiarlo in chat, issue o screenshot. Ricorda che gli appunti possono essere sincronizzati con altri dispositivi: cancella il token dagli appunti dopo averlo incollato in Home Assistant.

## Esiti ancora da verificare

- Il cookie `accessToken` è indicato dal codice del frontend SOL come non-HttpOnly, **ma l'accesso con `document.cookie` va ancora testato sul browser reale**.
- Alcuni browser o estensioni possono bloccare i bookmarklet oppure l'API degli appunti.
- Il token scade dopo circa **55 minuti** e non può essere rinnovato una volta scaduto. Se il bookmarklet segnala sessione scaduta, riesegui il login su SOL.
- Non è un login automatico persistente: la funzione è **solo un ausilio per copiare il token** dopo l'autenticazione effettuata dall'utente.

## Sicurezza

Il codice [`tools/contarina_token_bookmarklet.js`](../tools/contarina_token_bookmarklet.js) rifiuta qualsiasi pagina diversa da `https://sol.servizicontarina.it`, cerca esclusivamente il cookie `accessToken`, verifica la presenza di un JWT e che restino almeno due minuti di validità. Non usa `fetch`, `XMLHttpRequest`, `sendBeacon`, storage, server esterni o logging del token. **Non verifica la firma crittografica**: questa verifica viene demandata al backend SOL quando Home Assistant utilizza il token.

Il codice del preferito è stato testato con JWT **fittizi**, non con credenziali reali. La procedura tradizionale che recupera manualmente il cookie dagli strumenti sviluppatore resta il fallback.