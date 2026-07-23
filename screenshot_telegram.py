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
TARGET_W        = 1920
TARGET_H        = 2560
OUTPUT_PATH     = "screenshot.png"


WAIT_SELECTOR = "#tableArea .col:last-child .col-rows .row:last-child"

COMP_INFO = {
    "SA":  {
        "caption": lambda g: f"<b>🇮🇹📊 Serie A | Classifica</b>\n<i>📆 {g}ª Giornata</i>\n\n👉 @Juventus_Reborn",
        "wait":    WAIT_SELECTOR
    },
    "UCL": {
        "caption": lambda g: f"<b>🇪🇺📊 UCL | Classifica</b>\n<i>📆 {g}ª Giornata</i>\n\n👉 @Juventus_Reborn",
        "wait":    WAIT_SELECTOR
    },
    "UEL": {
        "caption": lambda g: f"<b>🇪🇺📊 UEL | Classifica</b>\n<i>📆 {g}ª Giornata</i>\n\n👉 @Juventus_Reborn",
        "wait":    WAIT_SELECTOR
    },
    "UECL": {
        "caption": lambda g: f"<b>🇪🇺📊 UECL | Classifica</b>\n<i>📆 {g}ª Giornata</i>\n\n👉 @Juventus_Reborn",
        "wait":    WAIT_SELECTOR
    },
}


def scarica_font_base64(css_url: str) -> str:
    """
    Scarica i font da un URL di Google Fonts (css2) e li restituisce come blocco
    CSS @font-face con sorgenti base64 inline.

    IMPORTANTE: l'URL viene letto direttamente dall'index.html, così i font
    incorporati sono SEMPRE quelli usati dalla grafica. Se in futuro cambiano i
    font nell'HTML, qui non c'è nulla da aggiornare.

    Se il download fallisce (es. CI senza rete) torna stringa vuota e si usano
    i font di sistema come fallback.
    """
    import base64

    if not css_url:
        print("⚠️  Nessun link Google Fonts trovato nell'HTML: uso i font di sistema.")
        return ""

    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    try:
        css_resp = requests.get(css_url, headers={"User-Agent": UA}, timeout=20)
        css_resp.raise_for_status()
        css_text = css_resp.text

        # Sostituisci ogni url(...) dentro i @font-face con un data URI base64
        font_urls = re.findall(r'url\((https://[^)]+)\)', css_text)
        for url in font_urls:
            try:
                font_resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
                font_resp.raise_for_status()
                b64 = base64.b64encode(font_resp.content).decode("ascii")
                fmt = "woff2" if "woff2" in url else "woff" if "woff" in url else "truetype"
                data_uri = f"data:font/{fmt};base64,{b64}"
                css_text = css_text.replace(url, data_uri)
            except Exception as e:
                print(f"⚠️  Font non scaricato ({url}): {e}")

        print(f"✅ Font incorporati come base64 ({len(font_urls)} file).")
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

    # La stessa texture chiara rifinisce tutte e quattro le competizioni.
    texture_file = "texture_white.png"

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_str = json.dumps(json_completo, ensure_ascii=False)
    html_patched = html_content

    # 1) Leggi l'URL dei Google Fonts DALL'HTML (così i font sono sempre allineati),
    #    poi rimuovi i <link> esterni e incorpora i font come @font-face base64.
    m = re.search(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', html_content)
    css_url = m.group(1) if m else None

    html_patched = re.sub(r'<link[^>]+fonts\.googleapis[^>]*>', '', html_patched)
    html_patched = re.sub(r'<link[^>]+fonts\.gstatic[^>]*>', '', html_patched)

    font_css = scarica_font_base64(css_url)
    if font_css:
        html_patched = html_patched.replace('<head>', f'<head>\n<style>\n{font_css}\n</style>', 1)

    # 2) Inietta i dati subito dopo <body> (l'HTML legge window.__CLASSIFICA__ se presente)
    inject = f"<script>\nwindow.__CLASSIFICA__ = {json_str};\n</script>"
    html_patched = html_patched.replace('<body>', '<body>\n' + inject, 1)

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
        # Aspetta che i font siano davvero pronti prima dello scatto
        try:
            await page.evaluate("async () => { await document.fonts.ready; }")
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        await page.screenshot(
            path="screenshot_raw.png",
            clip={"x": 0, "y": 0, "width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
        )
        await browser.close()

    temp_html.unlink()

    applica_texture("screenshot_raw.png", texture_file, OUTPUT_PATH)
    Path("screenshot_raw.png").unlink()

    print(f"✅ Screenshot generato: {comp_key} – Giornata {giornata}")
    return giornata, comp_key


def applica_texture(base_path, texture_path, output_path):
    base = Image.open(base_path).convert("RGBA")
    # La foto HD di Telegram usa quattro volte i pixel della foto standard:
    # per il formato 3:4 prepariamo quindi una sorgente 1920x2560 (LANCZOS).
    if base.size != (TARGET_W, TARGET_H):
        base = base.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    if texture_path and os.path.exists(texture_path):
        texture = Image.open(texture_path).convert("RGBA")
        if texture.size != base.size:
            texture = texture.resize(base.size, Image.LANCZOS)
        base.paste(texture, (0, 0), texture)
    else:
        print(f"⚠️  Texture non trovata ({texture_path}): salvo senza texture.")
    base.convert("RGB").save(output_path, "PNG")


def invia_telegram(giornata, comp_key):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Errore: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID mancanti.")
        return

    comp_data     = COMP_INFO.get(comp_key, COMP_INFO["SA"])
    caption_testo = comp_data["caption"](giornata)

    # Invio come FOTO inline alla risoluzione HD 3:4, non come documento.
    # Il Bot API non espone un interruttore "HD": è la sorgente fino a 2560 px
    # che consente a Telegram di generare la variante foto ad alta definizione.
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(OUTPUT_PATH, "rb") as foto:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption_testo, "parse_mode": "HTML"},
            files={"photo": ("classifica-hd.png", foto, "image/png")},
            timeout=60,
        )

    if response.status_code == 200:
        payload = response.json()
        photo_sizes = payload.get("result", {}).get("photo", [])
        largest = max(photo_sizes, key=lambda p: p.get("width", 0) * p.get("height", 0), default={})
        sent_w = largest.get("width", 0)
        sent_h = largest.get("height", 0)
        if max(sent_w, sent_h) >= 2000:
            print(f"✅ Immagine HD inviata su Telegram ({comp_key}) – variante massima {sent_w}x{sent_h}.")
        else:
            print(f"⚠️ Telegram ha restituito solo {sent_w}x{sent_h}: verificare la variante HD.")
    else:
        print(f"❌ Errore Telegram: {response.status_code} — {response.text}")


if __name__ == "__main__":
    giornata, comp_key = asyncio.run(scatta_screenshot())
    invia_telegram(giornata, comp_key)
