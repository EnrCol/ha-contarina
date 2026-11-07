# Contarina SOL — piano di collaudo e stato delle verifiche

**Riferimento:** beta 0.2.5b2, documentazione aggiornata senza variazioni alle logiche.

Legenda: **OK** = osservato nei test o sull'istanza dichiarata; **PENDENTE** = non completamente verificato; **N/D** = non coperto da dati disponibili. I test su SOL simulato non equivalgono a test live.

## Test automatici di repository

| Scenario | Stato | Fonte dell'esito |
| --- | --- | --- |
| Parser, modelli, API, soglie Secco | OK | Unit test Python su CI precedente |
| Bookmarklet (copia e riconnessione) | OK | Test Node su CI precedente |
| Config flow, reauth/reconfigure, proxy e Origin | OK | pytest-homeassistant-custom-component su ambiente isolato |
| Flussi Chrome end-to-end, stessa scheda, altra scheda e pairing | OK | Test HA con Chrome / SOL simulato |
| hassfest e validazione HACS | OK | GitHub Actions della beta 0.2.5b1 |
| Nuova release 0.2.5b2 | Da verificare | La CI deve completarsi sul nuovo commit |

L'harness disponibile nel collaudo precedente era HA **2026.10.4 / Python 3.14**; il frontend HA **2026.11.0** è stato verificato anche in un test isolato dedicato. Il valore «OK» non costituisce copertura universale.

## Prove su Home Assistant reale

| Scenario | Stato | Risultato |
| --- | --- | --- |
| Primo login browser con SOL reale | OK | Flusso completato e utenza selezionata |
| Rimozione/reinstallazione della stessa utenza | OK | 23/23 `entity_id` invariati |
| Sensori Secco e componenti nucleo | OK | Una utenza domestica da 120 L |
| Storico e totali fatture | OK | 11 documenti e totali annui disponibili |
| Calendario e confronto con ICS | OK (campione) | 25 date confrontate, tutte coincidenti |
| Notifica persistente per scadenza | OK (simulazione) | Riautenticazione e Riparazioni in test isolato |
| Browser su smartphone con SOL reale | PENDENTE | Usato iPhone simulato/Chrome test |
| Push `notify.*` su telefono reale | PENDENTE | Logica coperta da unit test |
| Servizio brand locale e icona Marketplace | PENDENTE | File PNG validi, rendering non confermato |

## Scenari non ancora coperti

- Utenze non domestiche, condominiali, più aree o molti contenitori della stessa tipologia.
- Ripresa da sessione scaduta dopo interruzioni di lunga durata su connessione instabile.
- Sessione e rinnovi continuativi per almeno 7 giorni; gestione rate limit SOL.
- Tutte le combinazioni di browser, proxy, accesso remoto Nabu Casa e app Companion.
- Confronto dell'intero storico di svuotamenti e degli stati economici con SOL.
- Fine anno, cambio tariffa/capacità del bidone, modifiche del numero componenti.
- Verifica del servizio locale delle immagini brand attraverso l'endpoint autenticato.

## Checklist per una nuova installazione

1. Verifica versione Home Assistant e release scelta dal Marketplace.
2. Avvia `Aggiungi integrazione` e completa **Collega dal browser**, senza password in HA.
3. Seleziona il contratto e controlla che le entità non risultino `unavailable`.
4. Confronta una raccolta, uno svuotamento e una fattura con SOL, senza condividere i valori privati.
5. Prova la creazione di una card solo su dashboard riservata; verifica `entity_id`.
6. Se vedi descrizioni vecchie o menu vuoti, prova refresh browser e riavvio HA Core.
7. Verifica separatamente icona **in Integrazioni** e **nel Marketplace**, riportando se HTTP 200/404 o segnaposto.
8. Conserva l'integrazione rifiuti precedente finché le automazioni non sono state confrontate.

## Release e rollback

I workflow automatici pubblicano una release beta solo se tutte le suite risultano verdi. Le release precedenti restano disponibili. In caso di problemi in una nuova beta, torna a una versione testata e verifica gli `entity_id` e i componenti, senza cancellare la config entry come prima misura. Per problemi di visualizzazione dell'icona usa la [FAQ](docs/FAQ.md), senza modifiche arbitrarie al codice SOL.
