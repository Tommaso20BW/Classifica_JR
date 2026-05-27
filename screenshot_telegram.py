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
SCALE           = 3
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


def scarica_font_base64() -> str:
    """
    Scarica i font da Google Fonts e li restituisce come blocco CSS @font-face
    con sorgenti base64 inline. Se il download fallisce (es. CI senza rete),
    torna una stringa vuota e i font di sistema vengono usati come fallback.
    """
    import base64

    GOOGLE_FONTS_CSS = (
        "https://fonts.googleapis.com/css2?"
        "family=Bebas+Neue"
        "&family=Barlow+Condensed:ital,wght@0,400;0,600;0,700;0,900;1,700"
        "&family=Inter:wght@400;600;700;800;900"
        "&display=swap"
    )
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    try:
        css_resp = requests.get(GOOGLE_FONTS_CSS, headers={"User-Agent": UA}, timeout=15)
        css_resp.raise_for_status()
        css_text = css_resp.text

        # Trova tutti gli url() nei @font-face e sostituiscili con data URI base64
        font_urls = re.findall(r'url\((https://[^)]+)\)', css_text)
        for url in font_urls:
            try:
                font_resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
                font_resp.raise_for_status()
                b64 = base64.b64encode(font_resp.content).decode("ascii")
                # Determina il formato dal URL
                fmt = "woff2" if "woff2" in url else "woff" if "woff" in url else "truetype"
                data_uri = f"data:font/{fmt};base64,{b64}"
                css_text = css_text.replace(url, data_uri)
            except Exception as e:
                print(f"⚠️  Font non scaricato ({url}): {e}")

        print("✅ Font incorporati come base64.")
        return css_text

    except Exception as e:
        print(f"⚠️  Impossibile scaricare i font da Google: {e}. Verranno usati i font di sistema.")
        return ""


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

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_str = json.dumps(json_completo, ensure_ascii=False)
    html_patched = html_content

    # 1) Replace external Google Fonts links with locally-embedded @font-face (base64)
    #    This avoids 403 errors in CI where google fonts are blocked.
    html_patched = re.sub(r'<link[^>]+fonts\.googleapis[^>]*>', '', html_patched)
    html_patched = re.sub(r'<link[^>]+fonts\.gstatic[^>]*>', '', html_patched)
    font_css = scarica_font_base64()
    if font_css:
        html_patched = html_patched.replace('<head>', f'<head>\n<style>\n{font_css}\n</style>', 1)

    # 2) Inject data script right after <body>
    inject = f"<script>\nwindow.__CLASSIFICA__ = {json_str};\n</script>"
    html_patched = html_patched.replace('<body>', '<body>\n' + inject, 1)

    # 4) Replace fetch() with inline Promise so data always loads on file://
    html_patched = html_patched.replace(
        "(window.__CLASSIFICA__ ? Promise.resolve(window.__CLASSIFICA__) : fetch('./classifica.json').then(r => r.json()))",
        f"Promise.resolve({json_str})"
    )

    temp_html = script_dir / "_screenshot_temp.html"
    temp_html.write_text(html_patched, encoding="utf-8")

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            "--disable-web-security",
            "--allow-file-access-from-files",
            "--allow-running-insecure-content",
        ])
        page = await browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=SCALE,
        )

        await page.goto(f"file://{temp_html}", wait_until="load")
        await page.wait_for_selector(comp_data["wait"], timeout=30000)
        await page.wait_for_timeout(4000)

        await page.screenshot(
            path="screenshot_raw.png",
            clip={"x": 0, "y": 0, "width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
        )
        await browser.close()

    temp_html.unlink()

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
