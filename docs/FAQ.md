# Domande frequenti — Contarina SOL

## Installazione e login

### Non trovo Contarina nella ricerca Marketplace
Il repository può essere aggiunto **direttamente da URL**, anche se non è ancora nel catalogo generale: `https://github.com/EnrCol/ha-contarina`. Home Assistant 2026.11+: **Impostazioni → Marketplace → Aggiungi da link**. Il fatto che non sia presente nella ricerca non significa che non sia installabile.

### Il primo login richiede ancora di incollare il JWT?
No, dalla 0.2.5b1 puoi scegliere **Collega dal browser**, effettuare normalmente il login al sito SOL e usare il preferito **Invia token a Home Assistant**. Il copia-incolla resta un'alternativa. Vedi [guida login](LOGIN_ASSISTITO.md).

### Perché devo usare un preferito? Posso inserire username e password?
La pagina SOL usa il proprio login e reCAPTCHA. L'integrazione non memorizza password e non automatizza la procedura di accesso. Il preferito legge un token dalla pagina SOL **già autenticata** e lo trasmette alla tua istanza Home Assistant.

### Uso Home Assistant sul PC e SOL sul telefono
Nella pagina di collegamento crea il preferito sul telefono e inserisci il **codice di abbinamento** mostrato nel dialogo di Home Assistant. Scade dopo 10 minuti ed è monouso. Il telefono deve poter raggiungere Home Assistant all'indirizzo contenuto nel preferito, meglio se HTTPS.

### Chrome, Edge, Firefox, Safari, Samsung Internet: funzionano tutti?
Non esiste ancora una matrice di compatibilità verificata su ogni dispositivo. Alcuni browser o estensioni limitano i bookmarklet, gli appunti e l'esecuzione da preferiti. La pagina include istruzioni per Chrome Android e Safari iOS; se la procedura non funziona, usa il **token manuale** e segnala browser/versione senza allegare il JWT.

### La sessione scade nonostante il rinnovo automatico
SOL rifiuta i token già scaduti. L'integrazione rinnova il JWT durante il normale funzionamento; arresti di Home Assistant, problemi di rete o interruzioni prolungate richiedono il login su SOL. A scadenza viene avviata la riautenticazione nativa; sono disponibili notifica persistente e push opzionale.

### Le opzioni del menu sono vuote o la descrizione è vecchia
Dopo un aggiornamento potrebbero restare traduzioni in cache. Esci dal flusso, ricarica forzatamente la pagina nel browser e, se necessario, riavvia **Home Assistant Core**. Controlla la versione installata nel Marketplace. Non cancellare preventivamente l'integrazione già configurata.

## Icona e grafica

### L'icona non compare nel Marketplace o nelle Integrazioni
**Sono due percorsi diversi e vanno diagnosticati separatamente.**

1. Controlla che la release installata includa `custom_components/contarina/brand/icon.png` e `logo.png`. I file sono presenti nel repository; l'icona `icon.png` è un PNG 256×256 valido.
2. **Home Assistant → Dispositivi e servizi:** dalla versione 2026.3 l'immagine viene servita tramite l'API locale `/api/brands/integration/contarina/icon.png`, accessibile con autenticazione. Se non viene mostrata, ricarica il browser e verifica che l'integrazione sia stata caricata dopo l'installazione. Per diagnosi, usa gli strumenti di rete del browser e controlla la richiesta al proxy con `?placeholder=no`, che restituisce 404 se l'immagine non esiste. Non pubblicare URL con token di autenticazione.
3. **Marketplace:** il catalogo pubblico recupera le immagini delle integrazioni che vi sono censite, tramite sincronizzazione dalle **GitHub Release**. Un repository aggiunto manualmente da link potrebbe non avere l'icona indicizzata nello stesso modo. Il segnaposto del Marketplace non prova che la release non contenga il PNG.
4. Se il PNG locale esiste ma la grafica continua a mancare, apri una issue specificando **solo** Home Assistant/versione, schermata interessata e risultato HTTP della richiesta all'immagine, senza token né indirizzi privati.

**Stato:** i file nel repository sono verificati. La visualizzazione dopo l'installazione dipende anche dal riavvio e dalla cache del frontend; dalla `0.2.5b4` la nuova icona è un bidone per la raccolta, non la precedente C, quindi non è dichiarata risolta dalla release 0.2.5b2.

Riferimenti ufficiali: [Brand images for custom integrations](https://contributors.home-assistant.io/core/integrations/brands/) · [Publish a custom integration](https://contributors.home-assistant.io/marketplace/guides/integrations/).

## Sensori, calendario, fatture

### Come riconosco l'utenza nelle entità?
Apri **Impostazioni → Dispositivi e servizi → Contarina → Entità**: gli `entity_id` includono un identificativo della tua utenza. Usalo solo nelle configurazioni private; oscuralo in screenshot pubblici.

### Le raccolte non coincidono con il calendario precedente
Confronta le stesse date e le stesse tipologie di rifiuti fra SOL, l'integrazione precedente e il calendario nativo. Non disattivare automazioni o sorgenti già funzionanti fino a quando non hai verificato la corrispondenza. Il calendario SOL può essere modificato dal gestore.

### Lo stato fattura «da verificare» significa insoluto?
**No.** SOL può fornire indicazioni non coerenti con i pagamenti registrati; la classificazione dell'integrazione non prova un saldo esigibile. Per una verifica economica prevale il portale ufficiale Contarina. Non pubblicare lo storico fatture in dashboard accessibili agli ospiti.

### Perché il Secco mostra 4 minimi quando ho 3 componenti?
Per il caso supportato (utenza domestica, un solo bidone Secco attivo da 120 L) la stima è **componenti + 1**. Questi svuotamenti sono **già addebitati nel minimo**, non gratuiti. Il numero dei componenti in fattura può riferirsi al 31 dicembre precedente; la stima è indicativa. Per capacità o contratti diversi la soglia non viene stimata automaticamente.

### Ho rimosso e riaggiunto Contarina: cambieranno gli `entity_id`?
Su un'utenza domestica reale il test ha ricreato **23 entità conservando tutti gli ID**. Non è una garanzia universale. Prima di una cancellazione esporta/annota `entity_id` e i consumatori; la dashboard non viene eliminata insieme all'integrazione.

## Segnalare un problema

Apri una [issue](https://github.com/EnrCol/ha-contarina/issues/new) indicando versione Home Assistant, versione Contarina, versione/browser, passaggi di riproduzione ed esito atteso/effettivo. Non allegare **JWT, username, password, codici monouso, numeri di contratto, fatture, indirizzi, log con header Authorization o URL con token**. Per dettagli consulta [CONTRIBUTING](CONTRIBUTING.md) e [privacy](PRIVACY_SICUREZZA.md).
