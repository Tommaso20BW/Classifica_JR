import os
import asyncio
import json
import requests
from playwright.async_api import async_playwright
from pathlib import Path
from PIL import Image

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

VIEWPORT_WIDTH  = 900
VIEWPORT_HEIGHT = 1200
SCALE           = 1.2
TARGET_W        = 1080
TARGET_H        = 1440
OUTPUT_PATH     = "screenshot.png"

COMP_INFO = {
    "SA":  {
        "caption": lambda g: f"<b>🇮🇹📊 Classifica Serie A - {g}ª Giornata.</b>\n\n👉 @Juventus_Reborn",
        "wait":    "#tableArea .col:last-child .col-rows .row:last-child"
    },
    "UCL": {
        "caption": lambda g: f"<b>🏆⭐ Classifica Champions League - Giornata {g}.</b>\n\n👉 @Juventus_Reborn",
        "wait":    "#tableArea .col:last-child .col-rows .row:last-child"
    },
    "UEL": {
        "caption": lambda g: f"<b>🟠🏆 Classifica Europa League - Giornata {g}.</b>\n\n👉 @Juventus_Reborn",
        "wait":    "#tableArea .col:last-child .col-rows .row:last-child"
    },
}


async def scatta_screenshot():
    script_dir = Path(__file__).parent.resolve()
    html_path  = script_dir / "index.html"
    json_path  = script_dir / "classifica.json"

    with open(json_path, "r", encoding="utf-8") as f:
        json_completo = json.load(f)

    if isinstance(json_completo, list):
        json_completo = {"competition": "SA", "giornata": 1, "classifica": json_completo}

    giornata  = json_completo.get("giornata", 1)
    comp_key  = json_completo.get("competition", "SA").upper()
    comp_data = COMP_INFO.get(comp_key, COMP_INFO["SA"])

    print(f"[INFO] competition={comp_key}, giornata={giornata}, squadre={len(json_completo.get('classifica', []))}")

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inject data AND replace fetch() with inline data so no network/file calls needed
    inject = f"""<script>
window.__CLASSIFICA__ = {json.dumps(json_completo, ensure_ascii=False)};
</script>"""
    html_patched = html_content.replace("</head>", inject + "\n</head>")

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            "--disable-web-security",
            "--allow-file-access-from-files",
            "--allow-running-insecure-content",
            "--no-sandbox",
        ])
        context = await browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=SCALE,
            # Set base URL so relative asset paths resolve correctly
            base_url=f"file://{script_dir}/",
        )
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[BROWSER {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        # Use set_content with base_url so assets (images, fonts) load from script_dir
        await page.set_content(html_patched, base_url=f"file://{script_dir}/index.html")

        await page.wait_for_timeout(3000)

        injected = await page.evaluate(
            "typeof window.__CLASSIFICA__ !== 'undefined' ? 'YES len=' + window.__CLASSIFICA__.classifica.length : 'NOT INJECTED'"
        )
        col_count = await page.evaluate("document.querySelectorAll('#tableArea .col').length")
        row_count = await page.evaluate("document.querySelectorAll('#tableArea .col-rows .row').length")
        print(f"[DEBUG] __CLASSIFICA__={injected}, cols={col_count}, rows={row_count}")

        await page.wait_for_selector(comp_data["wait"], timeout=30000)
        await page.wait_for_timeout(4000)

        await page.screenshot(
            path="screenshot_raw.png",
            clip={"x": 0, "y": 0, "width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
        )
        await browser.close()

    applica_texture("screenshot_raw.png", "texture.png", OUTPUT_PATH)
    Path("screenshot_raw.png").unlink()

    print(f"✅ Screenshot generato: {comp_key} – Giornata {giornata}")
    return giornata, comp_key


def applica_texture(base_path, texture_path, output_path):
    base = Image.open(base_path).convert("RGBA")
    if base.size != (TARGET_W, TARGET_H):
        base = base.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    texture = Image.open(texture_path).convert("RGBA")
    if texture.size != base.size:
        texture = texture.resize(base.size, Image.LANCZOS)
    base.paste(texture, (0, 0), texture)
    base.convert("RGB").save(output_path, "PNG")


def invia_telegram(giornata, comp_key):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Errore: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID mancanti.")
        return

    comp_data     = COMP_INFO.get(comp_key, COMP_INFO["SA"])
    caption_testo = comp_data["caption"](giornata)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(OUTPUT_PATH, "rb") as foto:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption_testo, "parse_mode": "HTML"},
            files={"photo": foto}
        )

    if response.status_code == 200:
        print(f"✅ Immagine inviata su Telegram ({comp_key})!")
    else:
        print(f"❌ Errore Telegram: {response.status_code} — {response.text}")


if __name__ == "__main__":
    giornata, comp_key = asyncio.run(scatta_screenshot())
    invia_telegram(giornata, comp_key)
