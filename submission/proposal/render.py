"""Render proposal.html -> Technical_Proposal.pdf (A4) with Chromium via Node Playwright.

If team.json exists, its values replace {{TEAM_NAME}}, {{TEAM_ID}}, {{TEAM_MEMBERS}} in a
temporary copy (kept next to proposal.html so relative image paths still resolve).
Usage:  python submission/proposal/render.py
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "proposal.html")
OUT = os.path.join(HERE, "Technical_Proposal.pdf")

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const [src, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + src, { waitUntil: 'load' });
  await page.pdf({
    path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: '<div style="width:100%;font-family:Inter,Arial,sans-serif;font-size:7.5px;color:#777;padding:0 18mm;display:flex;justify-content:space-between;">'
      + '<span>Qubit Happens (Team 6746) · Technical Proposal · ADB Quantum Innovation Challenge 2026</span>'
      + '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
    margin: { top: '18mm', bottom: '20mm', left: '18mm', right: '18mm' },
  });
  await browser.close();
})();
"""


def main():
    html = open(SRC, encoding="utf-8").read()
    team = os.path.join(HERE, "team.json")
    if os.path.exists(team):
        for k, v in json.load(open(team, encoding="utf-8")).items():
            html = html.replace("{{" + k + "}}", v)
    tmp_html = os.path.join(HERE, "_render.html")
    open(tmp_html, "w", encoding="utf-8").write(html)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(JS); js = f.name
    try:
        subprocess.run(["node", js, tmp_html, OUT], check=True)
    finally:
        os.remove(js); os.remove(tmp_html)
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
