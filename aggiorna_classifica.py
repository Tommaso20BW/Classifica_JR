import os
import json
import requests

# Fornisce "SA" come fallback se la variabile d'ambiente COMPETITION non è impostata
COMP_KEY = os.environ.get("COMPETITION", "SA").upper()

COMP_IDS = {
    "SA": "ita.1",
    "UCL": "uefa.champions",
    "UEL": "uefa.europa",
    "UECL": "uefa.europa.conf"
}

def scarica_dati_classifica(comp_key):
    print(f"📡 Recupero classifica ESPN per la competizione: {comp_key}...")
    comp_id = COMP_IDS.get(comp_key, COMP_IDS["SA"])
    
    url = f"https://site.api.espn.com/apis/v2/sports/soccer/all/leagues/{comp_id}/standings"
    res = requests.get(url)
    
    if res.status_code != 200:
        raise Exception(f"Errore API ESPN: {res.status_code}")
        
    data = res.json()
    
    # Tentativo di estrarre la giornata (matchweek) attuale dai dati della lega
    giornata = "—"
    try:
        # Spesso ESPN espone la giornata corrente in data['season']['types'][0]['groups'][0]...
        # o simili. Per sicurezza, cerchiamo nel finto "season" o usiamo un fallback.
        if "season" in data and "year" in data["season"]:
            # Se l'API non ha un campo diretto "matchweek", lasciamo "—" o gestiamolo
            pass
    except:
        pass

    # Se è una coppa europea (fase a gironi o classifica unica), adattiamo la struttura
    standings_list = data.get("children", [data])[0].get("standings", {}).get("entries", [])
    
    table_data = []
    for entry in standings_list:
        stats = {s["name"]: s["value"] for s in entry.get("stats", [])}
        team  = entry.get("team", {})
        
        # Estrazione dei dettagli principali
        table_data.append({
            "position": entry.get("stats", [{}])[0].get("value", len(table_data)+1), # fallback posizione
            "team_name": team.get("displayName", "Sconosciuto"),
            "team_logo": team.get("logos", [{}])[0].get("href", ""),
            "played": int(stats.get("gamesPlayed", 0)),
            "wins": int(stats.get("wins", 0)),
            "draws": int(stats.get("ties", 0)),
            "losses": int(stats.get("losses", 0)),
            "goals_for": int(stats.get("pointsFor", 0)),
            "goals_against": int(stats.get("pointsAgainst", 0)),
            "goal_diff": int(stats.get("pointDifferential", 0)),
            "points": int(stats.get("points", 0))
        })
        
    # Ordina per posizione numerica corretta
    table_data.sort(key=lambda x: x["position"])
    
    return table_data, giornata

def main():
    print(f"🚀 Avvio aggiorna_classifica.py per: {COMP_KEY}")
    
    try:
        tabella, giornata = scarica_dati_classifica(COMP_KEY)
    except Exception as e:
        print(f"❌ Errore durante il recupero dei dati: {e}")
        return

    # Salva il file classifica.json strutturato per index.html
    output = {
        "competition": COMP_KEY,
        "giornata": giornata,
        "table": tabella
    }
    
    with open("classifica.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
        
    print(f"💾 File classifica.json generato con successo ({len(tabella)} squadre).")

if __name__ == "__main__":
    main()
