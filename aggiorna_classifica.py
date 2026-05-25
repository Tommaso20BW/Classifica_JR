import os
import sys
import requests
import json

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
        "giornate": 8,
    },
}

# Overrides loghi per squadre italiane (Wikipedia SVG, alta qualità)
LOGO_OVERRIDE = {
    "juventus":  "https://upload.wikimedia.org/wikipedia/commons/9/99/Juventus_FC_2017_squared_icon_%28white%29.png",
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


def parse_standings(data: dict) -> tuple[list, int]:
    """
    Estrae la lista classifica e la giornata corrente dal JSON ESPN.
    Restituisce (classifica_pulita, giornata).
    """
    classifica = []
    giornata = 1

    # La stagione corrente è in data['season']
    season = data.get("season", {})
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

        for entry in entries:
            team = entry.get("team", {})
            nome = team.get("displayName", team.get("name", "?"))

            # Logo: ESPN CDN (alta qualità)
            logos = team.get("logos", [])
            logo_url = logos[0]["href"] if logos else ""

            # Override logo Juventus
            if "juventus" in nome.lower():
                logo_url = LOGO_OVERRIDE["juventus"]

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
    return classifica, giornata


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

    classifica, giornata = parse_standings(data)

    if not classifica:
        print("❌ Nessuna squadra trovata nella risposta ESPN.")
        sys.exit(1)

    output = {
        "competition":      comp_key,
        "competition_name": comp["nome"],
        "giornata":         giornata,
        "classifica":       classifica,
    }

    with open("classifica.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"✅ JSON salvato: {comp['nome']} – Giornata {giornata} ({len(classifica)} squadre).")


if __name__ == "__main__":
    genera_json_classifica()
