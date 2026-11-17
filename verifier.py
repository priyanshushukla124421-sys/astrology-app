"""
AstroPulse India - वेरिफायर और क्वालिटी मीटर
Gemini के लिखे हर पन्ने को (1) इंजन के प्रमाणित डेटा से मिलाता है (2) लेखन-गुणवत्ता का स्कोर देता है।
कोई AI कॉल नहीं होती, इसलिए यह मुफ्त और तेज़ है।

verify_page() के नतीजे में:
  errors   -> पक्की गलती (गलत तारीख, गलत मूलांक/भाग्यांक, दोष का उल्टा बयान); इन पर हिस्सा दोबारा बनवाया जाता है
  warnings -> संदिग्ध मिलान (ग्रह-भाव/राशि, अंश); सिर्फ दर्ज होती हैं
  checked / bad -> कितने तथ्य जाँचे गए और कितने गलत निकले (डेटा-मिलान % के लिए)
"""
import re

PLANET_WORDS = {
    "सूर्य": "Sun", "चंद्रमा": "Moon", "चंद्र": "Moon", "मंगल": "Mars", "बुध": "Mercury", "बृहस्पति": "Jupiter",
    "गुरु": "Jupiter", "शुक्र": "Venus", "शनि": "Saturn", "राहु": "Rahu", "केतु": "Ketu",
}
SIGNS_HI = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
HOUSE_WORDS = {"प्रथम": 1, "द्वितीय": 2, "तृतीय": 3, "चतुर्थ": 4, "पंचम": 5, "षष्ठ": 6, "सप्तम": 7,
               "अष्टम": 8, "नवम": 9, "दशम": 10, "एकादश": 11, "द्वादश": 12}
MONTHS = {"जनवरी": 1, "फरवरी": 2, "फ़रवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6, "जुलाई": 7, "अगस्त": 8,
          "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10, "अक्तूबर": 10, "नवंबर": 11, "नवम्बर": 11, "दिसंबर": 12, "दिसम्बर": 12}
_GEMS = ["माणिक", "मोती", "पन्ना", "पुखराज", "हीरा", "नीलम", "गोमेद", "लहसुनिया", "मूंगा", "रत्न", "gemstone", "ruby", "pearl", "emerald", "sapphire"]

# ऐसे शब्द जिनके होने पर "ग्रह-भाव" वाला वाक्य सीधा-सीधा स्थिति का बयान नहीं रहता (दृष्टि, स्वामित्व, D9 आदि)
_SKIP_WORDS = ("दृष्टि", "स्वामी", "भावेश", "लग्नेश", "अधिपति", "नवमांश", "D9", "D24", "गोचर", "कारक", "से ", "तक", "यदि", "जब", "अगर",
               "लिए", "पंचमेश", "षष्ठेश", "सप्तमेश", "अष्टमेश", "नवमेश", "दशमेश", "एकादशेश", "द्वादशेश", "चतुर्थेश", "द्वितीयेश", "तृतीयेश")


def _all_numbers(obj, out):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _all_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _all_numbers(v, out)


def _all_dates(obj, out):
    if isinstance(obj, str):
        for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", obj):
            out.add((int(m.group(3)), int(m.group(2)), int(m.group(1))))
        for m in re.finditer(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", obj):
            out.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    elif isinstance(obj, dict):
        for v in obj.values():
            _all_dates(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _all_dates(v, out)


def build_facts(chart, numdata=None, extra_texts=()):
    """इंजन के डेटा से जाँच के लिए तथ्य-सूची बनाता है।"""
    chart = chart or {}
    facts = {"planets": {}, "numbers": set(), "dates": set(), "doshas": {}, "num": numdata}
    for p, v in (chart.get("planets", {}) or {}).items():
        facts["planets"][p] = {"house": v.get("d1_house"), "sign": _sign_hi(v.get("d1_sign"))}
    _all_numbers(chart, facts["numbers"])
    _all_dates(chart.get("dasha_timeline", {}), facts["dates"])
    for t in extra_texts:
        _all_dates(t, facts["dates"])
    d = chart.get("doshas", {}) or {}
    facts["doshas"] = {
        "मांगलिक": bool((d.get("manglik") or {}).get("is_manglik")),
        "काल सर्प": bool((d.get("kaal_sarp") or {}).get("is_kaal_sarp")),
        "पितृ": bool((d.get("pitra_dosh") or {}).get("is_pitra")),
        "साढ़े साती": bool((d.get("sade_sati") or {}).get("is_sade_sati")),
    }
    return facts


def _sign_hi(s):
    m = re.search(r"\(([^)]+)\)", str(s or ""))
    return m.group(1) if m else str(s or "")


def _sentences(text):
    return [s.strip() for s in re.split(r"[।\n]|(?<=[a-z0-9])\.\s", text) if s.strip()]


def _house_in(sentence):
    nums = [int(x) for x in re.findall(r"(\d{1,2})\s*(?:वें|वां|वाँ|ठे|ठा|वा|रे|था|वें)?\s*भाव", sentence)]
    for w, n in HOUSE_WORDS.items():
        if re.search(w + r"\s*भाव", sentence):
            nums.append(n)
    return sorted(set(nums))


def _planets_in(sentence):
    found = set()
    for w, en in PLANET_WORDS.items():
        if w in sentence:
            found.add(en)
    if "चंद्रमा" in sentence or "चंद्र" in sentence:
        found.add("Moon")
    return found


# ------------------------------------------------------------------
def verify_page(text, facts, pkg_id=""):
    errors, warns = [], []
    checked = bad = 0
    t = text or ""

    # 1) तारीखें: "11 मार्च 2025" या 11-03-2025 रूप, डेटा में होनी चाहिए
    for m in re.finditer(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", t):
        key = (int(m.group(1)), MONTHS[m.group(2)], int(m.group(3)))
        checked += 1
        if facts["dates"] and key not in facts["dates"]:
            bad += 1
            errors.append(f"तारीख '{m.group(0)}' इंजन की दशा-तालिका में नहीं है")
    for m in re.finditer(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", t):
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        checked += 1
        if facts["dates"] and key not in facts["dates"] and key != facts.get("birth"):
            bad += 1
            errors.append(f"तारीख '{m.group(0)}' डेटा में नहीं है")

    # 2) अंश (डिग्री): दशमलव संख्याएँ इंजन की संख्याओं में होनी चाहिए
    for m in re.finditer(r"(?<![\d.])(\d{1,3})\.(\d{2,4})(?![\d.])\s*(?:°|डिग्री|अंश)", t):
        val = float(m.group(0).split("°")[0].split("डिग्री")[0].split("अंश")[0].strip())
        k = len(m.group(2))
        checked += 1
        ok = any(abs(x - val) <= max(0.0101, 0.51 * 10 ** (-k)) for x in facts["numbers"])
        if not ok:
            bad += 1
            warns.append(f"अंश {val}° इंजन के डेटा से मेल नहीं खाता")

    # 3) ग्रह-भाव और ग्रह-राशि के सीधे बयान
    for s in _sentences(t):
        if any(w in s for w in _SKIP_WORDS):
            continue
        if not any(w in s for w in ("स्थित", "विराजमान", "बैठे", "बैठा", "बैठी", "उपस्थित")):
            continue
        pl = _planets_in(s)
        if len(pl) != 1:
            continue
        p = next(iter(pl))
        fp = facts["planets"].get(p)
        if not fp:
            continue
        houses = _house_in(s)
        if len(houses) == 1:
            checked += 1
            if fp["house"] and houses[0] != fp["house"]:
                bad += 1
                warns.append(f"{_hi(p)} को {houses[0]} भाव में बताया, इंजन में {fp['house']} भाव")
        signs = [x for x in SIGNS_HI if x in s]
        if len(signs) == 1 and "राशि" in s:
            checked += 1
            if fp["sign"] and signs[0] != fp["sign"]:
                bad += 1
                warns.append(f"{_hi(p)} को {signs[0]} राशि में बताया, इंजन में {fp['sign']}")

    # 4) दोषों के बयान
    for name, present in facts["doshas"].items():
        for s in _sentences(t):
            if name not in s or "दोष" not in s and name != "साढ़े साती" and name != "काल सर्प":
                continue
            neg = any(w in s for w in ("नहीं", "मुक्त", "अनुपस्थित", "नही"))
            pos = any(w in s for w in ("उपस्थित है", "विद्यमान है", "बन रहा है", "बनता है", "दोष है", "प्रभाव में है"))
            if not present and pos and not neg:
                checked += 1
                bad += 1
                errors.append(f"इंजन के अनुसार '{name}' दोष नहीं है, पर पन्ने में उपस्थित बताया गया")
            elif present and neg and not pos and "आंशिक" not in s:
                checked += 1
                bad += 1
                errors.append(f"इंजन के अनुसार '{name}' दोष है, पर पन्ने में 'नहीं/मुक्त' लिखा गया")

    # 5) न्यूमरोलॉजी की संख्याएँ
    n = facts.get("num")
    if n:
        for m in re.finditer(r"आप(?:का|के)\s+मूलांक\s*(?:है\s*)?(\d)", t):
            checked += 1
            if int(m.group(1)) != n["mulank"]:
                bad += 1
                errors.append(f"मूलांक {m.group(1)} लिखा, सही मूलांक {n['mulank']} है")
        for m in re.finditer(r"आप(?:का|के)\s+भाग्यांक\s*(?:है\s*)?(\d)", t):
            checked += 1
            if int(m.group(1)) != n["bhagyank"]:
                bad += 1
                errors.append(f"भाग्यांक {m.group(1)} लिखा, सही भाग्यांक {n['bhagyank']} है")
        if n.get("name_number"):
            for m in re.finditer(r"नामांक\s*(?:है\s*)?(\d)", t):
                checked += 1
                if int(m.group(1)) != n["name_number"]:
                    bad += 1
                    errors.append(f"नामांक {m.group(1)} लिखा, सही नामांक {n['name_number']} है")
        else:
            if re.search(r"आप(?:का|के)\s+नामांक\s*(?:है\s*)?\d", t):
                checked += 1
                bad += 1
                errors.append("नामांक डेटा में उपलब्ध नहीं, फिर भी संख्या लिख दी गई")
        py27 = n["personal_years"].get(2027)
        for s in _sentences(t):
            if "2027" in s and "व्यक्तिगत वर्ष" in s:
                for m in re.finditer(r"व्यक्तिगत वर्ष\s*(?:अंक)?\s*(?:है\s*)?(\d)(?!\d)", s):
                    checked += 1
                    if int(m.group(1)) != py27:
                        bad += 1
                        errors.append(f"2027 का व्यक्तिगत वर्ष {m.group(1)} लिखा, सही {py27} है")

    return {"errors": errors, "warnings": warns, "checked": checked, "bad": bad}


def _hi(p):
    return {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
            "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}.get(p, p)


# ------------------------------------------------------------------
def quality_page(text):
    """(स्कोर 0-100, समस्याओं की लिस्ट) - सिर्फ लेखन-गुणवत्ता, तथ्यों की जाँच नहीं।"""
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    body = lines[1:] if lines else []
    words = len(" ".join(body).split())
    score, notes = 100.0, []
    if words < 250:
        score -= min(45, (250 - words) * 0.35)
        notes.append(f"शब्द कम ({words})")
    elif words < 320:
        score -= 6
    elif words > 520:
        score -= min(15, (words - 520) * 0.1)
        notes.append(f"शब्द ज्यादा ({words})")
    paras = [b for b in body if len(b.split()) > 25]
    if len(paras) < 3:
        score -= 12
        notes.append(f"पैराग्राफ कम ({len(paras)})")
    if any(re.match(r"^\s*([-•*]|\d+[.)])\s+", b) for b in body):
        score -= 10
        notes.append("बुलेट/नंबर सूची")
    low = (text or "").lower()
    gem = [g for g in _GEMS if g.lower() in low and g not in ("पन्ना",)]
    if gem:
        score -= 30
        notes.append("रत्न का जिक्र")
    if re.search(r"(PAGE\s*BREAK|प्रॉम्प्ट|STRICT|निर्देश)", text or "", flags=re.I):
        score -= 15
        notes.append("निर्देश का टेक्स्ट लीक")
    deva = len(re.findall(r"[\u0900-\u097F]", text or ""))
    alpha = len(re.findall(r"[A-Za-z]", text or ""))
    if deva and alpha > deva * 0.5:
        score -= 10
        notes.append("अंग्रेज़ी ज्यादा")
    sents = [s.strip() for s in re.split(r"[।.!?]", text or "") if len(s.strip()) > 25]
    if len(sents) != len(set(sents)):
        score -= 8
        notes.append("दोहराए वाक्य")
    last = (body[-1] if body else "").strip()
    if last and last[-1] not in "।.!?\"'”)":
        score -= 10
        notes.append("पन्ना अधूरा कटा लगता है")
    return max(0.0, round(score, 1)), notes
