"""Refactoriza el bloque KPI Chart de un index.html ya renderizado:
IIFE -> initKpiChart() + cv() para soportar el toggle claro/oscuro."""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "function initKpiChart()" in s:
    print("chart ya refactorizado:", p)
    sys.exit(0)

old_start = "// ── KPI Chart ──\n(function() {\n    const labels = ["
new_start = """// ── KPI Chart ──
function cv(k){ return getComputedStyle(document.body).getPropertyValue(k).trim(); }
let kpiChart = null;
function initKpiChart() {
    const labels = ["""
assert s.count(old_start) == 1, "start no encontrado o ambiguo"
s = s.replace(old_start, new_start, 1)

s = s.replace("new Chart(canvas, {", "kpiChart = new Chart(canvas, {", 1)

for old, new in [
    ("'#78909c'", "cv('--dim2')"),
    ("'#607d8b'", "cv('--dim')"),
    ("'#1a2a4a'", "cv('--line')"),
    ("'#00d4ff'", "cv('--accent')"),
]:
    s = s.replace(old, new)

old_end = "    });\n})();\n</script>\n\n\n<script>\n// Tema claro/oscuro"
new_end = "    }\n}\ninitKpiChart();\n</script>\n\n\n<script>\n// Tema claro/oscuro"
assert s.count(old_end) == 1, "final del chart no encontrado o ambiguo"
s = s.replace(old_end, new_end, 1)

open(p, "w", encoding="utf-8").write(s)
print("chart refactorizado:", p)
