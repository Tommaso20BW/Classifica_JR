import json
import os
import sys
import time
import urllib.error
import urllib.request


WORKFLOW_BOT = {
    "SerieA.yml",
    "ChampionsLeague.yml",
    "EuropaLeague.yml",
    "ConferenceLeague.yml",
}
STATI_ATTIVI = {"queued", "in_progress", "requested", "waiting", "pending"}
INTERVALLO_SECONDI = 15
ATTESA_MASSIMA_SECONDI = 5 * 60 * 60


def nome_workflow(run: dict) -> str:
    path = str(run.get("path", "")).split("@", 1)[0]
    return path.rsplit("/", 1)[-1]


def run_precedenti_attivi(runs: list[dict], run_corrente: int) -> list[dict]:
    precedenti = [
        run
        for run in runs
        if int(run.get("id", 0)) < run_corrente
        and run.get("status") in STATI_ATTIVI
        and nome_workflow(run) in WORKFLOW_BOT
    ]
    return sorted(precedenti, key=lambda run: int(run["id"]))


def recupera_run(repository: str, token: str) -> list[dict]:
    url = (
        f"https://api.github.com/repos/{repository}/actions/runs"
        "?per_page=100&exclude_pull_requests=true"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Classifica_JR-workflow-queue",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload.get("workflow_runs", [])


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    run_id_raw = os.environ.get("GITHUB_RUN_ID", "").strip()
    if not repository or not token or not run_id_raw.isdigit():
        print(
            "❌ Variabili GitHub mancanti: impossibile gestire la coda.",
            file=sys.stderr,
        )
        return 1

    run_corrente = int(run_id_raw)
    inizio = time.monotonic()
    ultima_coda: tuple[int, ...] | None = None
    print(f"🔒 Controllo coda condivisa dei quattro bot (run {run_corrente}).")

    while True:
        if time.monotonic() - inizio > ATTESA_MASSIMA_SECONDI:
            print("❌ Tempo massimo di attesa della coda superato.", file=sys.stderr)
            return 1

        try:
            runs = recupera_run(repository, token)
            precedenti = run_precedenti_attivi(runs, run_corrente)
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            print(f"⚠️  API GitHub temporaneamente non disponibile: {exc}")
            time.sleep(INTERVALLO_SECONDI)
            continue

        if not precedenti:
            print("✅ Turno disponibile: il workflow può proseguire.")
            return 0

        coda = tuple(int(run["id"]) for run in precedenti)
        if coda != ultima_coda:
            descrizione = ", ".join(
                f"{nome_workflow(run)} #{run['id']} ({run['status']})"
                for run in precedenti
            )
            print(f"⏳ Attendo la fine dei run precedenti: {descrizione}")
            ultima_coda = coda
        time.sleep(INTERVALLO_SECONDI)


if __name__ == "__main__":
    raise SystemExit(main())
