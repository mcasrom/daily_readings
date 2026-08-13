p = "index.html"
s = open(p, encoding="utf-8").read()
old = "<script>try{if(localStorage.getItem('hub_theme')==='light')document.body.classList.add('light');}catch(e){}</script>"
new = "<script>try{var t=localStorage.getItem('hub_theme');if(t==='light'||(t===null&&window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches))document.body.classList.add('light');}catch(e){}</script>"
assert s.count(old) == 1, "anti-FOUC no encontrado: %d" % s.count(old)
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("live actualizado (system pref)")
