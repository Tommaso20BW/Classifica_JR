import os
import asyncio
import json
import re
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
    "UECL": {
        "caption": lambda g: f"<b>🟢🏆 Classifica Conference League - Giornata {g}.</b>\n\n👉 @Juventus_Reborn",
        "wait":    "#tableArea .col:last-child .col-rows .row:last-child"
    },
}


async def scatta_screenshot():
    script_dir = Path(__file__).parent.absolute()
    html_path = script_dir / "index.html"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=SCALE
        )
        page = await context.new_page()
        
        # Carica il file HTML locale
        await page.goto(html_path.as_uri())
        
        # Carica il file JSON per leggere giornata e competizione attuale
        with open("classifica.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        comp_key = data.get("competition", "SA").upper()
        giornata = data.get("giornata", "—")
        
        cfg = COMP_INFO.get(comp_key, COMP_INFO["SA"])
        
        # Attende che la tabella sia renderizzata a schermo prima dello scatto
        await page.wait_for_selector(cfg["wait"])
        await asyncio.sleep(1)
        
        await page.screenshot(path="screenshot_raw.png")
        await browser.close()
        
        if Path("screenshot_raw.png").exists():
            return giornata, comp_key
        else:
            raise FileNotFoundError("Impossibile generare screenshot_raw.png")


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
        print(f"📡 Messaggio inviato correttamente su Telegram per {comp_key}!")
    else:
        print(f"❌ Errore invio Telegram: {response.status_code} - {response.text}")


async def main():
    comp_key = os.environ.get("COMPETITION", "SA").upper()
    print(f"🚀 Avvio screenshot per competizione: {comp_key}")
    
    giornata, comp_reale = await scatta_screenshot()
    
    # Applica texture di sfondo
    applica_texture("screenshot_raw.png", "texture.png", OUTPUT_PATH)
    
    # Spedisce l'immagine finale elaborata
    invia_telegram(giornata, comp_reale)
    
    # Pulizia file temporaneo raw
    if Path("screenshot_raw.png").exists():
        Path("screenshot_raw.png").unlink()


if __name__ == "__main__":
    asyncio.run(main())
