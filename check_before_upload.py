"""
GitHub पर डालने से पहले चलाइए:   python check_before_upload.py
बताता है: (1) किस फाइल में Gemini key लिखी है  (2) .gitignore ठीक है या नहीं  (3) git में अभी कौन-सी key वाली फाइलें जुड़ चुकी हैं।
key कहीं भी प्रिंट नहीं होती, सिर्फ फाइल का नाम।
"""
import os
import re
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
KEY_RE = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|AQ\.[A-Za-z0-9_\-]{20,}")
SKIP_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules", "API KEYS", "API_KEYS", "api keys", "api_keys"}   # key वाले फोल्डर यहीं रहें, बस git में न जाएँ (नीचे तीसरी जाँच देखती है)
TEXT_EXT = (".py", ".txt", ".bat", ".html", ".md", ".json", ".yaml", ".yml", ".env", ".cfg", ".ini", ".js", ".sh", ".toml", "")
MUST_IGNORE = ["API KEYS", "venv", "__pycache__", ".env"]

ok = True
print("=" * 60)
print("GitHub अपलोड से पहले की जाँच")
print("=" * 60)

# 1) फाइलों में key
leaks = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fn in files:
        path = os.path.join(root, fn)
        rel = os.path.relpath(path, BASE)
        if not fn.lower().endswith(TEXT_EXT) or os.path.getsize(path) > 3_000_000:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if KEY_RE.search(f.read()):
                    leaks.append(rel)
        except Exception:
            pass
if leaks:
    ok = False
    print("\n❌ इन फाइलों में Gemini key लिखी मिली:")
    for p in leaks:
        print("   -", p, "<-- यहाँ से key मिटाइए")
else:
    print("\n✅ किसी कोड-फाइल में key नहीं मिली।")

# 2) .gitignore
gi_path = os.path.join(BASE, ".gitignore")
if not os.path.isfile(gi_path):
    ok = False
    print("\n❌ '.gitignore' नाम की फाइल नहीं है।")
    if os.path.isfile(os.path.join(BASE, "_gitignore")):
        print("   '_gitignore' मिली है, उसका नाम बदलकर '.gitignore' कीजिए (Windows टर्मिनल: ren _gitignore .gitignore)")
else:
    txt = open(gi_path, encoding="utf-8", errors="ignore").read()
    missing = [m for m in MUST_IGNORE if m not in txt]
    if missing:
        ok = False
        print("\n❌ .gitignore में ये लाइनें नहीं हैं:", ", ".join(missing))
    else:
        print("✅ .gitignore ठीक है।")

# 3) git में पहले से जुड़ी key वाली फाइलें
try:
    tracked = subprocess.run(["git", "ls-files"], cwd=BASE, capture_output=True, text=True, timeout=20).stdout.splitlines()
    bad = [t for t in tracked if t.lower().startswith(("api keys/", "api_keys/")) or ("key" in os.path.basename(t).lower() and t.lower().endswith(".txt"))
           or t in leaks or t.lower().endswith((".db", ".env"))]
    if bad:
        ok = False
        print("\n❌ git में ये फाइलें पहले से जुड़ चुकी हैं (git add हो चुका है):")
        for t in bad:
            print("   -", t)
        print("   इन्हें हटाने का आसान तरीका: .git फोल्डर मिटाकर नए सिरे से 'git init' कीजिए (नीचे बताया है)")
    elif tracked:
        print("✅ git में जुड़ी फाइलों में कोई key वाली फाइल नहीं।")
except Exception:
    print("(git इंस्टॉल नहीं मिला या यह git फोल्डर नहीं है - यह जाँच छोड़ी गई)")

print("\n" + "=" * 60)
if ok:
    print("✅ सब ठीक है। अब 'git add .' और 'git push' कर सकते हैं।")
else:
    print("❌ ऊपर की गलतियाँ ठीक करके यह स्क्रिप्ट दोबारा चलाइए।")
    print("   याद रखें: जो key GitHub को दिख गई, उसे बदल दीजिए (नई key बनवाइए)।")
print("=" * 60)
