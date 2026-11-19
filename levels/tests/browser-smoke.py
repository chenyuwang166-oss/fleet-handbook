"""Offline browser checks. Run: python tests/browser-smoke.py"""
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("FLEET_LEVELS_ARTIFACTS", ROOT / "tests" / "artifacts" / "d2"))
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
# Exact official tokens, copied here so unexpected palette changes fail the check.
VI = {
    "brand-deep": "#3b2673", "brand-primary": "#8a4ed1", "brand-accent": "#b35be8",
    "brand-soft": "#e9e6ff", "text": "#0f1115", "text-2": "#4b4e57",
    "muted": "#686a72", "canvas": "#f7f8fa", "panel": "#ffffff",
    "panel-3": "#f1f0f7", "line": "#0f11151a", "line-strong": "#0f11153d",
    "peer": "#b9bbc2", "peer-light": "#dcdde2"
}
FONTS = {
    "zh": ['"Noto Sans SC"', '"Source Han Sans SC"', '"Microsoft YaHei"', 'sans-serif'],
    "en": ['"Inter"', '"Noto Sans"', '"Segoe UI"', 'sans-serif']
}
CARD_TRAITS = {
    "zh": ["", "", "按角色分工", "按流程接力", "写审分开"],
    "en": ["", "", "Defined roles", "Workflow handoffs", "Separate writing and review"]
}


def answers_for(level):
    values = {q["id"]: 0 for q in DATA["questions"]}
    for gate in DATA["levels"][level - 1]["requires"]:
        values[gate["question"]] = gate["minScore"]
    # Gates imply the minimum score. No unrelated answers should be needed.
    return values


def compact(text):
    return re.sub(r"\s+", "", text)


def font_names(font):
    return [part.strip().strip('"\'') for part in font.split(",")]


def main():
    errors, remote = [], []
    checked_cards = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844},
                                          device_scale_factor=1, accept_downloads=True,
                                          offline=True)
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.on("request", lambda req: remote.append(req.url) if req.url.startswith(("http:", "https:")) else None)
            page.add_init_script("""(() => {
              const original = CanvasRenderingContext2D.prototype.fillText;
              window.cardText = [];
              const originalImage = CanvasRenderingContext2D.prototype.drawImage;
              window.cardImages = [];
              CanvasRenderingContext2D.prototype.drawImage = function (image,x,y,width,height) {
                window.cardImages.push({source:image.id,x,y,width,height,w:this.canvas.width,h:this.canvas.height});
                return originalImage.apply(this,arguments);
              };
              CanvasRenderingContext2D.prototype.fillText = function (s,x,y) {
                window.cardText.push({text:s,x,y,width:this.measureText(s).width,
                  size:parseFloat(this.font.match(/([0-9.]+)px/)[1]),font:this.font,color:this.fillStyle,
                  ascent:this.measureText(s).actualBoundingBoxAscent,
                  descent:this.measureText(s).actualBoundingBoxDescent,w:this.canvas.width,h:this.canvas.height});
                return original.apply(this,arguments);
              };
            })();""")
            for level in range(1, 6):
                page.goto((ROOT / "index.html").as_uri(), wait_until="load")
                logo = page.locator("#metask-logo")
                assert logo.is_visible()
                assert logo.evaluate("e=>e.complete && e.naturalWidth > 0 && e.naturalWidth === e.naturalHeight")
                logo_src = logo.get_attribute("src")
                assert logo_src.startswith("data:image/svg+xml;base64,")
                assert hashlib.sha256(base64.b64decode(logo_src.split(",", 1)[1])).hexdigest() == "84d23bd5bb130cea2f116843116840d8dd1675ec8a48c930968a5c52165aed1d"
                assert logo.evaluate("e=>[e.width,e.height]") == [36, 36]
                if level == 1:
                    assert page.locator('meta[name="description"]').get_attribute("content") == "9 道关于真实工作方式的问题，看看你现在怎么分工。"
                    assert page.locator("#start").inner_text() == "开始自测 ↗"
                    assert "测的是做法，不是能力。" in page.locator('[data-i18n="lead"]').inner_text()
                    page.locator("#language").click()
                    assert page.locator("#start").inner_text() == "Start the check ↗"
                    assert "It measures how you work, not what your AI can do." in page.locator('[data-i18n="lead"]').inner_text()
                    page.locator("#language").click()
                    page.screenshot(path=str(OUT / "mobile-intro.png"), full_page=True)
                    page.locator("#start").focus()
                    page.keyboard.press("Enter")
                    page.keyboard.press("Tab")
                    page.keyboard.press("ArrowDown")
                    assert page.locator("#options input:checked").count() == 1
                    # Verify that switching languages preserves an in-flight answer.
                    before = page.locator("#options input:checked").get_attribute("value")
                    page.locator("#language").click()
                    assert page.locator("#options input:checked").get_attribute("value") == before
                    page.locator("#language").click()
                else:
                    page.locator("#start").click()
                page.locator("#next").is_visible()
                for i, (qid, score) in enumerate(answers_for(level).items()):
                    page.locator(f'input[value="{qid}-{score}"]').check(force=True)
                    if level == 5 and i == 5:
                        page.screenshot(path=str(OUT / "mobile-question.png"), full_page=True)
                    page.locator("#next").click()
                assert page.locator("#result-level").inner_text() == f"L{level}"
                for lang in ["zh", "en"]:
                    if lang == "en":
                        page.locator("#language").click()
                    assert page.locator("#result-level").inner_text() == f"L{level}"
                    result_level = DATA["levels"][level - 1]
                    assert page.locator("#result-summary").inner_text() == result_level["summary"][lang]
                    lab = "元任务实验室 MeTask AI Lab" if lang == "zh" else "MeTask AI Lab"
                    assert page.locator('.footer [data-i18n="lab"]').inner_text() == lab
                    assert page.locator('.footer [data-i18n="tag"]').count() == 0
                    assert not any(tag in page.locator(".footer").inner_text() for tag in ["#我的AI舰队", "#MyAIFleet"])
                    tokens = page.evaluate("""names => Object.fromEntries(names.map(name =>
                      [name,getComputedStyle(document.documentElement).getPropertyValue('--'+name).trim()]))""", list(VI))
                    assert tokens == VI, tokens
                    body_font = page.locator("body").evaluate("e=>getComputedStyle(e).fontFamily")
                    assert font_names(body_font) == font_names(",".join(FONTS[lang])), body_font
                    assert page.locator("body").evaluate("e=>getComputedStyle(e).backgroundColor") == "rgb(247, 248, 250)"
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    expected_chapters = [[1, 2], [1, 2], [2], [1, 3, 5], [3, 4, 5]][level - 1]
                    chapter_files = ["01-what-is-an-ai-fleet.md", "02-write-and-review.md", "03-memory.md", "04-decisions.md", "05-values.md"]
                    links = page.locator("#chapter-links a")
                    assert links.all_inner_texts() == [f"第{chapter}章" if lang == "zh" else f"Chapter {chapter}" for chapter in expected_chapters]
                    assert page.locator('[data-i18n="chapters"]').inner_text().strip() == ("手册章节：" if lang == "zh" else "Handbook chapters:")
                    chapter_hrefs = links.evaluate_all("els=>els.map(e=>e.getAttribute('href'))")
                    assert chapter_hrefs == [f"../handbook/{lang}/{chapter_files[chapter - 1]}" for chapter in expected_chapters]
                    for href in chapter_hrefs:
                        assert (ROOT / href).resolve().is_file(), href
                    skill_hrefs = page.locator("#skill-links a").evaluate_all("els=>els.map(e=>e.getAttribute('href'))")
                    skill_file = "SKILL.zh.md" if lang == "zh" else "SKILL.md"
                    assert skill_hrefs == [f"../skills/{skill}/{skill_file}" for skill in result_level["skills"]], skill_hrefs
                    for href in skill_hrefs:
                        assert (ROOT / href).resolve().is_file(), href
                    for fmt, size in [("portrait", (1080, 1350)), ("landscape", (1200, 675))]:
                        page.evaluate("window.cardText = []; window.cardImages = []")
                        page.locator(f"#{fmt}").click()
                        actual = page.locator("#share-card").evaluate("c => [c.width,c.height]")
                        assert actual == list(size)
                        texts = page.evaluate("window.cardText")
                        assert any(f"L{level}" == item["text"] for item in texts)
                        assert any("github.com/chenyuwang166-oss/fleet-handbook" == item["text"] for item in texts)
                        assert any("AI Fleet Handbook" == item["text"] for item in texts)
                        assert sum(item["text"] == "AI Fleet Handbook" for item in texts) == 1
                        assert any("AI 舰队手册" == item["text"] for item in texts) == (lang == "zh")
                        images = page.evaluate("window.cardImages")
                        logo_size = 56 if fmt == "landscape" else 72
                        margin = 70 if fmt == "landscape" else 86
                        logo_x, logo_y = size[0] - margin - logo_size, 63 if fmt == "landscape" else 92
                        assert images == [{"source": "metask-logo", "x": logo_x, "y": logo_y,
                                           "width": logo_size, "height": logo_size,
                                           "w": size[0], "h": size[1]}], images
                        assert any(lab == item["text"] for item in texts)
                        content_x = 86 if fmt == "portrait" else 430
                        title_rows = [item for item in texts if item["x"] == content_x and (737 <= item["y"] < 926 if fmt == "portrait" else 267 <= item["y"] < 425)]
                        statement_rows = [item for item in texts if item["x"] == content_x and (926 <= item["y"] < 1010 if fmt == "portrait" else 425 <= item["y"] < 505)]
                        assert compact("".join(item["text"] for item in title_rows)) == compact(result_level["title"][lang]), title_rows
                        assert compact("".join(item["text"] for item in statement_rows)) == compact(result_level["card"][lang]), statement_rows
                        assert max(item["y"] + item["descent"] for item in title_rows) < min(item["y"] - item["ascent"] for item in statement_rows)
                        rendered = compact("".join(item["text"] for item in texts))
                        for excluded in ["summary", "next"]:
                            assert compact(result_level[excluded][lang]) not in rendered, (excluded, rendered)
                        aria = page.locator("#share-card").get_attribute("aria-label")
                        assert result_level["title"][lang] in aria and result_level["card"][lang] in aria and lab in aria
                        assert result_level["summary"][lang] not in aria
                        expected_traits = CARD_TRAITS[lang][level - 1]
                        trait_y = 1010 if fmt == "portrait" else 505
                        trait_rows = [item["text"] for item in texts if item["y"] == trait_y]
                        assert trait_rows == ([expected_traits] if expected_traits else []), trait_rows
                        assert all(item["text"].strip() for item in texts), texts
                        if lang == "en":
                            assert not any(item["text"][0] in ",.!?;:" for item in texts), texts
                        assert not any(item["text"] in ["#我的AI舰队", "#MyAIFleet"] for item in texts)
                        cta = "九道题，看看你现在怎么分工" if lang == "zh" else "Nine questions on how you work"
                        assert any(cta == item["text"] for item in texts)
                        assert cta in aria
                        for item in texts:
                            assert item["color"] in {VI["brand-deep"], VI["text"], VI["text-2"]}, item
                            family = re.sub(r"^.*?[0-9.]+px\s+", "", item["font"])
                            assert font_names(family) == font_names(",".join(FONTS[lang])), item
                            assert item["x"] >= 0 and item["x"] + item["width"] <= item["w"], item
                            assert item["y"] - item["size"] >= 0 and item["y"] <= item["h"], item
                            assert item["y"] - item["ascent"] >= 0 and item["y"] + item["descent"] <= item["h"], item
                        checked_cards += 1
                        with page.expect_download() as pending:
                            page.locator("#download").click()
                        target = OUT / f"sample-L{level}-{fmt}-{lang}.png"
                        pending.value.save_as(target)
                        with Image.open(target) as image:
                            assert image.size == size and image.format == "PNG"
                            assert image.convert("RGB").getpixel((0, 0)) == (247, 248, 250)
                            accent = (70, 40) if fmt == "landscape" else (86, 66)
                            assert image.convert("RGB").getpixel(accent) == (138, 78, 209)
                            logo_pixels = image.convert("RGB").crop((logo_x, logo_y, logo_x + logo_size, logo_y + logo_size))
                            assert sum(count for count, color in logo_pixels.getcolors(logo_size * logo_size) if color == (112, 63, 168)) > 100
                    if level == 5 and lang == "zh":
                        page.locator("#portrait").click()
                        # Clear the optional long-press image before screenshot.
                        page.locator("#download-status").evaluate("e=>e.replaceChildren()")
                        page.screenshot(path=str(OUT / "mobile-result-zh.png"), full_page=True)
                    if level == 5 and lang == "en":
                        page.locator("#portrait").click()
                        page.set_viewport_size({"width": 1280, "height": 900})
                        page.screenshot(path=str(OUT / "desktop-result-en.png"), full_page=True)
                for href in page.locator("#skill-links a").evaluate_all("els=>els.map(e=>e.getAttribute('href'))"):
                    assert (ROOT / href).resolve().is_file(), href
            page.locator("#edit").click()
            assert page.locator("#options input:checked").count() == 1
            page.locator("#next").click()
            assert page.locator("#options input:checked").count() == 1
            page.reload()
            page.locator("#start").click()
            assert page.locator("#options input:checked").count() == 0
            assert page.locator("#next").is_disabled()
            assert not context.cookies()
            assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
            assert not errors, errors
            assert not remote, remote
            context.close()
        finally:
            browser.close()
    result = {"status": "PASS", "levels": 5, "languages": 2,
              "card_renders": checked_cards, "downloaded_pngs": checked_cards,
              "traits_by_level": CARD_TRAITS,
              "offline": True, "remote_requests": len(remote), "browser_errors": errors,
              "checks": ["keyboard", "in-flight language switch", "result language switch",
                         "mobile overflow", "all card text bounds", "actual PNG downloads",
                         "answer-derived traits", "summary trait deduplication", "empty trait rows omitted",
                         "hashtags removed", "bilingual card statement", "skill links", "localized chapter links", "localized skill links",
                         "intro working practices statement", "edit answers",
                         "reload clears answers", "no browser storage", "exact official VI tokens",
                         "localized official font stacks", "bilingual lab attribution",
                         "original titles and card statements", "summary stays on result page",
                         "no advice on cards", "title and statement do not overlap", "PNG VI pixels",
                         "original official logo SHA256", "page header logo", "all cards draw official logo",
                         "PNG logo pixels", "English-only English card header"]}
    (OUT / "browser-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
