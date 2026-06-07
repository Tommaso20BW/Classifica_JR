import os
import sys
import requests
import json
from pathlib import Path

# ESPN slug per competizione → nessuna API key richiesta
COMPETIZIONI = {
    "SA": {
        "slug":   "ita.1",
        "nome":   "Serie A",
        "comp":   "SA",
        "giornate": 38,
    },
    "UCL": {
        "slug":   "uefa.champions",
        "nome":   "Champions League",
        "comp":   "UCL",
        "giornate": 8,
    },
    "UEL": {
        "slug":   "uefa.europa",
        "nome":   "Europa League",
        "comp":   "UEL",
        "giornate": 8,
    },
    "UECL": {
        "slug":   "uefa.europa.conf",
        "nome":   "Conference League",
        "comp":   "UECL",
        "giornate": 6,
    },
}

# Overrides loghi per squadre italiane
LOGO_OVERRIDE = {
    "juventus":  "https://upload.wikimedia.org/wikipedia/commons/9/99/Juventus_FC_2017_squared_icon_%28white%29.png",
    "napoli":    "https://upload.wikimedia.org/wikipedia/commons/4/4d/SSC_Napoli_2025_%28white_and_azure%29.svg",
    "atalanta":  "https://upload.wikimedia.org/wikipedia/it/2/24/Atalanta_BC_2026.svg",
    "udinese":   "https://upload.wikimedia.org/wikipedia/it/a/ae/Logo_Udinese_Calcio_2010.svg",
    "fiorentina":"https://upload.wikimedia.org/wikipedia/commons/8/8c/ACF_Fiorentina_-_logo_%28Italy%2C_2022%29.svg",
    "verona":    "https://sport.sky.it/assets/images/3a737aa34cf3cac3ed64133d1527a6c517d0e8d5/skysport/it/calcio/serie-a/2020/06/01/hellas-verona-stemma/herllas%20verona_giallo_dentro.png",
    "roma":      "https://images2.gazzettaobjects.it/assets-mc/calcio/squadre/high/121.png",
    "venezia":   "https://upload.wikimedia.org/wikipedia/it/7/73/Venezia_FC_Logo_2026.svg",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}


# ── Mappa nomi squadre: nome ESPN → nome corretto (da teams.json) ──
def carica_mappa_nomi() -> tuple[dict, dict]:
    """
    Legge teams.json (nella stessa cartella dello script) e costruisce la
    mappa 'nome ESPN' → 'nome corretto'.

    Formato di teams.json:
        "Nome ESPN": ["Nome corretto", "Hashtag"]
    Il terzo campo (hashtag) NON viene usato.

    Restituisce due dizionari: uno con le chiavi originali e uno con le chiavi
    in minuscolo, così il confronto è robusto a differenze di maiuscole.
    Se teams.json manca o è illeggibile, torna mappe vuote (fallback ai nomi ESPN).
    """
    path = Path(__file__).parent / "teams.json"
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        print("⚠️  teams.json non trovato: uso i nomi originali ESPN.")
        return {}, {}
    except Exception as e:
        print(f"⚠️  Impossibile leggere teams.json ({e}): uso i nomi ESPN.")
        return {}, {}

    esatta: dict[str, str] = {}
    minuscola: dict[str, str] = {}
    for espn, valori in raw.items():
        corretto = valori[0] if isinstance(valori, list) and valori else espn
        esatta[espn] = corretto
        minuscola[espn.lower().strip()] = corretto
    return esatta, minuscola


MAPPA_NOMI, MAPPA_NOMI_LOWER = carica_mappa_nomi()


def nome_corretto(espn_name: str) -> str:
    """Converte un nome ESPN nel nome corretto definito in teams.json."""
    if not espn_name:
        return espn_name
    if espn_name in MAPPA_NOMI:
        return MAPPA_NOMI[espn_name]
    return MAPPA_NOMI_LOWER.get(espn_name.lower().strip(), espn_name)


def format_stagione(anno_inizio) -> str:
    """Da anno d'inizio ESPN (es. 2026) → stringa stagione '2026/27'.
    Torna '' se il valore non è un anno valido."""
    try:
        y = int(anno_inizio)
    except (TypeError, ValueError):
        return ""
    if y < 1900 or y > 2100:
        return ""
    return f"{y}/{(y + 1) % 100:02d}"


def stagione_da_testo(testo: str) -> str:
    """Estrae la stagione da stringhe ESPN tipo '2026-2027' o
    'Serie A 2026-2027' / '2026-27 Serie A'. Torna '' se non trovata."""
    import re
    m = re.search(r"(19|20)\d{2}", testo or "")
    return format_stagione(m.group()) if m else ""


def stagione_corrente_da_data() -> str:
    """Fallback (solo se l'API non espone la stagione): la ricava dalla data
    odierna. La stagione calcistica inizia a luglio."""
    from datetime import date
    oggi = date.today()
    anno_inizio = oggi.year if oggi.month >= 7 else oggi.year - 1
    return format_stagione(anno_inizio)


def get_standings_espn(slug: str) -> dict | None:
    """
    Chiama l'API pubblica non documentata di ESPN per le classifiche calcio.
    Restituisce il JSON grezzo oppure None in caso di errore.
    """
    url = f"https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        print(f"❌ HTTP {e.response.status_code} da ESPN ({slug}): {e}")
    except Exception as e:
        print(f"❌ Errore di rete ESPN ({slug}): {e}")
    return None


def parse_standings(data: dict) -> tuple[list, int, str]:
    """
    Estrae la lista classifica, la giornata e la stagione dal JSON ESPN.
    Restituisce (classifica_pulita, giornata, stagione).
    """
    classifica = []
    giornata = 1
    stagione = ""

    # ESPN non espone direttamente la matchday; la ricaviamo dai filter/note
    # Proviamo ad ottenerla da 'notes'
    for note in data.get("notes", []):
        text = note.get("headline", "")
        if "matchday" in text.lower() or "giornata" in text.lower() or "week" in text.lower():
            import re
            m = re.search(r"\d+", text)
            if m:
                giornata = int(m.group())
                break

    # Scorri i children (gruppi/fasi)
    children = data.get("children", [data])
    for child in children:
        standings_obj = child.get("standings", {})
        entries = standings_obj.get("entries", [])
        if not entries:
            continue

        # ── Stagione dall'API ESPN ──
        # Sorgente primaria: il campo intero 'season' (anno d'inizio, es. 2026).
        # Fallback: testo di 'seasonDisplayName' / nome o abbreviazione del gruppo
        # (es. "2026-27 Serie A", "Serie A 2026-2027", "2026-2027").
        if not stagione:
            stagione = format_stagione(standings_obj.get("season"))
        if not stagione:
            stagione = stagione_da_testo(
                standings_obj.get("seasonDisplayName")
                or child.get("abbreviation")
                or child.get("name")
            )

        for entry in entries:
            team = entry.get("team", {})
            nome = team.get("displayName", team.get("name", "?"))

            # Logo: ESPN CDN (alta qualità)
            logos = team.get("logos", [])
            logo_url = logos[0]["href"] if logos else ""

            # Override loghi per squadre note
            nome_lower = nome.lower()
            for chiave, url in LOGO_OVERRIDE.items():
                if chiave in nome_lower:
                    logo_url = url
                    break

            # Statistiche dalle 'stats'
            stats = {s["name"]: s.get("value", 0) for s in entry.get("stats", [])}

            pos   = int(stats.get("rank", entry.get("rank", 0)))
            pt    = int(stats.get("points", 0))
            pld   = int(stats.get("gamesPlayed", 0))
            won   = int(stats.get("wins", 0))
            draw  = int(stats.get("ties", 0))
            lost  = int(stats.get("losses", 0))
            gf    = int(stats.get("pointsFor", 0))
            ga    = int(stats.get("pointsAgainst", 0))
            dr    = int(stats.get("pointDifferential", gf - ga))

            # Aggiorna giornata con il massimo delle partite giocate
            if pld > giornata:
                giornata = pld

            # Nome corretto da teams.json (l'override loghi qui sopra usa
            # ancora il nome ESPN originale, quindi non cambia comportamento)
            nome = nome_corretto(nome)

            classifica.append({
                "pos":    pos,
                "team":   nome,
                "logo":   logo_url,
                "pt":     pt,
                "p":      pld,
                "v":      won,
                "n":      draw,
                "p_pers": lost,
                "gf":     gf,
                "gs":     ga,
                "dr":     dr,
            })

        break  # usa solo il primo gruppo valido

    # Ordina per posizione
    classifica.sort(key=lambda x: x["pos"])
    return classifica, giornata, stagione


def genera_json_classifica():
    comp_key = os.environ.get("COMPETITION", "SA").upper()
    comp = COMPETIZIONI.get(comp_key)
    if not comp:
        print(f"❌ Competizione non riconosciuta: {comp_key}. Usa SA, UCL, UEL o UECL.")
        sys.exit(1)

    print(f"📡 Recupero classifica ESPN: {comp['nome']} ({comp_key})...")

    data = get_standings_espn(comp["slug"])
    if data is None:
        print("❌ Impossibile recuperare i dati. Controlla la connessione.")
        sys.exit(1)

    classifica, giornata, stagione = parse_standings(data)

    if not classifica:
        print("❌ Nessuna squadra trovata nella risposta ESPN.")
        sys.exit(1)

    # Se l'API non ha esposto la stagione, la ricaviamo dalla data odierna
    if not stagione:
        stagione = stagione_corrente_da_data()
        print(f"⚠️  Stagione non trovata nell'API ESPN: uso il fallback da data ({stagione}).")

    output = {
        "competition":      comp_key,
        "competition_name": comp["nome"],
        "giornata":         giornata,
        "stagione":         stagione,
        "classifica":       classifica,
    }

    with open("classifica.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"✅ JSON salvato: {comp['nome']} – Giornata {giornata} – Stagione {stagione} ({len(classifica)} squadre).")


if __name__ == "__main__":
    genera_json_classifica()
