import unittest
from unittest.mock import patch

import bot_jr


def callback(update_id, data, chat_id=101, message_id=50):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": str(update_id),
            "from": {"id": 7, "is_bot": False, "first_name": "Tester"},
            "chat_instance": "test-chat",
            "message": {
                "message_id": message_id,
                "date": 123456,
                "chat": {"id": chat_id, "type": "private"},
            },
            "data": data,
        },
    }


class FakeTelegram:
    """Simula solo il confine Telegram; menu e selezione sono codice reale."""

    def __init__(self, batches=(), webhook=""):
        self.batches = iter(batches)
        self.webhook = webhook
        self.calls = []

    def call(self, method, **params):
        self.calls.append((method, params))
        if method == "getWebhookInfo":
            return {"url": self.webhook, "has_custom_certificate": False,
                    "pending_update_count": 0}
        if method == "sendMessage":
            return {"message_id": 50, "date": 123456,
                    "chat": {"id": 101, "type": "private"},
                    "text": params["text"]}
        if method == "getUpdates":
            return next(self.batches, [])
        return True


class BotJRTests(unittest.TestCase):
    def choose(self, api, **kwargs):
        return bot_jr.scegli_classifica(api, "101", **kwargs)

    def test_every_competition_can_be_sent_to_either_destination(self):
        for competition in ("SA", "UCL", "UEL", "UECL"):
            for destination in ("bot_jr", "juventus_reborn"):
                with self.subTest(competition=competition, destination=destination):
                    api = FakeTelegram([
                        [callback(1, f"competition:{competition}")],
                        [callback(2, f"destination:{destination}")],
                        [callback(3, "send")],
                    ])
                    selection = self.choose(api)
                    self.assertEqual(selection["competition"], competition)
                    self.assertEqual(selection["destination"], destination)
                    self.assertEqual(selection["message_id"], 50)

    def test_menu_starts_without_competition_and_defaults_to_juventus_reborn(self):
        api = FakeTelegram([
            [callback(1, "choose:competition"), callback(2, "competition:UEL")],
            [callback(3, "choose:destination"), callback(4, "destination:juventus_reborn")],
            [callback(5, "send")],
        ])
        selection = self.choose(api)
        self.assertEqual(selection["destination"], "juventus_reborn")
        menus = [params for _, params in api.calls
                 if params.get("reply_markup", {}).get("inline_keyboard")]
        first_buttons = [button for row in menus[0]["reply_markup"]["inline_keyboard"]
                         for button in row]
        self.assertEqual(len(first_buttons), 3)
        self.assertEqual("Scegli classifica", first_buttons[0]["text"])
        self.assertIn("Juventus Reborn", first_buttons[1]["text"])
        self.assertEqual([button["callback_data"] for button in first_buttons],
                         ["choose:competition", "choose:destination", "send"])
        competition_buttons = [button for row in menus[1]["reply_markup"]["inline_keyboard"]
                               for button in row]
        self.assertEqual(
            {button["callback_data"] for button in competition_buttons
             if button["callback_data"].startswith("competition:")},
            {"competition:SA", "competition:UCL", "competition:UEL", "competition:UECL"},
        )
        self.assertFalse(any(button["text"].startswith("✅") for button in competition_buttons
                             if button["callback_data"].startswith("competition:")))
        destination_buttons = [button for row in menus[3]["reply_markup"]["inline_keyboard"]
                               for button in row]
        self.assertEqual([button["callback_data"] for button in destination_buttons
                          if button["text"].startswith("✅")],
                         ["destination:juventus_reborn"])
        self.assertEqual(api.calls[-1], ("deleteMessage", {"chat_id": 101, "message_id": 50}))

    def test_ignores_other_chats_old_menus_and_out_of_order_choices(self):
        api = FakeTelegram([
            [callback(1, "competition:SA", chat_id=999),
             callback(2, "competition:SA", message_id=49),
             callback(3, "send"),
             callback(4, "competition:BAD"),
             callback(5, "competition:UCL")],
            [callback(6, "destination:unknown"),
             callback(7, "destination:juventus_reborn"),
             callback(8, "send")],
        ])
        selection = self.choose(api)
        self.assertEqual(selection["competition"], "UCL")
        self.assertEqual(selection["destination"], "juventus_reborn")
        polls = [params for method, params in api.calls if method == "getUpdates"]
        self.assertEqual(polls[1]["offset"], 6)
        answers = [params["callback_query_id"] for method, params in api.calls
                   if method == "answerCallbackQuery"]
        self.assertNotIn("1", answers)
        self.assertNotIn("2", answers)
        alert = next(params for method, params in api.calls
                     if method == "answerCallbackQuery" and params["callback_query_id"] == "3")
        self.assertTrue(alert["show_alert"])

    def test_back_and_changing_both_choices_before_sending(self):
        api = FakeTelegram([
            [callback(1, "choose:competition"), callback(2, "back"),
             callback(3, "choose:destination"), callback(4, "destination:bot_jr"),
             callback(5, "choose:competition"), callback(6, "competition:SA"),
             callback(7, "choose:competition"), callback(8, "competition:UECL"),
             callback(9, "choose:destination"), callback(10, "destination:juventus_reborn"),
             callback(11, "send")],
        ])
        selection = self.choose(api)
        self.assertEqual((selection["competition"], selection["destination"]),
                         ("UECL", "juventus_reborn"))
        self.assertEqual(api.calls[-1][0], "deleteMessage")

    def test_timeout_removes_buttons_without_selecting_a_default(self):
        api = FakeTelegram()
        with patch("bot_jr.time.monotonic", side_effect=[0, 601]):
            self.assertIsNone(self.choose(api))
        self.assertEqual(api.calls[-1][0], "editMessageText")
        self.assertEqual(api.calls[-1][1]["reply_markup"]["inline_keyboard"], [])

    def test_existing_webhook_is_not_overwritten(self):
        api = FakeTelegram(webhook="https://example.com/existing-bot")
        with self.assertRaises(bot_jr.TelegramError):
            self.choose(api)
        self.assertEqual([method for method, _ in api.calls], ["getWebhookInfo"])

    def test_send_uses_current_choices_and_stops_after_the_first_send(self):
        api = FakeTelegram([
            [callback(1, "competition:SA"), callback(2, "competition:UCL")],
            [callback(3, "destination:bot_jr"), callback(4, "send"),
             callback(5, "destination:juventus_reborn"), callback(6, "send")],
        ])
        selection = self.choose(api)
        self.assertEqual(selection["destination"], "bot_jr")
        self.assertEqual(selection["competition"], "UCL")

    def test_poll_failure_disables_the_menu_and_propagates_failure(self):
        api = FakeTelegram()
        original_call = api.call

        def fail_poll(method, **params):
            if method == "getUpdates":
                raise bot_jr.TelegramError("Errore di rete")
            return original_call(method, **params)

        api.call = fail_poll
        with self.assertRaises(bot_jr.TelegramError):
            self.choose(api)
        self.assertEqual(api.calls[-1][1]["reply_markup"]["inline_keyboard"], [])


if __name__ == "__main__":
    unittest.main()
