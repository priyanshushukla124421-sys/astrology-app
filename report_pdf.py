"""
AstroPulse India - रिपोर्ट PDF बनाने वाला मॉड्यूल (fpdf2 + Hind/Tinos फॉन्ट, देवनागरी shaping के साथ)

पेज क्रम (30-पेज रिपोर्ट = कुल 32 पेज):
  1      फ्रंट पेज (रिपोर्ट का नाम + जातक का नाम)      <- front.png जैसा
  2      जन्म विवरण पेज ("पृष्ठ 1")                    <- 2out_of_32.png जैसा
  3-4    चार्ट/ग्रह तालिका + दशा/दोष तालिका  (न्यूमरोलॉजी में: मूल अंक + ग्रिड, व्यक्तिगत वर्ष/माह)
  5...   Gemini के अध्याय (हर अध्याय एक पन्ने पर; टेक्स्ट अपने-आप पन्ना 80-85% भर देता है)
  आखिरी  बैक पेज (संपर्क + अस्वीकरण)                  <- back.png जैसा

फॉन्ट: fonts/Hind-*.ttf, fonts/Tinos-*.ttf (इसी फाइल के बगल के fonts फोल्डर में)
"""
import os
import re
import math
import datetime

from fpdf import FPDF
from fpdf.fonts import FontFace
from fpdf.enums import MethodReturnValue

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE, "fonts")

# ---- संपर्क (बैक पेज) ----
CONTACT_PHONE = "+91 93369 73524"
CONTACT_INSTA = "astropulse_india"

RED = (141, 28, 34)
RED_BRIGHT = (200, 40, 40)
GOLD = (198, 142, 40)
GOLD_DARK = (176, 124, 30)
CREAM_TXT = (255, 228, 162)
PAPER = (254, 248, 234)
BOX = (247, 235, 213)
SOFT = (251, 243, 224)
INK = (40, 30, 26)
GRAY = (110, 100, 92)

PL_HI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
         "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}
PL_SHORT = {"Sun": "सू", "Moon": "चं", "Mars": "मं", "Mercury": "बु", "Jupiter": "गु",
            "Venus": "शु", "Saturn": "श", "Rahu": "रा", "Ketu": "के"}
SIGN_SHORT = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
SIGN_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _hi(planet):
    return PL_HI.get(planet, planet or "-")


def _sign_hi(sign_text):
    if not sign_text:
        return "-"
    m = re.search(r"\(([^)]+)\)", str(sign_text))
    return m.group(1) if m else str(sign_text)


def _sign_num(sign_text):
    s = str(sign_text or "")
    for i, en in enumerate(SIGN_EN):
        if en.lower() in s.lower():
            return i + 1
    return 1


def _dmy(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else str(iso or "-")


def clean_chapter_text(text):
    """Gemini आउटपुट से markdown/HTML के निशान हटाकर साफ पैराग्राफ-लिस्ट बनाता है।"""
    t = (text or "").replace("\r\n", "\n")
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"^\s*#{1,6}\s*", "", t, flags=re.M)
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"^\s*[*\-•]\s+", "• ", t, flags=re.M)
    t = re.sub(r"^\s*[━=\-_]{4,}\s*$", "", t, flags=re.M)
    t = t.replace("`", "")
    lines = [ln.strip() for ln in t.split("\n")]
    return [ln for ln in lines if ln]


# ---------------------------------------------------------------
class AstroPDF(FPDF):
    def __init__(self, person_name=""):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.person_name = person_name
        self.special = set()          # बिना हेडर/फुटर वाले पेज (फ्रंट, बैक)
        self._next_special = False
        self.add_font("Hind", "", os.path.join(FONT_DIR, "Hind-Regular.ttf"))
        self.add_font("Hind", "B", os.path.join(FONT_DIR, "Hind-Bold.ttf"))
        TIN_OK[0] = all(os.path.isfile(os.path.join(FONT_DIR, f)) for f in ("Tinos-Regular.ttf", "Tinos-Bold.ttf", "Tinos-Italic.ttf"))
        if TIN_OK[0]:
            self.add_font("Tin", "", os.path.join(FONT_DIR, "Tinos-Regular.ttf"))
            self.add_font("Tin", "B", os.path.join(FONT_DIR, "Tinos-Bold.ttf"))
            self.add_font("Tin", "I", os.path.join(FONT_DIR, "Tinos-Italic.ttf"))
        self.set_text_shaping(True)
        self.set_auto_page_break(True, margin=24)
        self.set_margins(20, 20, 20)
        self.set_creator("AstroPulse India")
        self.set_author("AstroPulse India")

    def add_special_page(self):
        self._next_special = True
        self.add_page()

    def header(self):
        if self._next_special:
            self.special.add(self.page_no())
            self._next_special = False
            return
        if self.page_no() in self.special:
            return
        self.set_fill_color(*PAPER)
        self.rect(0, 0, 210, 297, "F")
        self.set_draw_color(*RED)
        self.set_line_width(0.7)
        self.rect(8, 8, 194, 281)
        self.set_draw_color(*GOLD)
        self.set_line_width(0.25)
        self.rect(9.6, 9.6, 190.8, 277.8)
        self.set_fill_color(*RED)
        self.rect(8, 8, 194, 6, "F")
        self.set_font("Hind", "B", 8)
        self.set_text_color(255, 255, 255)
        self.set_xy(12, 8.4)
        self.cell(90, 5, "ASTROPULSE INDIA", align="L")
        self.set_xy(108, 8.4)
        self.cell(90, 5, "वैदिक ज्योतिष रिपोर्ट", align="R")
        self.set_xy(20, 20)
        self.set_text_color(*INK)

    def footer(self):   # फुटर सबसे अंत में "पृष्ठ n / N" के साथ लगता है (_stamp_footers)
        pass


def _stamp_footers(pdf):
    total = len(pdf.pages)
    core = total - len(pdf.special)       # फ्रंट और बैक छोड़कर
    pdf.set_auto_page_break(False)
    num = 0
    for pn in range(1, total + 1):
        if pn in pdf.special:
            continue
        num += 1
        pdf.page = pn
        pdf.set_draw_color(*GOLD)
        pdf.set_line_width(0.3)
        pdf.line(20, 282, 190, 282)
        pdf.set_font("Hind", "", 8)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(20, 283.2)
        pdf.cell(120, 5, f"AstroPulse India  |  {pdf.person_name}", align="L")
        pdf.set_xy(140, 283.2)
        pdf.cell(50, 5, f"पृष्ठ {num} / {core}", align="R")
    pdf.page = total


# ---------------------------------------------------------------
# छोटे ड्रॉइंग हेल्पर
# ---------------------------------------------------------------
_DEV = re.compile(r"[\u0900-\u097F]")
TIN_OK = [True]   # Tinos फॉन्ट फाइलें मिलीं या नहीं


def _pick(font, style, text):
    """Tinos में देवनागरी नहीं है; हिंदी अक्षर दिखें (या Tinos फाइल न हो) तो Hind इस्तेमाल करता है।"""
    if font == "Tin" and (not TIN_OK[0] or _DEV.search(str(text))):
        return "Hind", ("B" if "B" in style else "")
    return font, style


def _text(pdf, x, y, w, text, font, style, size, color, align="C", h=None):
    font, style = _pick(font, style, text)
    pdf.set_font(font, style, size)
    pdf.set_text_color(*color)
    pdf.set_xy(x, y)
    pdf.cell(w, h or size * 0.45, text, align=align)


def _fit_size(pdf, text, font, style, max_size, min_size, max_w):
    font, style = _pick(font, style, text)
    size = max_size
    while size > min_size:
        pdf.set_font(font, style, size)
        if pdf.get_string_width(text) <= max_w:
            break
        size -= 0.5
    return size


def _circle(pdf, cx, cy, r, style="D"):
    pdf.ellipse(cx - r, cy - r, 2 * r, 2 * r, style)


def _special_frame(pdf):
    """फ्रंट/बैक पेज का दोहरा फ्रेम (लाल मोटा + सुनहरा पतला) और 4 कोनों की सुनहरी बिंदियाँ।"""
    pdf.set_fill_color(*PAPER)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_draw_color(*RED)
    pdf.set_line_width(1.1)
    pdf.rect(4.7, 4.7, 200.6, 287.6)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.3)
    pdf.rect(7.9, 7.9, 194.2, 281.2)
    pdf.set_fill_color(*GOLD)
    for (x, y) in ((12.8, 12.8), (197.2, 12.8), (12.8, 284.2), (197.2, 284.2)):
        _circle(pdf, x, y, 2.7, "F")


def _header_band(pdf, h=45.3):
    pdf.set_fill_color(*RED)
    pdf.rect(10.7, 10.7, 188.6, h, "F", round_corners=True, corner_radius=6)


# ---------------------------------------------------------------
# 1. फ्रंट पेज
# ---------------------------------------------------------------
def _wheel(pdf, cx, cy, r):
    k = r / 47.8
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(1.5 * k)
    _circle(pdf, cx, cy, r, "D")
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.6 * k)
    _circle(pdf, cx, cy, r * 0.9, "D")
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.5 * k)
    _circle(pdf, cx, cy, r * 0.67, "D")
    for i in range(12):
        a = math.radians(i * 30 + 90)
        pdf.set_line_width(0.55 * k)
        pdf.line(cx + r * 0.67 * math.cos(a), cy - r * 0.67 * math.sin(a),
                 cx + r * 0.9 * math.cos(a), cy - r * 0.9 * math.sin(a))
    pdf.set_fill_color(*RED)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(1.0 * k)
    _circle(pdf, cx, cy, r * 0.38, "DF")
    pdf.set_font("Hind", "", 44 * k)
    pdf.set_text_color(*CREAM_TXT)
    pdf.set_xy(cx - 15 * k, cy - 7.5 * k)
    pdf.cell(30 * k, 15 * k, "ॐ", align="C")


def _front_page(pdf, title_hi, title_en, info, chart, subtitle_hi, is_num):
    pdf.set_auto_page_break(False)
    pdf.add_special_page()
    _special_frame(pdf)
    _header_band(pdf, 45.3)
    _text(pdf, 20, 17.5, 170, "॥ श्री गणेशाय नमः ॥", "Hind", "", 12, CREAM_TXT, h=6)
    _text(pdf, 20, 28, 170, "ASTROPULSE INDIA", "Tin", "B", 31, CREAM_TXT, h=13)
    _text(pdf, 20, 45.6, 170, "Vedic Astrology  ·  Verified Kundli Reports", "Tin", "", 11, (255, 255, 255), h=5)

    t = subtitle_hi
    s = _fit_size(pdf, t, "Hind", "", 26, 14, 176)
    _text(pdf, 17, 63, 176, t, "Hind", "", s, RED, h=12)
    short_en = re.sub(r"\s*Report\s*$", "", title_en, flags=re.I).upper() + " REPORT"
    s2 = _fit_size(pdf, short_en, "Tin", "B", 15, 9, 170)
    _text(pdf, 20, 77.5, 170, short_en, "Tin", "B", s2, GOLD, h=7)

    _wheel(pdf, 105, 140, 47.8)

    name = (info.get("name") or "").upper()
    s3 = _fit_size(pdf, name, "Tin", "B", 26, 12, 170)
    _text(pdf, 20, 191.5, 170, name, "Tin", "B", s3, RED, h=11)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.8)
    pdf.line(28, 206, 182, 206)

    # जन्म विवरण का बॉक्स
    pdf.set_fill_color(*BOX)
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.6)
    pdf.rect(21.4, 214, 167.2, 45, "DF", round_corners=True, corner_radius=3)
    lagna = chart.get("lagna", {}) or {}
    dob = info.get("dob", "")
    if is_num:
        rows = [("जन्म तिथि", dob), ("जन्म समय", info.get("tob", "-")), ("जन्म स्थान", info.get("city", "-")),
                ("रिपोर्ट का प्रकार", "न्यूमरोलॉजी"), ("रिपोर्ट तिथि", datetime.date.today().strftime("%d-%m-%Y"))]
    else:
        rows = [("जन्म तिथि", dob), ("जन्म समय", info.get("tob", "-")), ("जन्म स्थान", info.get("city", "-")),
                ("D1 लग्न", _sign_hi(lagna.get("d1_sign"))), ("रिपोर्ट तिथि", datetime.date.today().strftime("%d-%m-%Y"))]
    y = 217.5
    for lbl, val in rows:
        _text(pdf, 31.3, y, 60, lbl, "Hind", "", 10.5, RED, align="L", h=6)
        vs = _fit_size(pdf, str(val), "Tin", "", 12, 8, 90)
        _text(pdf, 80, y, 98.7, str(val), "Tin", "", vs, INK, align="R", h=6)
        y += 7.9
    _text(pdf, 20, 270.5, 170, "Decode  ·  Understand  ·  Transform", "Tin", "", 12, RED, h=6)
    pdf.set_auto_page_break(True, margin=24)


# ---------------------------------------------------------------
# 2. जन्म विवरण पेज (हेडर/फुटर वाला, "पृष्ठ 1")
# ---------------------------------------------------------------
def _details_page(pdf, title_hi, title_en, info, chart, is_num):
    pdf.add_page()
    pdf.start_section("जन्म विवरण", level=0)
    _text(pdf, 20, 33, 170, "॥ श्री गणेशाय नमः ॥", "Hind", "", 13, RED, h=7)
    _text(pdf, 20, 53, 170, "ASTROPULSE INDIA", "Tin", "B", 38, RED, h=16)
    _text(pdf, 20, 68, 170, "Vedic Astrology  ·  Verified Kundli Reports", "Tin", "", 12, GRAY, h=6)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.8)
    pdf.line(38, 80, 172, 80)
    s = _fit_size(pdf, title_hi, "Hind", "", 32, 15, 170)
    _text(pdf, 20, 90, 170, title_hi, "Hind", "", s, RED, h=14)
    _text(pdf, 20, 104, 170, title_en, "Tin", "", 14, GOLD, h=7)

    pdf.set_fill_color(255, 252, 245)
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.6)
    pdf.rect(21.4, 130, 167.2, 96, "DF", round_corners=True, corner_radius=3)
    lagna = chart.get("lagna", {}) or {}
    indu = chart.get("indu_lagna", {}) or {}
    rows = [("जातक का नाम", info.get("name", "-")), ("लिंग", info.get("gender", "-")),
            ("जन्म तिथि", info.get("dob", "-")), ("जन्म समय", info.get("tob", "-")), ("जन्म स्थान", info.get("city", "-"))]
    if not is_num:
        rows += [("D1 लग्न", f"{_sign_hi(lagna.get('d1_sign'))}  ({_hi(lagna.get('d1_lord'))} स्वामी)"),
                 ("D9 लग्न", _sign_hi(lagna.get("d9_sign"))),
                 ("इन्दु लग्न", _sign_hi(indu.get("indu_lagna_sign")))]
    y = 135.5
    step = 10.2 if len(rows) > 5 else 14
    for lbl, val in rows:
        _text(pdf, 31.3, y, 60, lbl, "Hind", "", 11.5, RED, align="L", h=6)
        vs = _fit_size(pdf, str(val), "Tin", "", 13, 8, 100)
        _text(pdf, 80, y, 98.7, str(val), "Tin", "", vs, INK, align="R", h=6)
        y += step
    _text(pdf, 20, 245, 170, f"रिपोर्ट तैयार करने की तिथि : {datetime.date.today().strftime('%d-%m-%Y')}", "Hind", "", 11, GRAY, h=6)
    _text(pdf, 20, 255, 170, "यह रिपोर्ट वैदिक ज्योतिष के आधार पर मार्गदर्शन के लिए है।" if not is_num
          else "यह रिपोर्ट अंक ज्योतिष के आधार पर मार्गदर्शन के लिए है।", "Hind", "", 11, GRAY, h=6)


# ---------------------------------------------------------------
# आखिरी (बैक) पेज
# ---------------------------------------------------------------
def _back_page(pdf):
    pdf.set_auto_page_break(False)
    pdf.add_special_page()
    _special_frame(pdf)
    _header_band(pdf, 45.3)
    _text(pdf, 20, 22.5, 170, "ASTROPULSE INDIA", "Tin", "B", 31, CREAM_TXT, h=13)
    _text(pdf, 20, 39.5, 170, "Decode  ·  Understand  ·  Transform", "Tin", "", 12, (255, 255, 255), h=6)
    _text(pdf, 20, 68, 170, "आकाश में लिखे संकेतों को समझें,", "Hind", "", 24, RED, h=11)
    _text(pdf, 20, 80, 170, "अपने जीवन की दिशा को पहचानें।", "Hind", "", 24, RED, h=11)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.8)
    pdf.line(29.6, 102, 180.4, 102)
    _text(pdf, 20, 114, 170, "वैदिक ज्योतिष पर आधारित", "Hind", "", 15, INK, h=8)
    _text(pdf, 20, 125, 170, "व्यक्तिगत कुंडली रिपोर्ट एवं ज्योतिषीय मार्गदर्शन", "Hind", "", 15, INK, h=8)

    pdf.set_fill_color(*BOX)
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.8)
    pdf.rect(20, 148.5, 170, 65, "DF", round_corners=True, corner_radius=4)
    _text(pdf, 20, 154, 170, "हमसे जुड़ें", "Hind", "", 22, RED, h=10)
    _text(pdf, 20, 174, 170, f"Instagram  :  {CONTACT_INSTA}", "Tin", "", 15.5, INK, h=8)
    _text(pdf, 20, 187.5, 170, f"WhatsApp  :  {CONTACT_PHONE}", "Tin", "", 15.5, INK, h=8)

    _text(pdf, 20, 227, 170, "अस्वीकरण", "Hind", "", 20, RED, h=9)
    lines = ["यह रिपोर्ट वैदिक ज्योतिषीय मान्यताओं एवं गणनाओं पर आधारित है।",
             "इसे आत्मचिंतन एवं सामान्य मार्गदर्शन के लिए देखें।",
             "जीवन के महत्वपूर्ण निर्णय केवल इस रिपोर्ट के आधार पर न लें।"]
    y = 240
    for ln in lines:
        _text(pdf, 20, y, 170, ln, "Hind", "", 11.5, INK, h=6)
        y += 8.6
    _text(pdf, 20, 275, 170, "ASTROPULSE INDIA  |  CONFIDENTIAL", "Tin", "", 10.5, RED, h=5)
    pdf.set_auto_page_break(True, margin=24)


# ---------------------------------------------------------------
# उत्तर भारतीय कुंडली चार्ट (वेक्टर)
# ---------------------------------------------------------------
_POS = {1: (130, 52), 2: (60, 30), 3: (30, 60), 4: (65, 130), 5: (30, 200), 6: (60, 230),
        7: (130, 208), 8: (200, 230), 9: (230, 200), 10: (195, 130), 11: (230, 60), 12: (200, 30)}
_NUM = {1: (130, 82), 2: (82, 44), 3: (44, 82), 4: (92, 130), 5: (44, 178), 6: (82, 216),
        7: (130, 178), 8: (178, 216), 9: (216, 178), 10: (168, 130), 11: (216, 82), 12: (178, 44)}
_SIGN = {1: (130, 22), 2: (45, 14), 3: (14, 45), 4: (30, 130), 5: (14, 215), 6: (45, 246),
         7: (130, 248), 8: (215, 246), 9: (246, 215), 10: (230, 130), 11: (246, 45), 12: (215, 14)}


def _draw_chart(pdf, chart, kind, x0, y0, size):
    s = size / 260.0
    lagna = chart.get("lagna", {}) or {}
    lagna_sign = lagna.get("d1_sign") if kind == "D1" else lagna.get("d9_sign")
    lagna_num = _sign_num(lagna_sign)
    houses = {i: [] for i in range(1, 13)}
    for p, info in (chart.get("planets", {}) or {}).items():
        h = info.get("d1_house") if kind == "D1" else info.get("d9_house")
        if h in houses:
            houses[h].append(PL_SHORT.get(p, p))
    pdf.set_fill_color(255, 251, 240)
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.7)
    pdf.rect(x0, y0, size, size, "DF")
    pdf.set_line_width(0.4)
    pdf.line(x0, y0, x0 + size, y0 + size)
    pdf.line(x0, y0 + size, x0 + size, y0)
    pdf.set_draw_color(*GOLD)
    m = size / 2
    pdf.polygon([(x0 + m, y0), (x0, y0 + m), (x0 + m, y0 + size), (x0 + size, y0 + m)], style="D")

    def put(txt, cx, cy, fs, bold, color, w=24):
        pdf.set_font("Hind", "B" if bold else "", fs)
        pdf.set_text_color(*color)
        pdf.set_xy(x0 + cx * s - w / 2, y0 + cy * s - 2.5)
        pdf.cell(w, 5, txt, align="C")

    for i in range(1, 13):
        sign_num = (lagna_num + i - 2) % 12 + 1
        put(SIGN_SHORT[sign_num - 1], _SIGN[i][0], _SIGN[i][1], 6.5, True, GOLD, 16)
        put(str(sign_num), _NUM[i][0], _NUM[i][1], 7, True, RED_BRIGHT, 8)
        pl = houses[i]
        put(", ".join(pl), _POS[i][0], _POS[i][1], 8 if len(pl) > 3 else 9.5, True, (17, 24, 39), 30)
    pdf.set_text_color(*INK)


def _section_title(pdf, text):
    pdf.set_font("Hind", "B", 14)
    pdf.set_text_color(*RED)
    pdf.set_x(20)
    pdf.cell(170, 8, text, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.5)
    pdf.line(35, pdf.get_y(), 175, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(*INK)


def _table(pdf, headers, rows, widths, font_size=8.5, align="CENTER", line_height=5.6):
    pdf.set_font("Hind", "", font_size)
    pdf.set_text_color(*INK)
    with pdf.table(
        col_widths=widths, text_align=align, line_height=line_height,
        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=RED),
        cell_fill_color=SOFT, cell_fill_mode="ROWS", borders_layout="ALL", width=sum(widths),
    ) as table:
        r = table.row()
        for h in headers:
            r.cell(h)
        for row in rows:
            r = table.row()
            for c in row:
                r.cell(str(c))


def _page_charts(pdf, chart):
    pdf.add_page()
    pdf.start_section("कुंडली चार्ट और ग्रह स्थिति", level=0)
    pdf.set_y(20)
    _section_title(pdf, "लग्न कुंडली (D1) एवं नवमांश कुंडली (D9)")
    y = pdf.get_y() + 1
    for kind, x, label in (("D1", 24, "जन्म लग्न कुंडली (D1)"), ("D9", 109, "नवमांश कुंडली (D9)")):
        pdf.set_font("Hind", "B", 10)
        pdf.set_text_color(*GOLD)
        pdf.set_xy(x, y)
        pdf.cell(77, 6, label, align="C")
        _draw_chart(pdf, chart, kind, x, y + 7, 77)
    pdf.set_y(y + 7 + 77 + 6)
    _section_title(pdf, "D1 एवं D9 स्पष्ट ग्रह स्थिति तालिका")
    rows = []
    for p, v in (chart.get("planets", {}) or {}).items():
        rows.append([_hi(p), f"{v.get('degree_within_sign', '-')}°", v.get("d1_house", "-"),
                     _sign_hi(v.get("d1_sign")), _hi(v.get("d1_lord")), v.get("d9_house", "-"), _sign_hi(v.get("d9_sign"))])
    _table(pdf, ["ग्रह", "D1 अंश", "D1 भाव", "D1 राशि", "राशि स्वामी", "D9 भाव", "D9 राशि"], rows,
           (24, 24, 22, 28, 26, 22, 24), font_size=9, line_height=6.2)


def _page_dasha(pdf, chart):
    pdf.add_page()
    pdf.start_section("दशा एवं दोष तालिका", level=0)
    pdf.set_y(20)
    dt = chart.get("dasha_timeline", {}) or {}
    curr = dt.get("current_mahadasha", {}) or {}
    _section_title(pdf, f"विम्शोत्तरी दशा तालिका ({_hi(curr.get('lord'))} महादशा)")
    rows = []
    for ad in curr.get("antardashas_breakdown", []) or []:
        rows.append([_hi(curr.get("lord")), _hi(ad.get("lord")), _dmy(ad.get("start_date")), _dmy(ad.get("end_date")),
                     "वर्तमान" if ad.get("is_current") else ""])
    if rows:
        _table(pdf, ["महादशा", "अंतर्दशा", "आरंभ तिथि", "समाप्ति तिथि", "स्थिति"], rows, (30, 30, 36, 36, 38), font_size=8.5, line_height=5.4)
    pdf.ln(4)
    _section_title(pdf, "त्रैकालिक महादशा अनुक्रम")
    seq = []
    for lbl, key in (("पिछली", "previous_mahadasha"), ("वर्तमान", "current_mahadasha"), ("आगामी", "next_mahadasha")):
        md = dt.get(key, {}) or {}
        if md:
            seq.append([lbl, _hi(md.get("lord")), _dmy(md.get("start_date")), _dmy(md.get("end_date"))])
    if seq:
        _table(pdf, ["कालखंड", "महादशा स्वामी", "आरंभ तिथि", "समाप्ति तिथि"], seq, (36, 44, 45, 45), font_size=9, line_height=5.6)
    pdf.ln(4)
    _section_title(pdf, "प्रमुख वैदिक दोष एवं योग प्रमाणीकरण")
    d = chart.get("doshas", {}) or {}
    drows = [
        ["मांगलिक दोष", d.get("manglik", {}).get("details", "-")],
        ["काल सर्प योग", d.get("kaal_sarp", {}).get("details", "-")],
        ["पितृ दोष", d.get("pitra_dosh", {}).get("details", "-")],
        ["शनि साढ़े साती", d.get("sade_sati", {}).get("details", "-")],
    ]
    _table(pdf, ["योग / दोष", "कुंडली में स्थिति"], drows, (34, 136), font_size=8.5, align="LEFT", line_height=5.2)


# ---------------------------------------------------------------
# न्यूमरोलॉजी के दो टेम्पलेट पेज
# ---------------------------------------------------------------
def _page_num_core(pdf, n):
    from numerology import LOSHU_LAYOUT, PLANET
    pdf.add_page()
    pdf.start_section("मूल अंक और लो-शू ग्रिड", level=0)
    pdf.set_y(20)
    _section_title(pdf, "आपके मूल अंक")
    rows = [["मूलांक (जन्म की तारीख का अंक)", n["mulank"], n["mulank_planet"]],
            ["भाग्यांक (पूरी जन्म तिथि का अंक)", n["bhagyank"], n["bhagyank_planet"]]]
    if n["name_number"]:
        rows.append([f"नामांक (कंपाउंड {n['name_compound']})", n["name_number"], n["name_planet"]])
    else:
        rows.append(["नामांक", "उपलब्ध नहीं", "नाम अंग्रेज़ी अक्षरों में दें"])
    _table(pdf, ["अंक", "संख्या", "स्वामी ग्रह"], rows, (80, 40, 50), font_size=10, line_height=7)
    pdf.ln(5)
    _section_title(pdf, "लो-शू ग्रिड (जन्म तिथि के अंक + मूलांक + भाग्यांक)")
    cell, gx, gy = 30, 60, pdf.get_y() + 2
    for r, row in enumerate(LOSHU_LAYOUT):
        for c, d in enumerate(row):
            x, y = gx + c * cell, gy + r * cell
            cnt = n["grid_counts"][d]
            pdf.set_draw_color(*RED)
            pdf.set_line_width(0.5)
            pdf.set_fill_color(*(SOFT if cnt else (236, 232, 226)))
            pdf.rect(x, y, cell, cell, "DF")
            pdf.set_font("Hind", "B", 22 if cnt else 16)
            pdf.set_text_color(*(RED if cnt else (150, 150, 150)))
            pdf.set_xy(x, y + 5)
            pdf.cell(cell, 12, (str(d) * cnt) if cnt else str(d), align="C")
            pdf.set_font("Hind", "", 8)
            pdf.set_text_color(90, 90, 90)
            pdf.set_xy(x, y + cell - 8)
            pdf.cell(cell, 5, PLANET[d][0], align="C")
    pdf.set_y(gy + 3 * cell + 4)
    pres = ", ".join(str(i) for i in range(1, 10) if n["grid_counts"][i]) or "-"
    miss = ", ".join(map(str, n["missing"])) or "कोई नहीं"
    rep = ", ".join(f"{i} ({n['grid_counts'][i]} बार)" for i in n["repeated"]) or "कोई नहीं"
    for lbl, val in (("उपस्थित अंक", pres), ("अनुपस्थित अंक", miss), ("दोहराए गए अंक", rep)):
        pdf.set_x(30)
        pdf.set_font("Hind", "B", 10)
        pdf.set_text_color(*INK)
        pdf.cell(38, 6.5, lbl + ":")
        pdf.set_font("Hind", "", 10)
        pdf.cell(110, 6.5, val, new_x="LMARGIN", new_y="NEXT")


def _page_num_years(pdf, n):
    from numerology import PLANET, MONTHS_HI as MH
    pdf.add_page()
    pdf.start_section("व्यक्तिगत वर्ष और माह अंक", level=0)
    pdf.set_y(20)
    _section_title(pdf, "व्यक्तिगत वर्ष अंक (2026 से 2031)")
    rows = [[y, v, PLANET[v][0]] for y, v in n["personal_years"].items()]
    _table(pdf, ["वर्ष", "व्यक्तिगत वर्ष अंक", "स्वामी ग्रह"], rows, (50, 60, 60), font_size=10, line_height=6.4)
    pdf.ln(4)
    _section_title(pdf, "वर्ष 2027 के व्यक्तिगत माह अंक")
    m = n["personal_months_2027"]
    rows = [[MH[i], m[i], PLANET[m[i]][0], MH[i + 6], m[i + 6], PLANET[m[i + 6]][0]] for i in range(6)]
    _table(pdf, ["माह", "अंक", "ग्रह", "माह", "अंक", "ग्रह"], rows, (32, 18, 35, 32, 18, 35), font_size=9.5, line_height=6.2)
    pdf.ln(4)
    _section_title(pdf, "परंपरागत शुभ सूची (मूलांक और भाग्यांक)")
    lm, lb = n["lucky_mulank"], n["lucky_bhagyank"]
    rows = [[f"मूलांक {n['mulank']}", lm["day"], lm["colors"], lm["mantra"]],
            [f"भाग्यांक {n['bhagyank']}", lb["day"], lb["colors"], lb["mantra"]]]
    _table(pdf, ["अंक", "शुभ दिन", "शुभ रंग", "मंत्र"], rows, (28, 26, 54, 62), font_size=9, line_height=5.6)


# ---------------------------------------------------------------
# अध्याय पेज: टेक्स्ट से पन्ना 80-85% भरने के लिए अपने-आप फॉन्ट/स्पेस
# ---------------------------------------------------------------
CONTENT_TOP = 22.0
FILL_BOTTOM = 270.0          # टेक्स्ट कम से कम यहाँ तक पहुँचे (पन्ने का ~90%)
MAX_BOTTOM = 275.5           # इससे नीचे नहीं (फुटर की रेखा 282 पर है)


def _line_count(pdf, para, fs):
    pdf.set_font("Hind", "", fs)
    w = 166 if para.startswith("• ") else 170
    lines = pdf.multi_cell(w, 1, para, align="J", dry_run=True, output=MethodReturnValue.LINES)
    return max(1, len(lines))


def _layout(pdf, paras, body_top):
    """(फॉन्ट साइज़, लाइन-ऊंचाई mm, पैराग्राफ-गैप mm) चुनता है ताकि टेक्स्ट पन्ने में 90-100% तक पहुँचे।
    पहले सबसे बड़ा फॉन्ट (14.5 से 9.5) जो पन्ने में समाए; फिर भी जगह बचे तो लाइन-स्पेस और पैराग्राफ के बीच की जगह बढ़ाता है।"""
    target = FILL_BOTTOM + 3.0 - body_top      # थोड़ा ऊपर का लक्ष्य
    hi = MAX_BOTTOM - body_top
    n = len(paras)
    fs, nl = 9.5, 0
    for cand in (14.5, 14.0, 13.5, 13.0, 12.5, 12.0, 11.5, 11.0, 10.5, 10.0, 9.5):
        counts = sum(_line_count(pdf, p, cand) for p in paras)
        fs, nl = cand, counts
        if counts * cand * 0.3528 * 1.55 + n * 3.0 <= hi:
            break
    r, gap = 1.55, 3.0

    def height():
        return nl * fs * 0.3528 * r + n * gap
    while height() < target and r < 2.45:
        r += 0.03
    while height() < target and gap < 26.0:
        gap += 0.5
    # ऊपर निकल जाए तो थोड़ा घटाओ
    while height() > hi and gap > 3.0:
        gap -= 0.5
    while height() > hi and r > 1.4:
        r -= 0.02
    return fs, fs * 0.3528 * r, gap


def _chapter(pdf, page_text):
    lines = clean_chapter_text(page_text)
    if not lines:
        return
    title = lines[0].rstrip(":").strip()
    body = lines[1:]
    if len(title) > 110 and not body:
        body, title = [title], "विश्लेषण"
    pdf.set_auto_page_break(True, margin=17)      # अध्याय पन्ने पर 279mm तक लिख सकते हैं (फुटर 282 पर)
    pdf.add_page()
    pdf.start_section(title[:80], level=0)
    pdf.set_y(CONTENT_TOP)
    pdf.set_font("Hind", "B", 16)
    pdf.set_text_color(*RED)
    pdf.multi_cell(170, 9, title, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y() + 1, 190, pdf.get_y() + 1)
    pdf.set_draw_color(*RED_BRIGHT)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y() + 2.2, 80, pdf.get_y() + 2.2)
    pdf.ln(7)
    fs, lh, gap = _layout(pdf, body, pdf.get_y())
    pdf.set_font("Hind", "", fs)
    pdf.set_text_color(*INK)
    for para in body:
        is_bullet = para.startswith("• ")
        pdf.set_x(24 if is_bullet else 20)
        pdf.multi_cell(166 if is_bullet else 170, lh, para, align="L" if is_bullet else "J",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(gap)
    pdf.set_auto_page_break(True, margin=24)


# ---------------------------------------------------------------
def build_report_pdf(title_hi, title_en, chart, info, chapter_pages, numerology=None):
    """
    title_hi/title_en : रिपोर्ट का नाम
    chart             : vedic_engine का chart_data
    info              : {"name","gender","dob","tob","city"}
    chapter_pages     : Gemini के अध्यायों की लिस्ट (हर आइटम = एक पन्ने का टेक्स्ट, पहली लाइन = शीर्षक)
    numerology        : न्यूमरोलॉजी रिपोर्ट के लिए numerology.compute() का dict (वरना None)
    लौटाता है: PDF के bytes
    """
    for f in ("Hind-Regular.ttf", "Hind-Bold.ttf"):
        if not os.path.isfile(os.path.join(FONT_DIR, f)):
            raise FileNotFoundError(f"PDF के लिए फॉन्ट नहीं मिला: fonts/{f} (main.py वाले फोल्डर में 'fonts' फोल्डर रखें)")
    is_num = bool(numerology)
    pdf = AstroPDF(person_name=info.get("name", ""))
    pdf.set_title(f"{title_hi} - {info.get('name', '')}")
    front_title = "व्यक्तिगत अंक ज्योतिष रिपोर्ट" if is_num else "व्यक्तिगत जन्म कुंडली रिपोर्ट"
    _front_page(pdf, title_hi, title_en, info, chart, front_title, is_num)
    _details_page(pdf, title_hi, title_en, info, chart, is_num)
    if is_num:
        _page_num_core(pdf, numerology)
        _page_num_years(pdf, numerology)
    else:
        _page_charts(pdf, chart)
        _page_dasha(pdf, chart)
    for text in chapter_pages:
        _chapter(pdf, text)
    _back_page(pdf)
    _stamp_footers(pdf)
    return bytes(pdf.output())
