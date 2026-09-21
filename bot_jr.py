"""Menu Telegram attivo soltanto durante una run manuale di GitHub Actions."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


COMPETIZIONI = {
    "SA": "Serie A",
    "UCL": "Champions League",
    "UEL": "Europa League",
    "UECL": "Conference League",
}
DESTINAZIONI = {"bot_jr": "Bot JR", "juventus_reborn": "Juventus Reborn"}
STATO_PATH = Path(".bot-jr-menu.json")
ATTESA_SECONDI = 600


class TelegramError(RuntimeError):
    pass


class TelegramAPI:
    def __init__(self, token):
        self.token = token

    def call(self, method, **params):
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/{method}",
            data=json.dumps(params).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=params.get("timeout", 0) + 15) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            # Non stampare l'URL della richiesta: contiene il token del bot.
            raise TelegramError(f"Telegram {method}: errore HTTP {exc.code}.") from None
        except (OSError, ValueError):
            raise TelegramError(f"Telegram {method}: rete o risposta non disponibile.") from None
        if not payload.get("ok"):
            raise TelegramError(f"Telegram {method}: operazione rifiutata.")
        return payload.get("result")


def menu(competition, destination, page="home"):
    if page in {"competition", "destination"}:
        choices = COMPETIZIONI if page == "competition" else DESTINAZIONI
        selected = competition if page == "competition" else destination
        rows = [[{"text": ("✅ " if code == selected else "") + name,
                  "callback_data": f"{page}:{code}"}] for code, name in choices.items()]
        rows.append([{"text": "↩️ Indietro", "callback_data": "back"}])
    else:
        rows = [[
            {"text": COMPETIZIONI.get(competition, "Scegli classifica"),
             "callback_data": "choose:competition"},
            {"text": DESTINAZIONI[destination],
             "callback_data": "choose:destination"},
        ], [{"text": "📤 Invia", "callback_data": "send"}]]
    return {
        "text": (
            "📊 Scegli la classifica da inviare\n\n"
            f"Classifica: {COMPETIZIONI.get(competition, 'da scegliere')}\n"
            f"Destinazione: {DESTINAZIONI[destination]}\n\n"
            "Usa i due pulsanti per cambiare classifica e destinazione, poi premi Invia.\n"
            "Il menu scade dopo 10 minuti."
        ),
        "reply_markup": {"inline_keyboard": rows},
    }


def chiudi_menu(api, state, text):
    api.call(
        "editMessageText", chat_id=state["chat_id"], message_id=state["message_id"],
        text=text, reply_markup={"inline_keyboard": []},
    )


def scegli_classifica(api, chat_id, state_path=None):
    if api.call("getWebhookInfo").get("url"):
        raise TelegramError(
            "Il bot ha gia' un webhook attivo. Il menu richiede un bot senza "
            "webhook e senza altri processi getUpdates in ascolto."
        )
    competition = None
    destination = "juventus_reborn"
    page = "home"
    message = api.call("sendMessage", chat_id=chat_id, **menu(competition, destination))
    state = {"chat_id": message["chat"]["id"], "message_id": message["message_id"]}
    if state_path is not None:
        state_path.write_text(json.dumps(state), encoding="utf-8")
    print("Menu inviato a Bot JR. Attendo classifica, destinazione e invio (10 minuti).")
    deadline = time.monotonic() + ATTESA_SECONDI
    offset = 0
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                chiudi_menu(api, state, "⌛ Tempo scaduto. Nessuna classifica inviata. Avvia di nuovo il workflow.")
                return None
            updates = api.call(
                "getUpdates", offset=offset, timeout=min(25, max(1, int(remaining))),
                allowed_updates=["callback_query"],
            )
            for update in updates:
                offset = max(offset, update["update_id"] + 1)
                query = update.get("callback_query", {})
                source = query.get("message", {})
                if (source.get("chat", {}).get("id") != state["chat_id"]
                        or source.get("message_id") != state["message_id"]):
                    continue
                data = query.get("data", "")
                old_choices = (competition, destination, page)
                if data in {"choose:competition", "choose:destination", "back"}:
                    page = "home" if data == "back" else data[7:]
                elif data.startswith("competition:") and data[12:] in COMPETIZIONI:
                    competition = data[12:]
                    page = "home"
                elif data.startswith("destination:") and data[12:] in DESTINAZIONI:
                    destination = data[12:]
                    page = "home"
                elif data == "send" and competition:
                    api.call("answerCallbackQuery", callback_query_id=query["id"], text="Preparo la classifica…")
                    state.update(competition=competition, destination=destination)
                    api.call("deleteMessage", chat_id=state["chat_id"], message_id=state["message_id"])
                    state["menu_deleted"] = True
                    if state_path is not None:
                        state_path.write_text(json.dumps(state), encoding="utf-8")
                    return state
                else:
                    api.call("answerCallbackQuery", callback_query_id=query["id"],
                             text="Seleziona prima una classifica." if data == "send" else
                                  "Usa i pulsanti di questo menu.", show_alert=True)
                    continue
                api.call("answerCallbackQuery", callback_query_id=query["id"])
                # Telegram rifiuta editMessageText se il contenuto non cambia.
                if old_choices != (competition, destination, page):
                    api.call("editMessageText", chat_id=state["chat_id"],
                             message_id=state["message_id"], **menu(competition, destination, page))
    except TelegramError:
        try:
            chiudi_menu(api, state, "❌ Menu interrotto. Nessuna classifica inviata. Avvia di nuovo il workflow.")
        except TelegramError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=("failed", "cancelled"))
    args = parser.parse_args()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramError("Secret TELEGRAM_BOT_TOKEN mancante.")
    api = TelegramAPI(token)
    if args.status:
        if not STATO_PATH.exists():
            return 0
        state = json.loads(STATO_PATH.read_text(encoding="utf-8"))
        text = {
            "failed": "❌ Invio non completato. Controlla la run su GitHub e riprova.",
            "cancelled": "⏹ Workflow annullato. Avvia una nuova run per richiedere una classifica.",
        }[args.status]
        if state.get("menu_deleted"):
            api.call("sendMessage", chat_id=state["chat_id"], text=text)
        else:
            chiudi_menu(api, state, text)
        return 0

    chat_id = os.environ.get("TELEGRAM_CHAT_ID_BOT_JR", "").strip()
    channel_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id or not channel_id:
        raise TelegramError("Configura TELEGRAM_CHAT_ID_BOT_JR e TELEGRAM_CHAT_ID prima di avviare il menu.")
    selection = scegli_classifica(api, chat_id, STATO_PATH)
    if selection is None:
        print("Menu scaduto: termino senza generare o inviare immagini.")
        return 0
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write(f"competition={selection['competition']}\ndestination={selection['destination']}\n")
    print(f"Scelta: {COMPETIZIONI[selection['competition']]} → {DESTINAZIONI[selection['destination']]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TelegramError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1)
