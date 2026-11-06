# Contarina SOL per Home Assistant

![Icona Contarina SOL (integrazione non ufficiale)](custom_components/contarina/brand/icon.png)

**Integrazione indipendente e non ufficiale** per consultare calendario rifiuti, contenitori, svuotamenti e fatture dello Sportello Online Contarina (SOL). Non è sviluppata né approvata da Contarina S.p.A.

> **Beta 0.2.3b1.** Testata con Home Assistant 2026.11 su un'utenza domestica reale. Il calendario è stato confrontato con l'integrazione ICS esistente (25 date su 25 coincidenti nel periodo verificato). Mancano test estesi su utenze non domestiche, condominiali e durata massima della sessione.

## Funzionalità

- Configurazione grafica con selezione di uno o più contratti SOL.
- Calendario Home Assistant nativo, rifiuti di oggi/domani e prossima raccolta.
- Contenitori, svuotamenti annui e ultimo svuotamento registrato.
- Stima del **minimo annuale addebitato per il Secco** su utenze domestiche con un solo contenitore da 120 L: componenti del nucleo + 1; dati negli attributi del sensore svuotamenti esistente. La stima non significa prese gratuite e va confrontata con la composizione familiare presa a riferimento da Contarina.
- Fatture, scadenze, classificazioni SOL, storico nell'attributo `storico_fatture` di *Fatture disponibili* e totale fatturato per anno. **L'importo della fattura non è un residuo da pagare verificato**.
- JWT rinnovato automaticamente ogni 15 minuti e salvato nella configurazione protetta di Home Assistant.
- Operazioni HTTP **solo GET**; nessuna modifica ai contratti o ai pagamenti.

## Installazione da Marketplace

1. In Home Assistant 2026.11+, apri **Impostazioni → Marketplace → Aggiungi da link**.
2. Inserisci `https://github.com/EnrCol/ha-contarina` come repository personalizzato.
3. Installa **Contarina SOL (unofficial)**; riavvia Home Assistant se richiesto.
4. Apri **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Contarina SOL**.
5. Accedi a [SOL](https://sol.servizicontarina.it/) nel tuo browser e inserisci un **JWT `accessToken` recente** nella configurazione privata di Home Assistant. Seleziona i contratti da monitorare.

**Non inserire mai il token o le credenziali in issue GitHub, chat, screenshot o file pubblici.** Il token è una credenziale di accesso e contiene anche dati personali.

### Accesso assistito (sperimentale)

**Riconnessione senza copia-incolla (0.2.4b1):** *Riconfigura → Riconnetti dal browser* apre SOL; dopo il login un preferito invia il token direttamente a Home Assistant con un codice monouso. Dettagli in [LOGIN_ASSISTITO.md](docs/LOGIN_ASSISTITO.md).

Per evitare gli strumenti sviluppatore c'è anche un **bookmarklet**: un preferito eseguito *solo sulla pagina SOL già autenticata*, che legge il cookie `accessToken` e lo copia negli appunti senza inviarlo ad altri siti. Prima dell'uso leggi [LOGIN_ASSISTITO.md](docs/LOGIN_ASSISTITO.md) e il [codice leggibile](tools/contarina_token_bookmarklet.js).

Su una sessione SOL reale è stato verificato che `document.cookie` espone `accessToken` (cookie non HttpOnly). La copia negli appunti del bookmarklet dipende dal browser; se viene bloccata resta la copia manuale o la procedura DevTools. Non è supportato il login automatico con username/password né un bypass di reCAPTCHA.

Il JWT dura circa **55 minuti** e SOL **non rinnova un token già scaduto** (HTTP 401). Home Assistant lo rinnova ogni 10 minuti mentre è online, quindi il residuo resta sempre di almeno ~45 minuti.

- Riavvii, aggiornamenti e brevi interruzioni di rete (fino a ~45 minuti): nessun intervento.
- Home Assistant spento o offline più a lungo: compare la richiesta di riautenticazione; accedi su SOL e incolla un nuovo token (bookmarklet).

SOL non usa refresh token, sessioni lato server o cookie di rinnovo: l'unica credenziale è il JWT (verificato). La durata massima assoluta dei rinnovi concatenati non è ancora nota.

## Card Lovelace di esempio

Questa card usa solo entità Contarina già esistenti. Sostituisci `CONTRACT` con il suffisso della tua utenza, leggibile da **Impostazioni → Dispositivi e servizi → Contarina → Entità**.

```yaml
type: entities
title: Raccolta Contarina
entities:
  - entity: sensor.contarina_CONTRACT_rifiuti_oggi
    name: Oggi
  - entity: sensor.contarina_CONTRACT_rifiuti_domani
    name: Domani
  - entity: sensor.contarina_CONTRACT_prossima_raccolta
    name: Prossima raccolta
  - entity: sensor.contarina_CONTRACT_fatture_disponibili
    name: Fatture nello storico
```

Per una card più completa, inclusi il **contatore Secco** e la **tabella dello storico fatture**, consulta [DASHBOARD_EXAMPLE.md](DASHBOARD_EXAMPLE.md). La tabella dei dati finanziari dovrebbe essere usata solo in dashboard private o riservate agli amministratori.

## Note e limiti

- L'API SOL non è pubblica e può cambiare senza preavviso.
- La fatturazione non determina un saldo esigibile certo; verificare sul portale Contarina.
- Le date visualizzate nei sensori *Prossima raccolta* e *Ultimo svuotamento* sono testuali `GG-MM-AAAA`; il formato ISO è nell'attributo `data_iso` per automazioni e confronti.
- Per il minimo Secco valgono soltanto i casi verificati: utenza domestica, singolo contenitore Secco attivo da 120 L, dati dei componenti e svuotamenti validi.
- È consigliato mantenere attiva la vecchia integrazione rifiuti finché tutte le automazioni e le notifiche non siano state migrate e confrontate.
- Il download HACS sostituisce i file dell'integrazione; le dashboard create manualmente in Home Assistant non sono installate automaticamente.

## Sviluppo e verifiche

Test Python: `python -m pip install aiohttp && python -m unittest discover -s tests -v`.

Test bookmarklet: `node --test tests/bookmarklet.test.mjs`.

La CI verifica inoltre hassfest e HACS. Vedi [specifica 0.2](SPEC_0_2.md), [piano di collaudo](TEST_PLAN.md) e [note di rilascio](RELEASE_NOTES_0.2.3b1.md).

Licenza: MIT.
