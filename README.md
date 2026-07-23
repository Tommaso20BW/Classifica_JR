# 📊 Classifica JR

Bot Telegram che recupera le classifiche calcistiche da ESPN, genera una card grafica ad alta risoluzione e la pubblica sul canale configurato.

Il progetto gira su GitHub Actions e supporta quattro competizioni:

| `COMPETITION` | Competizione | Slug ESPN |
|---|---|---|
| `SA` | Serie A | `ita.1` |
| `UCL` | Champions League | `uefa.champions` |
| `UEL` | Europa League | `uefa.europa` |
| `UECL` | Conference League | `uefa.europa.conf` |

## Come funziona

Ogni esecuzione segue questa pipeline:

```text
ESPN standings API
        │
        ▼
aggiorna_classifica.py ──► classifica.json
        │
        ▼
index.html + Playwright + texture
        │
        ▼
screenshot.png ──► Telegram
        │
        └────────► commit di classifica.json
```

### 1. Recupero e normalizzazione

`aggiorna_classifica.py`:

- legge la competizione dalla variabile `COMPETITION` (default `SA`);
- interroga l’endpoint pubblico ESPN delle classifiche;
- estrae posizione, punti, partite, vittorie, pareggi, sconfitte, gol fatti/subiti e differenza reti;
- ricava giornata e stagione, con fallback basato sulla data corrente;
- normalizza i nomi tramite `teams.json`;
- applica override grafici per alcuni loghi;
- salva il risultato in `classifica.json`.

### 2. Rendering e invio

`screenshot_telegram.py`:

- incorpora in base64 i font Google dichiarati in `index.html`, con fallback ai font di sistema;
- inietta `classifica.json` nel template;
- renderizza la pagina con Playwright/Chromium;
- usa fondali UEFA ad alta definizione con un overlay nero semitrasparente al 70%;
- ridimensiona il risultato alla risoluzione HD 3:4 di **1920×2560 px**;
- applica `texture_white.png` a tutte e quattro le competizioni;
- prepara la card in formato foto HD 3:4 (`1920x2560`) e la invia con `sendPhoto`, mantenendo la didascalia HTML;
- controlla nella risposta di Telegram la risoluzione della variante foto più grande.

Lo screenshot è temporaneo e non viene committato. Il workflow aggiorna invece `classifica.json` nel repository quando il contenuto cambia.

## Workflow

È presente un workflow manuale per ogni competizione:

- `.github/workflows/SerieA.yml`
- `.github/workflows/ChampionsLeague.yml`
- `.github/workflows/EuropaLeague.yml`
- `.github/workflows/ConferenceLeague.yml`

Tutti usano Python 3.10, installano Chromium e avviano in sequenza i due script. Non è configurato uno schedule automatico.

## Configurazione

In **Settings → Secrets and variables → Actions** configura:

| Secret | Obbligatorio | Uso |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | sì | Token del bot Telegram. |
| `TELEGRAM_CHAT_ID` | sì | Chat o canale di destinazione. |

`FOOTBALL_API_KEY` compare nei workflow, ma il codice non la usa: l’endpoint ESPN chiamato dal bot non richiede una chiave API.

## Avvio

### Da GitHub

Apri **Actions**, seleziona il workflow della competizione desiderata e usa **Run workflow**.

### In locale

```bash
python -m pip install -r requirements.txt
playwright install chromium
```

Esempio per la Serie A:

```bash
COMPETITION=SA python aggiorna_classifica.py
COMPETITION=SA python screenshot_telegram.py
```

Per il secondo comando servono `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`. Su PowerShell imposta le variabili con `$env:NOME="valore"` prima di eseguire gli script.

## Struttura

```text
Classifica_JR/
├── aggiorna_classifica.py
├── screenshot_telegram.py
├── index.html
├── classifica.json
├── teams.json
├── texture_white.png
├── serie-a-scudetto.png
├── ucl-mark.png
├── uel-mark.png
├── uecl-mark.png
├── ucl-texture-hq.webp
├── uel-texture-hq.webp
├── uecl-texture-hq.webp
├── requirements.txt
└── .github/workflows/
    ├── SerieA.yml
    ├── ChampionsLeague.yml
    ├── EuropaLeague.yml
    └── ConferenceLeague.yml
```

## Limiti noti

- Gli endpoint ESPN usati sono pubblici ma non documentati: struttura e disponibilità possono cambiare.
- Giornata e stagione dipendono dai metadati ESPN; se mancano vengono stimate dai dati disponibili.
- Font, loghi e rendering richiedono accesso di rete durante l’esecuzione; sono previsti alcuni fallback grafici.

---

Progetto amatoriale, non affiliato con Juventus FC, Telegram o ESPN.
