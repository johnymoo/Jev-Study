#!/usr/bin/env python3
"""Build jev_study site: convert planning/02-working reports into one styled HTML page."""
import html as H
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "planning/02-working"
OUT = Path(__file__).resolve().parent / "index.html"

try:
    import markdown as _md
    def to_html(text):
        return _md.markdown(text, extensions=["tables", "fenced_code"])
except ImportError:
    def to_html(text):
        out, in_code, buf = [], False, []
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.strip().startswith("```"):
                if in_code:
                    out.append("<pre><code>" + H.escape("\n".join(buf)) + "</code></pre>")
                    buf = []
                in_code = not in_code
            elif in_code:
                buf.append(ln)
            else:
                e = H.escape(ln)
                if re.match(r"^###\s", ln): out.append(f"<h3>{e[4:]}</h3>")
                elif re.match(r"^##\s", ln): out.append(f"<h2>{e[3:]}</h2>")
                elif re.match(r"^#\s", ln): out.append(f"<h1>{e[2:]}</h1>")
                elif ln.startswith("- "): out.append(f"<li>{e[2:]}</li>")
                elif ln.startswith("|"):
                    row = [c.strip() for c in ln.strip("|").split("|")]
                    if set("".join(row)) <= set("-: "): pass
                    elif lines[i-1].startswith("|") and not set("".join(c.strip() for c in lines[i-1].strip("|").split("|"))) <= set("-: "):
                        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
                    else:
                        out.append("<tr>" + "".join(f"<th>{c}</th>" for c in row) + "</tr>")
                else: out.append(f"<p>{e}</p>")
            i += 1
        html_text = "\n".join(out)
        html_text = re.sub(r"(<tr>(?:<th>.*?</th>)+</tr>)((?:<tr>(?:<td>.*?</td>)+</tr>)+)", r"<table>\1<tbody>\2</tbody></table>", html_text)
        html_text = re.sub(r"(<li>.*?</li>\n(?=<li>))", r"\1", html_text)
        return html_text

FILES = [
    ("00-overview.md", "总览", "★"),
    ("01-openjev-semif.md", "01 · openjev (SemIf)", ""),
    ("02-jev-behavior-study.md", "02 · jev-behavior-study", ""),
    ("03-jev-capability-atlas.md", "03 · jev-capability-atlas", ""),
    ("04-jevfire.md", "04 · jevfire", ""),
    ("05-jev-ultrafast.md", "05 · jev-ultrafast", ""),
    ("06-jev-demos.md", "06 · jev-demos", ""),
    ("07-jev-phishing-bench.md", "07 · jev-phishing-bench", ""),
    ("08-windtunnel.md", "08 · WindTunnel", ""),
    ("09-jev-browser.md", "09 · jev-browser", ""),
]

nav, sections = [], []
for fname, title, badge in FILES:
    path = REPORTS / fname
    body = to_html(path.read_text(encoding="utf-8")) if path.exists() else "<p>缺失</p>"
    sid = fname.replace(".md", "")
    nav.append(f'<a href="#{sid}">{badge} {title}</a>')
    sections.append(f'<section id="{sid}">{body}</section>')

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jev 复现生态调研 · Jev_study</title>
<style>
:root { --bg:#0f1117; --panel:#171a23; --card:#1c202b; --text:#d8dce6; --dim:#8b93a5;
        --accent:#7aa2f7; --good:#9ece6a; --warn:#e0af68; --bad:#f7768e; --border:#2a2f3d; }
* { box-sizing:border-box; }
body { margin:0; display:flex; background:var(--bg); color:var(--text);
       font:15px/1.75 -apple-system,"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif; }
nav { width:260px; flex-shrink:0; position:sticky; top:0; height:100vh; overflow-y:auto;
      background:var(--panel); border-right:1px solid var(--border); padding:28px 18px; }
nav h1 { font-size:17px; margin:0 0 4px; color:#fff; }
nav .sub { font-size:12px; color:var(--dim); margin-bottom:20px; }
nav a { display:block; padding:7px 10px; margin:2px 0; border-radius:8px; color:var(--dim);
        text-decoration:none; font-size:13.5px; }
nav a:hover { background:var(--card); color:var(--accent); }
main { flex:1; max-width:980px; margin:0 auto; padding:40px 48px 80px; }
section { background:var(--card); border:1px solid var(--border); border-radius:14px;
          padding:32px 38px; margin-bottom:34px; scroll-margin-top:24px; }
h1 { font-size:24px; color:#fff; border-bottom:2px solid var(--accent); padding-bottom:10px; }
h2 { font-size:19px; color:var(--accent); margin-top:34px; }
h3 { font-size:16px; color:#c0caf5; }
table { border-collapse:collapse; width:100%; margin:16px 0; font-size:13.5px; }
th, td { border:1px solid var(--border); padding:8px 12px; text-align:left; vertical-align:top; }
th { background:#232939; color:#c0caf5; }
tr:nth-child(even) td { background:#20242f; }
code { background:#262b38; padding:1px 6px; border-radius:5px; font-size:13px; color:#9ece6a; }
pre code { display:block; padding:14px; overflow-x:auto; }
blockquote { border-left:3px solid var(--warn); margin:14px 0; padding:4px 18px; color:var(--dim); }
a { color:var(--accent); }
li { margin:4px 0; }
hr { border:none; border-top:1px solid var(--border); margin:24px 0; }
@media (max-width: 900px) { body{flex-direction:column} nav{position:static;width:100%;height:auto} main{padding:20px} section{padding:22px} }
</style>
</head>
<body>
<nav>
  <h1>Jev_study</h1>
  <div class="sub">Jev 复现生态调研 · 2026-09-20<br>源：yage.ai 文章 × 9 仓库一手核验</div>
  {NAV}
</nav>
<main>
{SECTIONS}
</main>
</body>
</html>"""

OUT.write_text(TPL.replace("{NAV}", "\n".join(nav)).replace("{SECTIONS}", "\n".join(sections)), encoding="utf-8")
print(f"written {OUT} ({OUT.stat().st_size} bytes)")
