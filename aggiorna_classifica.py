import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests


# Le URL correnti senza ID seguono automaticamente la stagione attiva scelta
# da Diretta.it. Durante i test delle coppe si usano classifiche archiviate e
# complete: al 24 agosto 2026 le pagine 2026/27 mostrano ancora soltanto i
# tabelloni delle qualificazioni, non la classifica della fase campionato.
COMPETIZIONI = {
    "SA": {
        "nome": "Serie A",
        "url": "https://www.diretta.it/serie-a/classifiche/",
        "test_url": "https://www.diretta.it/serie-a/classifiche/",
        "giornate": 38,
        "squadre": 20,
    },
    "UCL": {
        "nome": "Champions League",
        "url": (
            "https://www.diretta.it/calcio/europa/"
            "champions-league/classifiche/"
        ),
        "test_url": (
            "https://www.diretta.it/calcio/europa/"
            "champions-league-2025-2026/classifiche/"
        ),
        "giornate": 8,
        "squadre": 36,
    },
    "UEL": {
        "nome": "Europa League",
        "url": (
            "https://www.diretta.it/calcio/europa/"
            "europa-league/classifiche/"
        ),
        "test_url": (
            "https://www.diretta.it/calcio/europa/"
            "europa-league-2025-2026/classifiche/"
        ),
        "giornate": 8,
        "squadre": 36,
    },
    "UECL": {
        "nome": "Conference League",
        "url": (
            "https://www.diretta.it/calcio/europa/"
            "conference-league/classifiche/"
        ),
        "test_url": (
            "https://www.diretta.it/calcio/europa/"
            "conference-league-2025-2026/classifiche/"
        ),
        "giornate": 6,
        "squadre": 36,
    },
}

TEAM_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.7",
}

# La tabella usa icone 30x30. La pagina della squadra, sempre su Diretta.it,
# espone invece lo stesso stemma nella variante heading__logo da 100x100.
LOGO_GRANDE_RE = re.compile(
    r'<img\b(?=[^>]*\bclass=["\'][^"\']*\bheading__logo\b[^"\']*["\'])'
    r'(?=[^>]*\bsrc=["\']([^"\']+)["\'])[^>]*>',
    re.IGNORECASE,
)

# Uniche eccezioni richieste: tutti gli altri stemmi restano quelli grandi di
# Diretta.it. Il file Juventus e' l'originale 3359x3359 collegato da Wikipedia;
# quello Roma e' la risorsa 512x512 indicata dall'utente.
LOGHI_PERSONALIZZATI = {
    "juventus": (
        "https://upload.wikimedia.org/wikipedia/commons/9/99/"
        "Juventus_FC_2017_squared_icon_%28white%29.png"
    ),
    "roma": "https://assets.football-logos.cc/logos/italy/512x512/roma.8dfa8968.png",
    "as roma": "https://assets.football-logos.cc/logos/italy/512x512/roma.8dfa8968.png",
}


def carica_mappa_nomi() -> tuple[dict, dict]:
    """Carica le correzioni dei nomi da teams.json, se disponibili."""
    path = Path(__file__).parent / "teams.json"
    try:
        with open(path, encoding="utf-8") as file:
            raw = json.load(file)
    except FileNotFoundError:
        print("⚠️  teams.json non trovato: uso i nomi di Diretta.it.")
        return {}, {}
    except Exception as exc:
        print(f"⚠️  Impossibile leggere teams.json ({exc}): uso i nomi di Diretta.it.")
        return {}, {}

    esatta: dict[str, str] = {}
    minuscola: dict[str, str] = {}
    for nome_sorgente, valori in raw.items():
        corretto = (
            valori[0]
            if isinstance(valori, list) and valori
            else nome_sorgente
        )
        esatta[nome_sorgente] = corretto
        minuscola[nome_sorgente.lower().strip()] = corretto
    return esatta, minuscola


MAPPA_NOMI, MAPPA_NOMI_LOWER = carica_mappa_nomi()


def nome_corretto(source_name: str) -> str:
    """Applica l'eventuale correzione del nome definita in teams.json."""
    if not source_name:
        return source_name
    if source_name in MAPPA_NOMI:
        return MAPPA_NOMI[source_name]
    return MAPPA_NOMI_LOWER.get(source_name.lower().strip(), source_name)


def format_stagione(anno_inizio) -> str:
    """Converte l'anno iniziale 2026 nella stagione breve 2026/27."""
    try:
        anno = int(anno_inizio)
    except (TypeError, ValueError):
        return ""
    if anno < 1900 or anno > 2100:
        return ""
    return f"{anno}/{(anno + 1) % 100:02d}"


def stagione_da_testo(testo: str) -> str:
    """Estrae la stagione da testi come 'Champions League 2025/2026'."""
    match = re.search(r"(19|20)\d{2}", testo or "")
    return format_stagione(match.group()) if match else ""


def stagione_corrente_da_data() -> str:
    """Fallback della stagione quando Diretta.it non la espone nel titolo."""
    oggi = date.today()
    anno_inizio = oggi.year if oggi.month >= 7 else oggi.year - 1
    return format_stagione(anno_inizio)


def _intero(valore, campo: str, squadra: str) -> int:
    """Converte un valore numerico della tabella e produce errori leggibili."""
    try:
        return int(str(valore).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"valore non valido per {campo} di {squadra}: {valore!r}"
        ) from exc


def _logo_grande_diretta(team_url: str, fallback: str) -> str:
    """Recupera dalla pagina squadra lo stemma Diretta.it da 100x100."""
    if not team_url:
        return fallback
    try:
        response = requests.get(
            urljoin("https://www.diretta.it/", team_url),
            headers=TEAM_PAGE_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        match = LOGO_GRANDE_RE.search(response.text)
        if match:
            return urljoin(response.url, match.group(1))
    except Exception as exc:
        print(f"⚠️  Logo grande non disponibile per {team_url}: {exc}")
    return fallback


def _logo_personalizzato(nome_squadra: str) -> str:
    return LOGHI_PERSONALIZZATI.get(nome_squadra.strip().lower(), "")


def _loghi_grandi_diretta(raw_rows: list[dict]) -> list[str]:
    """Scarica in parallelo le varianti grandi, mantenendo l'ordine delle righe."""
    if not raw_rows:
        return []
    workers = min(8, len(raw_rows))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        loghi = list(executor.map(
            lambda raw: (
                _logo_personalizzato(raw.get("team", ""))
                or _logo_grande_diretta(
                    raw.get("team_url", ""),
                    raw.get("logo", ""),
                )
            ),
            raw_rows,
        ))

    trovati = sum(
        logo and logo != raw.get("logo", "")
        for logo, raw in zip(loghi, raw_rows)
    )
    print(
        f"🖼️  Loghi ad alta risoluzione: "
        f"{trovati}/{len(raw_rows)}."
    )
    if trovati != len(raw_rows):
        raise RuntimeError(
            "non tutte le squadre espongono il logo Diretta.it da 100x100; "
            "interrompo per evitare un'immagine con stemmi sgranati"
        )
    return loghi


def scrape_standings_diretta(url: str) -> tuple[list, int, str] | None:
    """Legge una classifica dal DOM renderizzato di Diretta.it.

    La pagina carica la tabella tramite JavaScript, quindi viene usato Chromium
    headless, gia' installato dai workflow per creare lo screenshot Telegram.
    I loghi vengono copiati direttamente dalla tabella di Diretta.it senza
    override personalizzati.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage"],
            )
            try:
                context = browser.new_context(
                    locale="it-IT",
                    timezone_id="Europe/Rome",
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)

                rows = page.locator(".ui-table__body .ui-table__row")
                rows.first.wait_for(state="visible", timeout=45_000)

                raw_rows = rows.evaluate_all(
                    """
                    rows => rows.map(row => ({
                        pos: row.querySelector('.tableCellRank')?.textContent?.trim() || '',
                        team: row.querySelector('.tableCellParticipant__name')?.textContent?.trim() || '',
                        team_url: row.querySelector('.tableCellParticipant__name')?.href || '',
                        logo: row.querySelector('.tableCellParticipant__image img')?.src || '',
                        values: [...row.querySelectorAll('span.table__cell--value')]
                            .map(cell => cell.textContent.trim())
                    }))
                    """
                )
                titolo = page.locator("h1").first.inner_text(timeout=10_000)
                resolved_url = page.url
            finally:
                browser.close()
    except Exception as exc:
        print(f"❌ Errore durante l'estrazione da Diretta.it: {exc}")
        return None

    try:
        classifica = []
        loghi_grandi = _loghi_grandi_diretta(raw_rows)
        for raw, logo_grande in zip(raw_rows, loghi_grandi):
            squadra_originale = raw.get("team", "").strip()
            valori = raw.get("values", [])
            if not squadra_originale or len(valori) < 7:
                raise ValueError(f"riga incompleta: {raw!r}")

            posizione_testo = re.sub(r"\D", "", raw.get("pos", ""))
            if not posizione_testo:
                raise ValueError(f"posizione mancante per {squadra_originale}")

            pld = _intero(valori[0], "partite", squadra_originale)
            won = _intero(valori[1], "vittorie", squadra_originale)
            draw = _intero(valori[2], "pareggi", squadra_originale)
            lost = _intero(valori[3], "sconfitte", squadra_originale)
            score_match = re.fullmatch(r"(\d+)\s*:\s*(\d+)", valori[4])
            if not score_match:
                raise ValueError(
                    f"reti non valide per {squadra_originale}: {valori[4]!r}"
                )
            gf, ga = map(int, score_match.groups())
            dr = _intero(valori[5], "differenza reti", squadra_originale)
            points = _intero(valori[6], "punti", squadra_originale)

            if pld != won + draw + lost:
                raise ValueError(
                    f"totale partite incoerente per {squadra_originale}: "
                    f"{pld} != {won}+{draw}+{lost}"
                )
            if dr != gf - ga:
                raise ValueError(
                    f"differenza reti incoerente per {squadra_originale}: "
                    f"{dr} != {gf}-{ga}"
                )

            # Variante grande Diretta.it, salvo le sole eccezioni Juventus/Roma.
            logo = logo_grande
            classifica.append({
                "pos": int(posizione_testo),
                "team": nome_corretto(squadra_originale),
                "logo": logo,
                "logo_light_bg": logo,
                "logo_dark_bg": logo,
                "pt": points,
                "p": pld,
                "v": won,
                "n": draw,
                "p_pers": lost,
                "gf": gf,
                "gs": ga,
                "dr": dr,
            })

        classifica.sort(key=lambda row: row["pos"])
        posizioni = [row["pos"] for row in classifica]
        if posizioni != list(range(1, len(classifica) + 1)):
            raise ValueError(f"posizioni non consecutive: {posizioni}")
        if len({row["team"] for row in classifica}) != len(classifica):
            raise ValueError("la tabella contiene squadre duplicate")

        giornata = max((row["p"] for row in classifica), default=0) or 1
        stagione = stagione_da_testo(titolo)
        print(f"🌐 Pagina risolta: {resolved_url}")
        return classifica, giornata, stagione
    except Exception as exc:
        print(f"❌ Formato classifica Diretta.it non valido: {exc}")
        return None


def _env_true(nome: str) -> bool:
    return os.environ.get(nome, "").strip().lower() in {"1", "true", "yes", "on"}


def genera_json_classifica():
    comp_key = os.environ.get("COMPETITION", "SA").upper()
    comp = COMPETIZIONI.get(comp_key)
    if not comp:
        print(f"❌ Competizione non riconosciuta: {comp_key}. Usa SA, UCL, UEL o UECL.")
        sys.exit(1)

    test_only = _env_true("TEST_ONLY")
    url_override = os.environ.get("DIRETTA_STANDINGS_URL", "").strip()
    url = url_override or (comp["test_url"] if test_only else comp["url"])

    modalita = "test senza Telegram" if test_only else "produzione"
    print(
        f"📡 Recupero classifica Diretta.it: {comp['nome']} "
        f"({comp_key}, {modalita})..."
    )
    if test_only and url == comp["test_url"] and url != comp["url"]:
        print("ℹ️  Test europeo su classifica completa archiviata 2025/26.")

    risultato = scrape_standings_diretta(url)
    if risultato is None:
        print("❌ Impossibile recuperare la classifica da Diretta.it.")
        sys.exit(1)
    classifica, giornata, stagione = risultato

    squadre_attese = comp["squadre"]
    if len(classifica) != squadre_attese:
        print(
            f"❌ Numero di squadre inatteso: {len(classifica)} "
            f"(attese {squadre_attese})."
        )
        sys.exit(1)

    if not stagione:
        stagione = stagione_corrente_da_data()
        print(
            "⚠️  Stagione non trovata nella pagina: "
            f"uso il fallback da data ({stagione})."
        )

    output = {
        "competition": comp_key,
        "competition_name": comp["nome"],
        "giornata": giornata,
        "stagione": stagione,
        "classifica": classifica,
    }

    with open("classifica.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=4)

    print(
        f"✅ JSON salvato: {comp['nome']} – Giornata {giornata} – "
        f"Stagione {stagione} ({len(classifica)} squadre)."
    )
    if test_only:
        for row in classifica:
            print(f"{row['pos']:>2}. {row['team']:<22} {row['pt']:>3} pt")


if __name__ == "__main__":
    genera_json_classifica()
