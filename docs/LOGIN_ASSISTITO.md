# Login e riconnessione a Contarina SOL

**Versione:** 0.2.5b2 e successive. Il login vero avviene sempre su [SOL](https://sol.servizicontarina.it/); l'integrazione non riceve la password, non supera reCAPTCHA e non automatizza l'accesso al sito.

## Primo collegamento

1. Home Assistant → **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Contarina SOL**.
2. Scegli **Collega dal browser**.
3. Premi **Apri sito web**: si apre la pagina di collegamento. Il codice di abbinamento resta visibile nel dialogo Home Assistant.
4. La prima volta crea il preferito **Invia token a Home Assistant** dalla pagina aperta:
   - **Computer:** trascina il pulsante nella barra dei preferiti (non cliccarlo nella pagina di creazione).
   - **Telefono:** premi **Copia codice del preferito**, aggiungi ai preferiti una pagina qualsiasi, modifica il preferito sostituendone l'URL con il codice copiato. Su Chrome Android cerca poi il nome del preferito nella barra degli indirizzi mentre sei su SOL.
5. Premi **Apri Contarina SOL**, accedi con le normali credenziali e completa gli eventuali controlli del portale.
6. Sulla pagina SOL **autenticata** attiva il preferito; se browser/dispositivo sono diversi da quelli che hanno avviato il collegamento, inserisci il codice di abbinamento.
7. Home Assistant verifica il JWT con SOL; alla prima configurazione seleziona i contratti da monitorare.

Il codice vale **10 minuti ed è monouso**; se scade riavvia il flusso. Il preferito contiene solo l'indirizzo di Home Assistant, ma deve essere ricreato se cambi indirizzo (es. locale ↔ remoto). Il telefono deve poter raggiungere quell'indirizzo, preferibilmente in HTTPS.

## Riconnettere una sessione scaduta

Quando HA o SOL rimangono indisponibili abbastanza a lungo, il JWT può scadere. Home Assistant mostra una notifica persistente e una segnalazione nelle **Riparazioni**.

1. Vai in **Impostazioni → Dispositivi e servizi → Contarina SOL → ⋮ → Riconfigura**, oppure usa il collegamento nella notifica.
2. Scegli **Riconnetti dal browser**.
3. Apri SOL, accedi e riusa il preferito (se la URL di HA non è cambiata).
4. Il collegamento si completa senza ricopiare il token. Una notifica già aperta viene rimossa quando l'integrazione torna operativa.

L'integrazione tenta il rinnovo del JWT durante il normale funzionamento con intervallo intorno ai 10 minuti. Se il JWT è **già scaduto**, serve un nuovo login su SOL: non esiste una procedura autonoma con password.

## Smartphone e browser diversi

È supportato il percorso **Home Assistant su PC, SOL sul telefono**, con codice di abbinamento mostrato nel dialogo di Home Assistant. La pagina di creazione del preferito è adattata a schermi mobili, ma supporto e comportamento dei bookmarklet possono dipendere dal browser, dalla gestione degli appunti e dalle estensioni. Il collaudo del flusso da dispositivo diverso comprende test automatici e browser simulati: **non tutti i browser mobili sono stati provati con SOL reale**.

## Notifiche

La scadenza crea una notifica persistente e l'evento `contarina_session_expired`. Dalle **Opzioni** dell'integrazione puoi scegliere un servizio `notify.*` esistente per una notifica push opzionale. Il push sulla Companion App non è stato ancora collaudato su tutti i dispositivi.

Esempio di automazione (sostituisci il servizio del telefono):

```yaml
id: contarina_sessione_scaduta
alias: "Contarina - Avviso sessione scaduta"
triggers:
  - trigger: event
    event_type: contarina_session_expired
actions:
  - action: notify.mobile_app_telefono
    data:
      title: "Contarina SOL"
      message: "Sessione scaduta: apri Home Assistant per ricollegarla."
      data:
        url: /config/integrations/integration/contarina
        clickAction: /config/integrations/integration/contarina
mode: single
```

**Evita duplicazioni:** se selezioni già un servizio push nelle opzioni Contarina, questa automazione invierà un secondo avviso.

## Alternativa: incollare il JWT

Nel menu iniziale o di riconnessione seleziona **Incolla il token manualmente**. Dopo un normale login SOL puoi usare il bookmarklet **Copia token Contarina** in [tools/BOOKMARKLET.txt](../tools/BOOKMARKLET.txt) e incollare il JWT nel campo riservato di Home Assistant. Gli strumenti sviluppatore del browser sono un'ultima alternativa.

Non riportare il JWT in issue, chat, screenshot, cronologie accessibili o servizi di sincronizzazione degli appunti. Per il comportamento degli appunti consulta [privacy e sicurezza](PRIVACY_SICUREZZA.md).

## Meccanismo di sicurezza in breve

- Ogni flusso usa uno stato casuale monouso legato al config flow e valido 10 minuti, non inserito nel preferito.
- Se si usa un altro dispositivo si richiede un **codice breve monouso** con blocco temporaneo globale dopo tentativi errati.
- Il JWT passa dal browser SOL al frammento URL della pagina HA e poi tramite POST allo stesso origin; lo stato e il token sono verificati lato Home Assistant e SOL.
- La vista di ricezione richiede origine esatta (schema, host e porta) secondo le regole dei proxy fidati di Home Assistant. Per accesso remoto via Nabu Casa è previsto HTTPS.
- Il JWT viene salvato nella configurazione di Home Assistant e può finire nei backup. Usare HTTPS quando possibile.
- Nessun token viene inviato a server aggiuntivi dall'integrazione; le API di raccolta sono richieste GET a SOL.

Approfondisci in [PRIVACY_SICUREZZA.md](PRIVACY_SICUREZZA.md). Se un flusso termina in errore, riparti dal menu iniziale o consulta [FAQ](FAQ.md).
