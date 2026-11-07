# Contarina SOL 0.2.5b3 (beta)

## Correzione icone

- Ripristinato `custom_components/contarina/brand/icon.png` dalla **0.2.3b1**, ultima release con PNG integro.
- `custom_components/contarina/brand/logo.png` usa la stessa immagine valida.
- La `0.2.4b1` aveva introdotto PNG danneggiati: intestazione/dimensioni leggibili ma CRC della palette non valido e struttura dei chunk incompleta; la corruzione si era propagata alle beta successive.
- Aggiunto `tests/test_brand_png.py`, che verifica **firma, CRC di tutti i chunk, IHDR, IDAT, IEND, dimensioni e assenza di dati troncati** e fallisce sui PNG alterati.
- Verifica visuale del frontend Home Assistant e del Marketplace da completare **dopo** l'installazione della nuova beta.

## Compatibilità

- Nessuna modifica a login, token, API SOL, sensori, calendario, entità, unique ID o dashboard.
- Home Assistant minimo: 2026.11.0.
- L'integrazione resta non ufficiale e in beta.

La release viene pubblicata solo dopo i test Python, Node, Home Assistant/Chrome, hassfest e HACS.
