"""Browser-level QA of the real running app; all output stays on the server."""
from pathlib import Path
import os,json
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH","data/browser")
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/qa";OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--no-sandbox"])
    page=b.new_page(viewport={"width":1440,"height":1050},device_scale_factor=1)
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto("http://127.0.0.1:8765",wait_until="networkidle")
    page.wait_for_selector("#content:not([hidden])",timeout=120000)
    page.wait_for_selector("#habitat-map path",timeout=120000)
    assert page.locator("#diagnostics-summary table tr").count()==3
    assert "Coral/Algae" in page.locator("#habitat-summary").inner_text()
    page.screenshot(path=str(OUT/"desktop.png"),full_page=True)
    n=page.locator("#site option").count();assert n>=1
    page.locator("#asof").fill("2024-05-15");page.locator("#refresh").click()
    page.wait_for_function("document.getElementById('status').textContent.includes('2024-05-15')",timeout=120000)
    assert not page.locator("#error").is_visible()
    page.screenshot(path=str(OUT/"historical.png"),full_page=True)
    with page.expect_download() as download:page.locator("#export").click()
    d=download.value;d.save_as(str(OUT/"export.csv"))
    page.locator("[data-view=evidence]").click()
    page.wait_for_selector("#evaluation-summary table")
    page.screenshot(path=str(OUT/"evidence.png"),full_page=True)
    page.locator("[data-view=pilot]").click()
    page.screenshot(path=str(OUT/"pilot.png"),full_page=True)
    page.set_viewport_size({"width":390,"height":844})
    page.locator("[data-view=overview]").click()
    page.screenshot(path=str(OUT/"mobile.png"),full_page=True)
    overflow=page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert not overflow,"Mobile horizontal overflow"
    page.locator("#language").click()
    assert page.evaluate("window.ReefI18n.language")=="en"
    assert page.locator("#asof").input_value()=="2024-05-15"
    page.screenshot(path=str(OUT/"mobile_en.png"),full_page=True)
    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    page.set_viewport_size({"width":1440,"height":1050})
    for view in ["overview","evidence","pilot"]:
        page.locator("[data-view="+view+"]").click()
        text=page.locator("#"+view).inner_text()
        assert not any("\u4e00"<=c<="\u9fff" for c in text),(view,text)
        page.screenshot(path=str(OUT/(view+"_en.png")),full_page=True)
    page.reload(wait_until="networkidle")
    page.wait_for_selector("#content:not([hidden])",timeout=120000)
    assert page.evaluate("window.ReefI18n.language")=="en"
    page.locator("#language").click()
    assert page.evaluate("window.ReefI18n.language")=="zh"
    assert not errors,errors
    (OUT/"browser_qa.json").write_text(json.dumps({"page_errors":errors,"site_count":n,"export_bytes":(OUT/"export.csv").stat().st_size,
      "atlas_real_geometry":True,"model_diagnostics":True,"historical_replay":True,"english_views":True,"language_persistence":True,"evidence_table":True,"mobile_no_overflow":not overflow},indent=2))
    b.close()
print("Browser QA passed")
