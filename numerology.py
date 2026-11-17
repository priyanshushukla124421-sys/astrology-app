"""
AstroPulse India - अंक ज्योतिष (न्यूमरोलॉजी) गणना मॉड्यूल
main.py (प्रॉम्प्ट के लिए डेटा) और report_pdf.py (PDF की तालिकाएं) दोनों इसी को इस्तेमाल करते हैं।

गणना भारतीय पद्धति पर आधारित है:
- मूलांक  = जन्म की तारीख का एक-अंकीय योग
- भाग्यांक = पूरी जन्म तिथि (दिन+माह+वर्ष) के सभी अंकों का एक-अंकीय योग
- नामांक  = नाम के अंग्रेज़ी अक्षरों का कैल्डियन (Chaldean) मान-योग (नाम अंग्रेज़ी अक्षरों में हो तभी)
- लो-शू ग्रिड = जन्म तिथि के अंक (+ मूलांक और भाग्यांक) की 3x3 ग्रिड
- व्यक्तिगत वर्ष/माह = दिन + माह + (वर्ष या माह-अंक) का एक-अंकीय योग
"""
import re

PLANET = {
    1: ("सूर्य", "Sun"), 2: ("चंद्र", "Moon"), 3: ("गुरु", "Jupiter"), 4: ("राहु", "Rahu"), 5: ("बुध", "Mercury"),
    6: ("शुक्र", "Venus"), 7: ("केतु", "Ketu"), 8: ("शनि", "Saturn"), 9: ("मंगल", "Mars"),
}
# परंपरागत मान्यता वाली सामान्य सूची (रत्न शामिल नहीं)
LUCKY = {
    1: {"day": "रविवार", "colors": "सुनहरा, केसरिया, पीला", "mantra": "ॐ घृणि सूर्याय नमः"},
    2: {"day": "सोमवार", "colors": "सफेद, क्रीम, हल्का हरा", "mantra": "ॐ सोमाय नमः"},
    3: {"day": "गुरुवार", "colors": "पीला, सुनहरा, हल्का नारंगी", "mantra": "ॐ बृं बृहस्पतये नमः"},
    4: {"day": "शनिवार", "colors": "स्लेटी, गहरा नीला, भूरा", "mantra": "ॐ रां राहवे नमः"},
    5: {"day": "बुधवार", "colors": "हरा, हल्का हरा", "mantra": "ॐ बुं बुधाय नमः"},
    6: {"day": "शुक्रवार", "colors": "सफेद, गुलाबी, आसमानी", "mantra": "ॐ शुं शुक्राय नमः"},
    7: {"day": "मंगलवार", "colors": "हल्का हरा, धूसर, सफेद", "mantra": "ॐ कें केतवे नमः"},
    8: {"day": "शनिवार", "colors": "गहरा नीला, काला, गहरा बैंगनी", "mantra": "ॐ शं शनैश्चराय नमः"},
    9: {"day": "मंगलवार", "colors": "लाल, मैरून, सिंदूरी", "mantra": "ॐ अं अंगारकाय नमः"},
}
LOSHU_LAYOUT = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]

_CHALDEAN = {}
for _v, _letters in {1: "AIJQY", 2: "BKR", 3: "CGLS", 4: "DMT", 5: "EHNX", 6: "UVW", 7: "OZ", 8: "FP"}.items():
    for _c in _letters:
        _CHALDEAN[_c] = _v


def reduce_digit(n):
    n = abs(int(n))
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def name_number(name):
    """(कंपाउंड योग, एक-अंकीय नामांक) या (None, None) अगर नाम अंग्रेज़ी अक्षरों में नहीं है।"""
    letters = [c for c in (name or "").upper() if "A" <= c <= "Z"]
    if len(letters) < 2:
        return None, None
    total = sum(_CHALDEAN.get(c, 0) for c in letters)
    return total, reduce_digit(total)


def compute(name, day, month, year):
    dob_digits = f"{day:02d}{month:02d}{year}"
    mulank = reduce_digit(day)
    bhagyank = reduce_digit(sum(int(c) for c in dob_digits))
    comp, nam = name_number(name)

    counts = {i: 0 for i in range(1, 10)}
    for c in dob_digits:
        if c != "0":
            counts[int(c)] += 1
    counts[mulank] += 1          # परंपरा: मूलांक और भाग्यांक भी ग्रिड में जोड़े जाते हैं
    counts[bhagyank] += 1
    missing = [i for i in range(1, 10) if counts[i] == 0]
    repeated = [i for i in range(1, 10) if counts[i] >= 2]

    def personal_year(y):
        return reduce_digit(day + month + sum(int(c) for c in str(y)))

    years = {y: personal_year(y) for y in range(2026, 2032)}
    py27 = years[2027]
    months27 = [reduce_digit(py27 + m) for m in range(1, 13)]

    return {
        "name": name, "day": day, "month": month, "year": year,
        "mulank": mulank, "bhagyank": bhagyank,
        "name_compound": comp, "name_number": nam,
        "mulank_planet": PLANET[mulank][0], "bhagyank_planet": PLANET[bhagyank][0],
        "name_planet": PLANET[nam][0] if nam else None,
        "grid_counts": counts, "missing": missing, "repeated": repeated,
        "personal_years": years, "personal_months_2027": months27,
        "lucky_mulank": LUCKY[mulank], "lucky_bhagyank": LUCKY[bhagyank],
    }


MONTHS_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्तूबर", "नवंबर", "दिसंबर"]


def format_for_prompt(n):
    """Gemini प्रॉम्प्ट में डाला जाने वाला प्रमाणित अंक-ज्योतिष डेटा-ब्लॉक।"""
    L = []
    L.append(f"जन्म तिथि: {n['day']:02d}/{n['month']:02d}/{n['year']}")
    L.append(f"मूलांक (Mulank / Psychic Number): {n['mulank']}  | स्वामी ग्रह: {n['mulank_planet']}")
    L.append(f"भाग्यांक (Bhagyank / Destiny Number): {n['bhagyank']}  | स्वामी ग्रह: {n['bhagyank_planet']}")
    if n["name_number"]:
        L.append(f"नामांक (Name Number, Chaldean): कंपाउंड योग {n['name_compound']} → एक-अंकीय {n['name_number']}  | स्वामी ग्रह: {n['name_planet']}")
    else:
        L.append("नामांक: उपलब्ध नहीं (नाम अंग्रेज़ी अक्षरों में नहीं दिया गया)। नामांक की कोई संख्या न गढ़ें; नाम-कंपन वाले अध्याय में मूलांक/भाग्यांक के आधार पर नाम-ऊर्जा का सामान्य मार्गदर्शन दें।")
    L.append("")
    L.append("लो-शू ग्रिड (जन्म तिथि के अंक + मूलांक + भाग्यांक; कोष्ठक में उस अंक की संख्या):")
    for row in LOSHU_LAYOUT:
        L.append("   " + "   ".join(f"{d}({n['grid_counts'][d]})" for d in row))
    L.append("उपस्थित अंक: " + (", ".join(str(i) for i in range(1, 10) if n["grid_counts"][i] > 0) or "-"))
    L.append("अनुपस्थित अंक: " + (", ".join(map(str, n["missing"])) or "कोई नहीं"))
    L.append("दोहराए गए अंक (2 या अधिक बार): " + (", ".join(f"{i} ({n['grid_counts'][i]} बार)" for i in n["repeated"]) or "कोई नहीं"))
    L.append("")
    L.append("व्यक्तिगत वर्ष अंक (Personal Year): " + ", ".join(f"{y}→{v}" for y, v in n["personal_years"].items()))
    L.append("वर्ष 2027 के व्यक्तिगत माह अंक: " + ", ".join(f"{MONTHS_HI[i]}→{v}" for i, v in enumerate(n["personal_months_2027"])))
    L.append("")
    lm, lb = n["lucky_mulank"], n["lucky_bhagyank"]
    L.append(f"मूलांक {n['mulank']} की परंपरागत सूची: दिन {lm['day']}; रंग {lm['colors']}; मंत्र {lm['mantra']}")
    L.append(f"भाग्यांक {n['bhagyank']} की परंपरागत सूची: दिन {lb['day']}; रंग {lb['colors']}; मंत्र {lb['mantra']}")
    L.append("ग्रह-अंक संबंध: 1-सूर्य, 2-चंद्र, 3-गुरु, 4-राहु, 5-बुध, 6-शुक्र, 7-केतु, 8-शनि, 9-मंगल")
    return "\n".join(L)


if __name__ == "__main__":
    print(format_for_prompt(compute("Divyanshu Shukla", 15, 8, 1990)))
