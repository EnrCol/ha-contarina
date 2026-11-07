# Contarina SOL per Home Assistant

![Icona di Contarina SOL](custom_components/contarina/brand/icon.png)

**Integrazione non ufficiale** per consultare in Home Assistant il calendario della raccolta differenziata, i contenitori, gli svuotamenti e le fatture dello [Sportello Online Contarina (SOL)](https://sol.servizicontarina.it/).

> **Beta 0.2.5b4 · Home Assistant 2026.11 o successivo.** Progetto indipendente, non sviluppato, affiliato o approvato da Contarina S.p.A. Utilizza API SOL non pubbliche e soggette a modifica. Installa a tuo rischio; conserva i sistemi di raccolta già funzionanti fino al confronto dei dati.

[![Apri questo repository nel Marketplace di Home Assistant](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=EnrCol&repository=ha-contarina&category=integration)

## Funzionalità

- **Raccolta rifiuti:** calendario nativo, raccolte di oggi e domani, prossima raccolta.
- **Contenitori:** tipologia, capacità, svuotamenti dell'anno e data dell'ultimo svuotamento.
- **Secco:** stima del minimo annuo fatturato per una sola utenza domestica con un unico contenitore Secco attivo da 120 L: componenti SOL + 1. Gli svuotamenti **non sono gratuiti**; la composizione familiare della fattura può essere diversa da quella attuale.
- **Fatture:** ultima fattura, documenti da verificare, scadenze, storico e totale fatturato per anno. Gli importi fatturati **non sono necessariamente importi da pagare**.
- **Primo accesso e riconnessione facilitati:** login al sito ufficiale SOL, poi preferito del browser per trasferire il JWT a Home Assistant senza copiarlo manualmente. È disponibile un codice di abbinamento per un altro browser o smartphone.
- **Sessione:** rinnovo automatico del JWT mentre Home Assistant e SOL restano raggiungibili; se scade, notifica persistente, Riparazioni ed eventuale notifica push configurata.

L'integrazione legge le API SOL con richieste GET: **non paga fatture, non cambia contratti e non comanda contenitori**. Non raccoglie né salva le credenziali username/password di SOL.

## Installazione rapida

**Requisito:** Home Assistant 2026.11.0 o successivo con accesso allo Sportello Online Contarina.

1. Usa il pulsante **Marketplace** qui sopra, oppure apri **Impostazioni → Marketplace → Aggiungi da link** e inserisci `https://github.com/EnrCol/ha-contarina`.
2. Aggiungi il repository come **integrazione**, installa la release beta e riavvia Home Assistant se lo richiede.
3. Apri **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Contarina SOL (unofficial)**.
4. Seleziona **Collega dal browser** (consigliato). Nella pagina che si apre crea il preferito **Invia token a Home Assistant**, accedi a SOL e usa il preferito dalla pagina SOL autenticata.
5. Se il login avviene su un altro browser o dispositivo, inserisci il **codice di abbinamento** mostrato da Home Assistant (monouso, valido 10 minuti).
6. Seleziona le utenze da monitorare e completa la configurazione.

**Alternativa:** scegli **Incolla il token manualmente**. Non incollare mai la password al posto del JWT.

Guide: [installazione e aggiornamenti](MARKETPLACE.md) · [primo login, smartphone e riconnessione](docs/LOGIN_ASSISTITO.md) · [FAQ](docs/FAQ.md).

## Card Lovelace di esempio

Dopo l'installazione, sostituisci `CONTRATTO` con il numero presente nei tuoi `entity_id`; non usare necessariamente il nome commerciale dell'utenza.

```yaml
type: entities
title: Contarina — Raccolta rifiuti
entities:
  - entity: sensor.contarina_CONTRATTO_rifiuti_oggi
    name: Oggi
  - entity: sensor.contarina_CONTRATTO_rifiuti_domani
    name: Domani
  - entity: sensor.contarina_CONTRATTO_prossima_raccolta
    name: Prossima raccolta
  - entity: sensor.contarina_CONTRATTO_fatture_disponibili
    name: Fatture disponibili
```

Altre card, con calendario, **minimo Secco** e **tabella fatture**, sono in [DASHBOARD_EXAMPLE.md](DASHBOARD_EXAMPLE.md). Le informazioni di fatturazione dovrebbero comparire soltanto in dashboard private.

## Stato del collaudo

**Verificato su Home Assistant 2026.11 reale, con una utenza domestica:**

- Primo collegamento dal browser con SOL reale e completamento della scelta utenza.
- Rimozione e nuova configurazione: **23 entità ricreate con gli stessi `entity_id`**, e calendario/fatture/svuotamenti nuovamente disponibili.
- Storico di 11 fatture, riepiloghi annuali e stima del minimo Secco da 120 L.
- Confronto del calendario con la precedente fonte ICS per un intervallo campione: 25 date su 25 corrispondenti.

**Verificato nei test automatici / su istanza simulata:** abbinamento da altro browser, frontend Chrome, simulazione smartphone, gestione delle scadenze, controlli di origine, hassfest e HACS.

**Da verificare su più installazioni:** utenze non domestiche/condominiali, tutte le varianti di browser mobili, push Companion reale, rinnovi ininterrotti di lunga durata e comportamento su altri contratti. Il login facilitato **non sostituisce l'accesso a SOL e non aggira reCAPTCHA**.

## Limitazioni e sicurezza

- L'API SOL è privata e non documentata ufficialmente: modifiche lato Contarina possono interrompere l'integrazione.
- Il JWT è una **credenziale sensibile**, salvata nella configurazione Home Assistant e nei relativi backup. Non pubblicarla in issue, log, screenshot o chat.
- Il rinnovo avviene normalmente ogni circa 10 minuti; un JWT scaduto non può essere rinnovato senza nuova autenticazione su SOL.
- La stima Secco è disponibile solo nei casi tariffari documentati e va confrontata con la fattura ufficiale.
- Le date dei sensori sono mostrate in formato `GG-MM-AAAA`; per confronti e automazioni usa l'attributo `data_iso`.
- Le dashboard non sono installate automaticamente; gli aggiornamenti dell'integrazione possono richiedere un riavvio.
- Le immagini brand locali sono comprese nel pacchetto, ma la loro visualizzazione nel Marketplace dipende anche dal catalogo/cache Home Assistant. Consulta la [diagnostica del branding](docs/FAQ.md#licona-non-compare-nel-marketplace-o-nelle-integrazioni).

Approfondimenti: [privacy e sicurezza](docs/PRIVACY_SICUREZZA.md) · [specifica tecnica](SPEC_0_2.md) · [piano di test](TEST_PLAN.md).

## Versioni, supporto e contributi

- [Release](https://github.com/EnrCol/ha-contarina/releases) · [Changelog](CHANGELOG.md) · [Segnala un problema](https://github.com/EnrCol/ha-contarina/issues/new).
- Prima di aprire una issue leggi [FAQ](docs/FAQ.md) e [guida al contributo](docs/CONTRIBUTING.md); **non allegare JWT, dati di fatturazione o numeri di contratto reali**.
- Codice sorgente e test aperti; licenza [MIT](LICENSE).

**Contarina S.p.A. non fornisce assistenza per questa integrazione non ufficiale.**
