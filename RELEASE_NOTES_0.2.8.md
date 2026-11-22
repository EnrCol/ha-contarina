# Contarina SOL v0.2.8 — Correzione: riconnessione dal browser più affidabile

Versione di sola correzione. Lettura SOL, gestione JWT, sensori, archivio PDF e card restano invariati rispetto alla **v0.2.7**.

## Correzione

- La pagina che riceve il token dal preferito leggeva solo la parte del corpo della richiesta già arrivata. Se il token arrivava in più pacchetti (connessione lenta, proxy, accesso remoto), la riconnessione poteva fallire con «Richiesta non valida». Ora il corpo viene letto fino alla fine.
- Gli invii scartati vengono annotati nel log di Home Assistant con il motivo e la dimensione, **mai con il token**.

## Collaudo

- Home Assistant TEST 2026.11.0: invio del corpo in un unico pacchetto e in due pacchetti a 0,5 s di distanza, entrambi letti per intero; test automatici superati.

## Aggiornamento

Da HACS aggiorna a `v0.2.8` e riavvia Home Assistant. Nessuna riconfigurazione richiesta.
