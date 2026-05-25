import os
import requests
import json

# Mappatura nomi squadre
MAPPA_NOMI = {
    # --- SERIE A ---
    "juventus fc": "Juventus", "juventus": "Juventus",
    "inter milan": "Inter", "fc internazionale milano": "Inter", "inter": "Inter",
    "ac milan": "Milan", "milan": "Milan",
    "ssc napoli": "Napoli", "napoli": "Napoli",
    "as roma": "Roma", "roma": "Roma",
    "ss lazio": "Lazio", "lazio": "Lazio",
    "atalanta bc": "Atalanta", "atalanta": "Atalanta",
    "bologna fc 1909": "Bologna", "bologna fc": "Bologna", "bologna": "Bologna",
    "acf fiorentina": "Fiorentina", "fiorentina": "Fiorentina",
    "torino fc": "Torino", "torino": "Torino",
    "udinese calcio": "Udinese", "udinese": "Udinese",
    "empoli fc": "Empoli", "empoli": "Empoli",
    "us lecce": "Lecce", "lecce": "Lecce",
    "ac monza": "Monza", "monza": "Monza",
    "cagliari calcio": "Cagliari", "cagliari": "Cagliari",
    "genoa cfc": "Genoa", "genoa": "Genoa",
    "como 1907": "Como", "como": "Como",
    "parma calcio 1913": "Parma", "parma calcio": "Parma", "parma": "Parma",
    "venezia fc": "Venezia", "venezia": "Venezia",
    "hellas verona fc": "Verona", "hellas verona": "Verona",
    # --- SERIE B ---
    "us sassuolo calcio": "Sassuolo", "us sassuolo": "Sassuolo", "sassuolo": "Sassuolo",
    "us salernitana 1919": "Salernitana", "us salernitana": "Salernitana", "salernitana": "Salernitana",
    "frosinone calcio": "Frosinone", "frosinone": "Frosinone",
    "us cremonese": "Cremonese", "cremonese": "Cremonese",
    "us catanzaro 1929": "Catanzaro", "catanzaro": "Catanzaro",
    "palermo fc": "Palermo", "palermo": "Palermo",
    "uc sampdoria": "Sampdoria", "sampdoria": "Sampdoria",
    "brescia calcio": "Brescia", "brescia": "Brescia",
    "fc südtirol": "Südtirol", "fc sudtirol": "Südtirol", "südtirol": "Südtirol",
    "ac pisa 1909": "Pisa", "pisa sc": "Pisa", "pisa": "Pisa",
    "uc reggiana 1919": "Reggiana", "reggiana": "Reggiana",
    "modena fc 2018": "Modena", "modena fc": "Modena", "modena": "Modena",
    "ssc bari": "Bari", "bari": "Bari",
    "cosenza calcio": "Cosenza", "cosenza": "Cosenza",
    "spezia calcio": "Spezia", "spezia": "Spezia",
    "as cittadella": "Cittadella", "cittadella": "Cittadella",
    "cesena fc": "Cesena", "cesena": "Cesena",
    "ss juve stabia": "Juve Stabia", "juve stabia": "Juve Stabia",
    "carrarese calcio 1908": "Carrarese", "carrarese": "Carrarese",
    "mantova 1911": "Mantova", "mantova": "Mantova",
    # --- CHAMPIONS / EUROPA LEAGUE (nomi internazionali comuni) ---
    "fc barcelona": "Barcelona", "barcelona": "Barcelona",
    "real madrid cf": "Real Madrid", "real madrid": "Real Madrid",
    "manchester city fc": "Man City", "manchester city": "Man City",
    "liverpool fc": "Liverpool", "liverpool": "Liverpool",
    "fc bayern münchen": "Bayern", "fc bayern munich": "Bayern", "bayern munich": "Bayern",
    "borussia dortmund": "Dortmund",
    "paris saint-germain fc": "PSG", "paris saint-germain": "PSG", "psg": "PSG",
    "atletico de madrid": "Atlético", "atletico madrid": "Atlético",
    "chelsea fc": "Chelsea", "chelsea": "Chelsea",
    "arsenal fc": "Arsenal", "arsenal": "Arsenal",
    "manchester united fc": "Man United", "manchester united": "Man United",
    "tottenham hotspur fc": "Tottenham", "tottenham hotspur": "Tottenham",
    "bayer 04 leverkusen": "Leverkusen", "bayer leverkusen": "Leverkusen",
    "rb leipzig": "RB Leipzig",
    "porto fc": "Porto", "fc porto": "Porto",
    "benfica": "Benfica", "sl benfica": "Benfica",
    "sporting cp": "Sporting CP",
    "ajax": "Ajax", "afc ajax": "Ajax",
    "psv eindhoven": "PSV",
    "villarreal cf": "Villarreal",
    "sevilla fc": "Sevilla", "sevilla": "Sevilla",
    "valencia cf": "Valencia",
    "real sociedad": "Real Sociedad",
    "ac milan": "Milan",
    "ssc napoli": "Napoli",
    "juventus fc": "Juventus",
    "fc internazionale milano": "Inter",
    "as roma": "Roma",
    "ss lazio": "Lazio",
    "atalanta bc": "Atalanta",
    "acf fiorentina": "Fiorentina",
    "celtic fc": "Celtic", "celtic": "Celtic",
    "rangers fc": "Rangers",
    "club brugge kv": "Club Brugge", "club brugge": "Club Brugge",
    "shakhtar donetsk": "Shakhtar",
    "dynamo kyiv": "Dynamo Kyiv",
    "red bull salzburg": "Salzburg", "fc red bull salzburg": "Salzburg",
    "eintracht frankfurt": "Frankfurt",
    "vfl wolfsburg": "Wolfsburg",
    "borussia mönchengladbach": "M'gladbach",
    "sc freiburg": "Freiburg",
    "union berlin": "Union Berlin", "1. fc union berlin": "Union Berlin",
    "olympique lyonnais": "Lyon", "olympique de marseille": "Marseille",
    "stade rennais fc": "Rennes",
    "losc lille": "Lille", "lille": "Lille",
    "rc lens": "Lens",
    "monaco": "Monaco", "as monaco": "Monaco",
    "fenerbahçe sk": "Fenerbahçe", "fenerbahce sk": "Fenerbahçe",
    "galatasaray sk": "Galatasaray",
    "besiktas jk": "Beşiktaş",
    "trabzonspor": "Trabzonspor",
    "olympiakos fc": "Olympiakos",
    "panathinaikos fc": "Panathinaikos",
    "slavia prague": "Slavia Praha", "sk slavia prague": "Slavia Praha",
    "sparta prague": "Sparta Praha", "ac sparta prague": "Sparta Praha",
    "viktoria plzen": "Plzeň",
    "fk crvena zvezda": "Stella Rossa", "red star belgrade": "Stella Rossa",
    "fk dinamo zagreb": "Dinamo Zagreb", "gnk dinamo zagreb": "Dinamo Zagreb",
    "bsc young boys": "Young Boys",
    "fk shakhtar donetsk": "Shakhtar",
    "west ham united fc": "West Ham", "west ham united": "West Ham",
    "aston villa fc": "Aston Villa", "aston villa": "Aston Villa",
    "newcastle united fc": "Newcastle", "newcastle united": "Newcastle",
    "brighton & hove albion fc": "Brighton",
}

# Configurazione competizioni
COMPETIZIONI = {
    "SA":  {"codice": "SA",  "nome": "Serie A",           "giornate": 38, "squadre": 20},
    "UCL": {"codice": "CL",  "nome": "Champions League",  "giornate": 8,  "squadre": 36},
    "UEL": {"codice": "EL",  "nome": "Europa League",     "giornate": 8,  "squadre": 36},
}

def genera_json_classifica():
    api_token = os.environ.get('FOOTBALL_API_KEY') or os.environ.get('FOOTBALL_DATA_API_TOKEN')
    if not api_token:
        print("❌ Errore: Nessun API Token trovato nei secrets (controlla FOOTBALL_API_KEY).")
        return

    comp_key = os.environ.get("COMPETITION", "SA").upper()
    comp = COMPETIZIONI.get(comp_key)
    if not comp:
        print(f"❌ Competizione non riconosciuta: {comp_key}. Usa SA, UCL o UEL.")
        return

    url = f"https://api.football-data.org/v4/competitions/{comp['codice']}/standings"
    headers = {"X-Auth-Token": api_token}

    print(f"📡 Recupero classifica: {comp['nome']} ({comp['codice']})...")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()

            giornata_attuale = 1
            if 'season' in data and 'currentMatchday' in data['season']:
                giornata_attuale = data['season']['currentMatchday']
            elif 'filters' in data and 'matchday' in data['filters']:
                giornata_attuale = data['filters']['matchday']

            standings = data['standings'][0]['table']
            classifica_pulita = []

            for team_data in standings:
                nome_api = team_data['team']['name']
                nome_api_lower = nome_api.lower().strip()
                nome_it = MAPPA_NOMI.get(nome_api_lower, nome_api)

                if "juventus" in nome_api_lower or "next gen" in nome_api_lower:
                    logo_url = "https://upload.wikimedia.org/wikipedia/commons/9/99/Juventus_FC_2017_squared_icon_%28white%29.png"
                    if "next gen" in nome_api_lower:
                        nome_it = "Juve Next Gen"
                else:
                    logo_url = team_data['team']['crest']

                classifica_pulita.append({
                    "pos":    team_data['position'],
                    "team":   nome_it,
                    "logo":   logo_url,
                    "pt":     team_data['points'],
                    "p":      team_data['playedGames'],
                    "v":      team_data['won'],
                    "n":      team_data['draw'],
                    "p_pers": team_data['lost'],
                    "gf":     team_data['goalsFor'],
                    "gs":     team_data['goalsAgainst'],
                    "dr":     team_data['goalDifference']
                })

            output_finale = {
                "competition": comp_key,
                "competition_name": comp['nome'],
                "giornata": giornata_attuale,
                "classifica": classifica_pulita
            }

            with open('classifica.json', 'w', encoding='utf-8') as f:
                json.dump(output_finale, f, ensure_ascii=False, indent=4)
            print(f"✅ JSON salvato: {comp['nome']} – Giornata {giornata_attuale} ({len(classifica_pulita)} squadre).")
        else:
            print(f"❌ Errore API: {response.status_code} — {response.text}")
    except Exception as e:
        print(f"❌ Eccezione durante la chiamata API: {e}")

if __name__ == "__main__":
    genera_json_classifica()
