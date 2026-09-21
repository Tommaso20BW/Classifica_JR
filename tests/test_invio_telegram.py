from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import screenshot_telegram


class InvioTelegramTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.photo = Path(temporary.name) / "classifica.png"
        self.photo.write_bytes(b"test-image")
        for name, value in {"TELEGRAM_TOKEN": "test-token",
                            "TELEGRAM_CHAT_ID": "selected-chat",
                            "OUTPUT_PATH": str(self.photo)}.items():
            patcher = patch.object(screenshot_telegram, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_http_failure_fails_the_workflow_instead_of_reporting_success(self):
        response = Mock(status_code=403, text="Forbidden")
        response.json.return_value = {"ok": False, "error_code": 403}
        with patch.object(screenshot_telegram.requests, "post", return_value=response):
            with self.assertRaises(RuntimeError):
                screenshot_telegram.invia_telegram(3, "UCL")

    def test_api_failure_in_successful_http_response_also_fails(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": False, "error_code": 400}
        with patch.object(screenshot_telegram.requests, "post", return_value=response):
            with self.assertRaises(RuntimeError):
                screenshot_telegram.invia_telegram(3, "UCL")

    def test_sends_only_one_photo_to_the_selected_chat_with_selected_caption(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True, "result": {
            "photo": [{"file_id": "photo", "width": 1920, "height": 2560}]}}
        with patch.object(screenshot_telegram.requests, "post", return_value=response) as post:
            screenshot_telegram.invia_telegram(3, "UEL")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["data"]["chat_id"], "selected-chat")
        self.assertIn("UEL", post.call_args.kwargs["data"]["caption"])
        self.assertIn("3ª Giornata", post.call_args.kwargs["data"]["caption"])

    def test_missing_destination_does_not_send(self):
        with patch.object(screenshot_telegram, "TELEGRAM_CHAT_ID", ""):
            with patch.object(screenshot_telegram.requests, "post") as post:
                with self.assertRaises(RuntimeError):
                    screenshot_telegram.invia_telegram(3, "SA")
                post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
