<div align="center">

# 📊 Classifica JR

**Bot Telegram che pubblica in automatico le classifiche calcistiche con grafica ad alta risoluzione.**

Recupera i dati da ESPN, li trasforma in una card grafica brandizzata e la invia su Telegram — costruito su GitHub Actions, senza server.

`Python 3.10` · `ESPN API` · `Playwright` · `Pillow` · `GitHub Actions`

</div>

-----

## Indice

- [Cos’è](#cosè)
- [Come funziona](#come-funziona)
- [Funzionalità](#funzionalità)
- [Competizioni supportate](#competizioni-supportate)
- [Struttura del repository](#struttura-del-repository)
- [Configurazione](#configurazione)
- [Avvio](#avvio)
- [Stack tecnico](#stack-tecnico)
- [Fonte dati](#fonte-dati)

-----

## Cos’è

Classifica JR recupera la classifica aggiornata di Serie A, Champions League, Europa League o Conference League tramite l’API pubblica di ESPN, la renderizza in una card grafica personalizzata e la invia come immagine al canale Telegram **@Juventus_Reborn**. Ogni competizione ha il proprio workflow GitHub Actions attivabile manualmente.

-----

## Come funziona

```
                ┌──────────────────────┐
                │   GitHub Actions      │  ← un workflow per competizione
                │  SerieA · UCL · ...   │
                └──────────┬───────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │         aggiorna_classifica.py        │
        │   scarica la classifica da ESPN e     │
        │   la salva in classifica.json         │
        └────────────────────┬───────────────────┘
                             │
                             ▼
        ┌──────────────────────────────────────┐
        │        screenshot_telegram.py         │
        │   index.html → PNG (Playwright)       │
        │   + overlay texture (Pillow) → invio  │
        └───────────────┬──────────┬─────────────┘
                        │          │
                        ▼          ▼
                  ┌─────────┐  ┌──────────┐
                  │  ESPN   │  │ Telegram │
                  │ (dati)  │  │ (output) │
                  └─────────┘  └──────────┘
```

Il workflow esegue i due script in sequenza: prima `aggiorna_classifica.py` recupera i dati da ESPN e li salva in `classifica.json`, poi `screenshot_telegram.py` renderizza la card da `index.html`, vi applica l’overlay texture e la invia su Telegram.

-----

## Funzionalità

- **Recupero dati ESPN** — classifica completa con posizione, punti, partite, vittorie, pareggi, sconfitte, gol fatti/subiti e differenza reti.
- **Loghi personalizzati** — override dei loghi ESPN per le squadre italiane (Juventus, Napoli, Atalanta, Fiorentina, Roma, Udinese, Verona).
- **Rendering grafico** — la classifica viene resa in HTML e scattata come screenshot con Playwright a risoluzione **1080×1440 px** con fattore di scala 3×.
- **Overlay texture** — immagine `texture.png` applicata come layer trasparente per un effetto grafico coerente con il branding del canale.
- **Font embedded in base64** — i font Google (Bebas Neue, Barlow Condensed, Inter) vengono scaricati e incorporati direttamente nell’HTML per garantire il rendering corretto in ambienti CI senza accesso a risorse esterne.
- **Commit automatico del JSON** — `classifica.json` viene aggiornato e committato nel repository ad ogni esecuzione.
- **Didascalia dinamica** — il messaggio Telegram riporta automaticamente il numero di giornata corrente.

-----

## Competizioni supportate

|Variabile `COMPETITION`|Campionato       |Emoji|
|-----------------------|-----------------|-----|
|`SA`                   |Serie A          |🇮🇹    |
|`UCL`                  |Champions League |🇪🇺    |
|`UEL`                  |Europa League    |🇪🇺    |
|`UECL`                 |Conference League|🇪🇺    |

-----

## Struttura del repository

```
Classifica_JR/
├── aggiorna_classifica.py    # Recupera e salva la classifica in JSON
├── screenshot_telegram.py    # Renderizza la card HTML e invia su Telegram
├── index.html                # Template grafico della classifica
├── classifica.json           # Dati aggiornati (rigenerati ad ogni esecuzione)
├── texture.png               # Overlay grafico applicato all'immagine finale
└── .github/workflows/
    ├── SerieA.yml            # Workflow Serie A
    ├── ChampionsLeague.yml   # Workflow Champions League
    ├── EuropaLeague.yml      # Workflow Europa League
    └── ConferenceLeague.yml  # Workflow Conference League
```

-----

## Configurazione

In **Settings → Secrets and variables → Actions** aggiungi:

|Secret              |Descrizione                                                                |
|--------------------|---------------------------------------------------------------------------|
|`TELEGRAM_BOT_TOKEN`|Token del bot Telegram.                                                    |
|`TELEGRAM_CHAT_ID`  |Chat ID del canale di destinazione.                                        |
|`FOOTBALL_API_KEY`  |*(Presente nei workflow ma non usato attivamente — ESPN non richiede key.)*|

-----

## Avvio

1. Fai il **fork** del repository.
1. Configura i secret elencati sopra.
1. Avvia il workflow desiderato da `Actions → [nome campionato] → Run workflow`.

> Il workflow esegue i due script in sequenza: prima aggiorna il JSON, poi genera lo screenshot e lo invia su Telegram.

-----

## Stack tecnico

`Python 3.10` · `requests` · `Playwright (Chromium)` · `Pillow` · `GitHub Actions`

-----

## Fonte dati

[ESPN API pubblica](https://site.api.espn.com/apis/v2/sports/soccer/) — nessuna API key necessaria.

-----

<div align="center">

*Progetto amatoriale. Non affiliato con la Juventus FC, Telegram o ESPN.*

</div>