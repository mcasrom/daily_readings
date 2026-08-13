"""Aplica tema claro/oscuro + toggle + Ko-fi a un briefing.html ya renderizado.
Idempotente: si ya contiene ko-fi.com/m_castillo, no toca nada."""
import re
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "ko-fi.com/m_castillo" in s:
    print("ya transformado:", p)
    sys.exit(0)

VARS = """:root{
            --bg:#0a0e17; --bg2:#0d1520; --panel:#111827; --grad:#141e30;
            --line:#1a2a4a; --text:#d0dbe8;
            --accent:#00d4ff; --accent2:#4fc3f7;
            --dim:#607d8b; --dim2:#78909c; --link:#b0bec5; --meta:#546e7a;
            --faint:#455a64; --star-dim:#2a3a5a; --star-hover:#4a5a7a;
            --hl-bg:rgba(0,212,255,0.03);
        }
        body.light{
            --bg:#f4f6fb; --bg2:#eef1f8; --panel:#ffffff; --grad:#e3ebf7;
            --line:#d7deeb; --text:#0f172a;
            --accent:#0284c7; --accent2:#0369a1;
            --dim:#475569; --dim2:#64748b; --link:#1e293b; --meta:#64748b;
            --faint:#94a3b8; --star-dim:#cbd5e1; --star-hover:#94a3b8;
            --hl-bg:rgba(2,132,199,0.06);
        }
        body.light { color-scheme: light; }
        """
assert "<style>" in s
s = s.replace("<style>", "<style>\n" + VARS, 1)

marker = "// ── KPI Chart ──"
head, tail = s.split(marker, 1)

REPL = {
    "#0a0e17": "var(--bg)", "#0d1520": "var(--bg2)", "#111827": "var(--panel)",
    "#141e30": "var(--grad)", "#1a2a4a": "var(--line)", "#d0dbe8": "var(--text)",
    "#4fc3f7": "var(--accent2)", "#00d4ff": "var(--accent)",
    "#607d8b": "var(--dim)", "#78909c": "var(--dim2)", "#b0bec5": "var(--link)",
    "#546e7a": "var(--meta)", "#455a64": "var(--faint)",
    "#2a3a5a": "var(--star-dim)", "#4a5a7a": "var(--star-hover)",
    "#e0e0e0": "var(--text)",
    "rgba(0,212,255,0.03)": "var(--hl-bg)",
}
for k, v in REPL.items():
    head = head.replace(k, v)

old_start = """(function() {
    const labels = {{ chart_data.labels | tojson }}"""
if old_start in tail:
    new_start = """function cv(k){ return getComputedStyle(document.body).getPropertyValue(k).trim(); }
let kpiChart = null;
function initKpiChart() {
    const labels = {{ chart_data.labels | tojson }}"""
    tail = tail.replace(old_start, new_start, 1)
    old_end = """    });
})();"""
    new_end = """    });
}
initKpiChart();"""
    tail = tail.replace(old_end, new_end, 1)
    for old, new in [
        ("'#78909c'", "cv('--dim2')"),
        ("'#607d8b'", "cv('--dim')"),
        ("'#1a2a4a'", "cv('--line')"),
        ("'#00d4ff'", "cv('--accent')"),
    ]:
        tail = tail.replace(old, new)

head = head.replace(
    "<body>",
    "<body>\n\n<script>try{if(localStorage.getItem('hub_theme')==='light')document.body.classList.add('light');}catch(e){}</script>\n",
    1,
)

nav_span = '    <span id="pipeline-status" style="margin-left:auto;padding:14px 22px;"></span>'
head = head.replace(
    nav_span,
    nav_span + '\n    <button id="themeToggle" title="Alternar tema claro/oscuro" style="background:none;border:none;color:var(--dim);cursor:pointer;font-size:0.95em;padding:14px 20px;white-space:nowrap;">☀️</button>',
    1,
)

kofi = '    <p style="margin-top:10px;"><a href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener" style="display:inline-block;"><img height="36" style="border:0px;height:36px;" src="https://storage.ko-fi.com/cdn/kofi3.png?v=6" border="0" alt="Apóyanos en Ko-fi"></a></p>\n'
lines = head.splitlines()
idx = next((i for i, l in enumerate(lines) if "Inteligencia Geopolítica" in l and "©" in l), None)
assert idx is not None, "footer anchor no encontrado"
lines.insert(idx, kofi.rstrip("\n"))
head = "\n".join(lines)

toggle_js = """
<script>
// Tema claro/oscuro con persistencia
const themeBtn = document.getElementById('themeToggle');
function setTheme(light){
    document.body.classList.toggle('light', light);
    try{ localStorage.setItem('hub_theme', light ? 'light' : 'dark'); }catch(e){}
    if (themeBtn) themeBtn.textContent = light ? '🌙' : '☀️';
    if (typeof initKpiChart === 'function') initKpiChart();
}
if (themeBtn) {
    themeBtn.textContent = document.body.classList.contains('light') ? '🌙' : '☀️';
    themeBtn.addEventListener('click', function(){ setTheme(!document.body.classList.contains('light')); });
}
</script>

"""
assert "</body>" in tail
tail = tail.replace("</body>", toggle_js + "</body>", 1)

open(p, "w", encoding="utf-8").write(head + marker + tail)
print("transformado:", p)
