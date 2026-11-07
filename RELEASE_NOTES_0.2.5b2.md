# Contarina SOL 0.2.5b2 (beta)

**Aggiornamento documentale per avviare la distribuzione pubblica.** Home Assistant minimo: **2026.11.0**.

## Novità

- README aggiornato: installazione via Marketplace e collegamento diretto My Home Assistant, funzionalità, limiti, FAQ e riferimenti.
- Guida di primo login e riconnessione con preferito del browser, codice di abbinamento da smartphone e notifica opzionale.
- Nuove pagine `docs/FAQ.md`, `docs/PRIVACY_SICUREZZA.md` e `docs/CONTRIBUTING.md`.
- Esempi Lovelace, specifica tecnica e test plan riallineati alla 0.2.5b1 e alle verifiche effettuate.
- Nuovo `CHANGELOG.md`.

## Branding

- `custom_components/contarina/brand/icon.png` e `logo.png` restano nel pacchetto.
- **Problema visivo ancora aperto:** in alcune schermate l'icona non appare. La release documenta la differenza tra proxy locale di Home Assistant e indice delle immagini del catalogo Marketplace, ma non promette una correzione del frontend. Diagnostica: [FAQ](https://github.com/EnrCol/ha-contarina/blob/main/docs/FAQ.md#licona-non-compare-nel-marketplace-o-nelle-integrazioni).

## Compatibilità e sicurezza

- **Nessuna modifica al codice operativo** di login, sessione, API SOL, entità o automazioni.
- La configurazione e gli `entity_id` della precedente 0.2.5b1 rimangono invariati.
- Il JWT è una credenziale: non pubblicarlo in issue, log o screenshot.
- Beta non ufficiale; API SOL private e non garantite.

## Test richiesti per il rilascio

La pubblicazione automatica avviene soltanto dopo unit test Python, test Node, test Home Assistant con browser Chrome, hassfest e HACS.

Per l'installazione: [README](https://github.com/EnrCol/ha-contarina#readme) · [Marketplace](https://github.com/EnrCol/ha-contarina/blob/main/MARKETPLACE.md) · [Changelog](https://github.com/EnrCol/ha-contarina/blob/main/CHANGELOG.md).
