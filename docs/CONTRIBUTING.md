# Contributi e supporto — Contarina SOL

Contarina SOL è un'integrazione Home Assistant **non ufficiale**. Issue, test e contributi sono benvenuti; l'autore non può fornire supporto sul portale ufficiale Contarina né garantire compatibilità con utenze e browser non testati.

## Prima di aprire una issue

Leggi [README](../README.md), [FAQ](FAQ.md), [login assistito](LOGIN_ASSISTITO.md) e [privacy](PRIVACY_SICUREZZA.md). Controlla se l'errore è già stato segnalato in [Issues](https://github.com/EnrCol/ha-contarina/issues).

Per segnalare un problema, includi:

- Home Assistant Core e versione dell'integrazione (tag della release).
- Sistema/browser se il problema riguarda login, icona o smartphone.
- Modalità d'accesso a HA (locale/reverse proxy/Nabu Casa, **senza URL personali**).
- Passaggi per riprodurre, comportamento atteso e risultato osservato.
- Se possibile, codice di errore e log **completamente oscurati** dai dati sensibili.
- Se il problema è nelle fatture o nei contenitori, descrizione del tipo di utenza e delle condizioni senza identificativi personali.

**Non pubblicare mai:** JWT, password, cookie, stato/codice di abbinamento, numeri di contratto, fatture, indirizzi, screenshot finanziari e URL con token.

## Proporre modifiche

1. Apri una issue per modifiche di comportamento non banali (specie autenticazione e sicurezza).
2. Crea un branch da `main` e un pull request con lo scopo circoscritto.
3. Mantieni compatibilità con i `unique_id` esistenti: cambiare i nomi degli attributi o le entità rompe dashboard e automazioni.
4. Scrivi test per nuove logiche (Python e, per il bookmarklet, Node). Per il frontend testabile usa `tests_ha` e istanze isolate, non credenziali personali.
5. Verifica tutti i workflow GitHub: test unitari, Home Assistant, hassfest, HACS.
6. Aggiorna README, FAQ e note di release se cambia l'esperienza d'uso.

Comandi per i test offline (Python 3.14 e Node 22 dove disponibili):

```bash
python -m pip install aiohttp
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
```

I test Home Assistant richiedono anche `pytest-homeassistant-custom-component` e `playwright`; il workflow GitHub fornisce l'ambiente di riferimento. Non usare JWT reali nei test.

## Pubblicazione

Le release beta sono costruite solo quando superano i controlli della CI, come configurato in [publish-beta.yml](../.github/workflows/publish-beta.yml). L'inclusione nel catalogo generale Marketplace richiede una **pull request separata** a [hacs/default](https://github.com/hacs/default). Il solo repo pubblico è installabile direttamente da URL. Per ora non dichiarare supporto ufficiale o approvazione di Contarina S.p.A.

## Report di sicurezza

Non aprire issue pubbliche con exploit, token reali o dati privati. Verifica se il repository offre GitHub Private Vulnerability Reporting; in alternativa chiedi al maintainer un canale privato senza includere segreti nella richiesta iniziale.
