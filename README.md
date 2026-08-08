<div align="center">

# 📊 Classifica JR

**Generatore di classifiche calcistiche in alta definizione con pubblicazione su Telegram.**

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Serie A](https://github.com/Tommaso20BW/Classifica_JR/actions/workflows/SerieA.yml/badge.svg)](https://github.com/Tommaso20BW/Classifica_JR/actions/workflows/SerieA.yml)

</div>

## Panoramica

Classifica JR recupera i dati da ESPN, li normalizza in un file JSON, renderizza una card verticale e la invia al canale Telegram configurato.

```text
ESPN standings
      ↓
aggiorna_classifica.py
      ↓
classifica.json
      ↓
index.html + Playwright + Pillow
      ↓
screenshot.png
      ↓
Telegram
```

## Competizioni

La variabile `COMPETITION` seleziona uno dei quattro profili:

| Valore | Competizione | Slug ESPN | Giornate fase principale |
| --- | --- | --- | ---: |
| `SA` | Serie A | `ita.1` | 38 |
| `UCL` | Champions League | `uefa.champions` | 8 |
| `UEL` | Europa League | `uefa.europa` | 8 |
| `UECL` | Conference League | `uefa.europa.conf` | 6 |

Il valore predefinito è `SA`.

## Recupero e normalizzazione

`aggiorna_classifica.py` interroga l'endpoint pubblico ESPN delle classifiche ed estrae:

- posizione e punti;
- partite giocate, vittorie, pareggi e sconfitte;
- gol fatti, gol subiti e differenza reti;
- giornata corrente;
- stagione.

La giornata viene ricavata dalle note ESPN quando possibile e aggiornata con il massimo numero di partite giocate. La stagione usa i metadati ESPN; se mancano, viene stimata dalla data corrente considerando luglio come inizio della nuova annata.

`teams.json` normalizza i nomi delle squadre. Per alcuni club italiani sono inoltre configurati URL grafici alternativi per il logo.

Il risultato viene scritto in `classifica.json`:

```json
{
  "competition": "SA",
  "competition_name": "Serie A",
  "giornata": 1,
  "stagione": "2026/27",
  "classifica": []
}
```

## Rendering e invio

`screenshot_telegram.py`:

1. legge `classifica.json`;
2. incorpora in base64 i Google Fonts dichiarati in `index.html`, con fallback ai font di sistema;
3. inietta i dati direttamente nel template;
4. renderizza la pagina con Playwright e Chromium;
5. ridimensiona l'immagine a **1920 × 2560 px**;
6. applica `texture_white.png` come rifinitura finale;
7. invia il PNG a Telegram con `sendPhoto` e didascalia HTML.

Il template cambia colori, fondale e marchio in base alla competizione. Serie A usa lo Scudetto; le coppe europee usano i rispettivi marchi e fondali ad alta risoluzione.

Dopo l'invio il codice legge dalla risposta Telegram la variante foto più grande e segnala nei log se non raggiunge almeno 2.000 pixel sul lato maggiore.

> [!NOTE]
> Lo screenshot e il file HTML temporaneo non vengono conservati nel repository. GitHub Actions committa soltanto `classifica.json` quando cambia.

## Struttura

```text
Classifica_JR/
├── aggiorna_classifica.py
├── screenshot_telegram.py
├── index.html
├── classifica.json
├── teams.json
├── texture_white.png
├── texture_black.png
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

## Requisiti

- Python 3.14, come nei workflow GitHub Actions;
- Chromium per Playwright;
- accesso a ESPN, agli asset grafici remoti e a Telegram.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
playwright install chromium
```

## Configurazione

Configura in **Settings → Secrets and variables → Actions**:

| Secret | Uso |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token del bot Telegram |
| `TELEGRAM_CHAT_ID` | Chat o canale di destinazione |

`FOOTBALL_API_KEY` è ancora presente nei workflow per compatibilità, ma il codice non la legge: l'endpoint ESPN usato non richiede una chiave.

## Avvio locale

### Linux e macOS

```bash
export COMPETITION="SA"
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
python aggiorna_classifica.py
python screenshot_telegram.py
```

### PowerShell

```powershell
$env:COMPETITION = "SA"
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
python aggiorna_classifica.py
python screenshot_telegram.py
```

La generazione del JSON termina con errore se ESPN non restituisce una classifica valida. Lo script grafico, invece, segnala nei log secret mancanti o rifiuti Telegram senza forzare attualmente un codice di uscita non zero.

## GitHub Actions

È presente un workflow manuale per ogni competizione:

| Workflow | `COMPETITION` |
| --- | --- |
| `SerieA.yml` | `SA` |
| `ChampionsLeague.yml` | `UCL` |
| `EuropaLeague.yml` | `UEL` |
| `ConferenceLeague.yml` | `UECL` |

Tutti i workflow:

- usano Python 3.14;
- installano e mettono in cache Chromium;
- aggiornano `classifica.json`;
- generano e inviano la card;
- committano il JSON quando cambia;
- eliminano i propri run completati dalla cronologia.

Non è configurato uno `schedule`: l'avvio avviene tramite **Run workflow** o un sistema esterno.

## Limiti noti

- Gli endpoint ESPN usati sono pubblici ma non documentati.
- Classifiche con più gruppi usano il primo gruppo valido restituito dall'API.
- Giornata e stagione possono essere stimate quando ESPN non espone metadati sufficienti.
- Font, loghi e fondali remoti possono non essere raggiungibili; sono presenti fallback parziali.
- Un errore Telegram viene mostrato nei log, ma non rende necessariamente fallito il workflow.

---

Progetto amatoriale, non affiliato con Juventus Football Club, Telegram o ESPN.
