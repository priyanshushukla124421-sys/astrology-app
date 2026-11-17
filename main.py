from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from functools import lru_cache
import time
from vedic_engine import get_vedic_planets, ZODIAC_SIGNS
import sqlite3
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AstroPulse India API")
templates = Jinja2Templates(directory="templates")

# ---- वैकल्पिक लॉगिन: Render में APP_PASSWORD सेट करने पर पूरा ऐप पासवर्ड माँगेगा (APP_USER डिफ़ॉल्ट: admin) ----
import base64
import secrets
APP_PASSWORD = os.environ.get("APP_PASSWORD")


@app.middleware("http")
async def basic_auth_guard(request, call_next):
    if not APP_PASSWORD or request.url.path == "/health":
        return await call_next(request)
    ok = False
    hdr = request.headers.get("authorization", "")
    if hdr.lower().startswith("basic "):
        try:
            user, _, pw = base64.b64decode(hdr[6:]).decode("utf-8").partition(":")
            ok = secrets.compare_digest(pw, APP_PASSWORD) and secrets.compare_digest(user, os.environ.get("APP_USER", "admin"))
        except Exception:
            ok = False
    if not ok:
        return Response(content="Login required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="AstroPulse India"'})
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect("astropulse.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gender TEXT,
            dob TEXT,
            tob TEXT,
            city TEXT,
            chart_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 1 से 10 रिपोर्ट्स के लिए विस्तृत मास्टर प्रॉम्प्ट्स ---
DEFAULT_PROMPTS = {
    "consultation": """================================================================================
[30-PAGE ROYAL CALL CONSULTATION & MASTER REPORT - GEMINI GENERATION PROMPT]
================================================================================
आप एक वरिष्ठ वैदिक ज्योतिषाचार्य की भूमिका में कार्य करें।
मुझे नीचे दिए गए जातक के प्रमाणित वैदिक कुंडली डेटा के आधार पर **पन्ना 4 (अध्याय 1) से पन्ना 30 (अध्याय 27) तक के पूरे 27 अध्यायों** का गहन ज्योतिषीय विश्लेषण तैयार करके दें।

================================================================================
⛔ सबसे सख्त नियम (STRICT FORMAT RULES FOR GEMINI - NO GLITCHES):
================================================================================
1. **शुरुआती 3 पन्ने (Page 1, Page 2, Page 3) हमारे सिस्टम टेम्पलेट में पहले से सुरक्षित हैं**, इसलिए आपको कोई भी टेबल, SVG या Page 1-3 का कोड नहीं लिखना है!
2. आपको सीधे **अध्याय 1 (Page 4) से अध्याय 27 (Page 30)** तक पूरे 27 पन्ने लिखने हैं। किसी भी पन्ने को अधूरा न छोड़ें और कहीं भी शॉर्टकट (`...`) का प्रयोग न करें।
3. **हर नए पन्ने (अध्याय) की शुरुआत में अनिवार्य रूप से यह लाइन लिखें:**
   ==================== PAGE BREAK ====================
4. प्रत्येक पन्ने पर सबसे पहली लाइन में केवल उस अध्याय का शीर्षक लिखें (उदाहरण: `अध्याय 1 — कुंडली का मूल सार, लग्न, लग्नेश और चंद्र समन्वय`)।
5. शीर्षक के नीचे **ठीक 4 विस्तृत पैराग्राफ (कुल 360 से 410 शब्द प्रति पन्ना)** लिखें। कोई भी बुलेट पॉइंट्स या सब-हेडिंग न बनाएं, केवल शुद्ध पैराग्राफ लिखें।

================================================================================
📖 पन्ना 4 से पन्ना 30 तक लिखे जाने वाले 27 अध्यायों की अनिवार्य सूची:
================================================================================
- PAGE 4  (अध्याय 1) : कुंडली का मूल सार, [D1 Lagna] लग्न, लग्नेश और चंद्र राशि का समन्वय एवं व्यक्तित्व की मुख्य थीम
- PAGE 5  (अध्याय 2) : प्रथम भाव (लग्न भाव): शारीरिक गठन, आत्मबल, स्वभाव, मान-सम्मान और जीवन की दिशा (D1 व D9 समन्वय सहित)
- PAGE 6  (अध्याय 3) : द्वितीय भाव (धन एवं कुटुंब भाव): संचित धन, वाणी का प्रभाव, पारिवारिक संस्कार और आर्थिक आधार
- PAGE 7  (अध्याय 4) : तृतीय भाव (पराक्रम एवं भ्रातृ भाव): साहस, इच्छाशक्ति, भाई-बहन, संचार कौशल और पुरुषार्थ
- PAGE 8  (अध्याय 5) : चतुर्थ भाव (सुख, माता एवं संपत्ति भाव): मानसिक शांति, माता का सुख, भूमि, भवन, वाहन और घरेलू वातावरण
- PAGE 9  (अध्याय 6) : पंचम भाव (विद्या, बुद्धि एवं संतान भाव): पूर्व पुण्य, बौद्धिक क्षमता, उच्च शिक्षा, प्रेम और संतान सुख
- PAGE 10 (अध्याय 7) : षष्ठ भाव (रोग, ऋण एवं शत्रु भाव): स्वास्थ्य, प्रतिस्पर्धा, दैनिक संघर्ष, नौकरी और शत्रुओं पर विजय
- PAGE 11 (अध्याय 8) : सप्तम भाव (विवाह एवं साझेदारी भाव): जीवनसाथी का स्वभाव, वैवाहिक सुख, व्यापारिक साझेदारी और सामाजिक संबंध
- PAGE 12 (अध्याय 9) : अष्टम भाव (आयु, रहस्य एवं परिवर्तन भाव): दीर्घायु, आकस्मिक घटनाएं, गूढ़ ज्ञान, ससुराल पक्ष और जीवन के बड़े रूपांतरण
- PAGE 13 (अध्याय 10): नवम भाव (भाग्य एवं धर्म भाव): भाग्योदय का समय, गुरु और पिता का आशीर्वाद, लंबी यात्राएं और आध्यात्मिक उन्नति
- PAGE 14 (अध्याय 11): दशम भाव (कर्म, करियर एवं राज्य भाव): आजीविका, व्यवसाय बनाम नौकरी, पद-प्रतिष्ठा, अधिकार और समाज में ख्याति
- PAGE 15 (अध्याय 12): एकादश भाव (लाभ एवं इच्छापूर्ति भाव): आय के स्रोत, इन्दु लग्न का धन प्रभाव, बड़े लाभ और मनोकामना पूर्ति
- PAGE 16 (अध्याय 13): द्वादश भाव (व्यय, विदेश एवं मोक्ष भाव): खर्चों का प्रबंधन, विदेश यात्रा/संबंध, शय्या सुख और मानसिक मुक्ति
- PAGE 17 (अध्याय 14): प्रथम प्रमुख सकारात्मक राजयोग: कुंडली में निर्माण, ग्रहों की स्थिति और जीवन में इसका व्यावहारिक लाभ
- PAGE 18 (अध्याय 15): द्वितीय प्रमुख सकारात्मक धन/करियर योग: आर्थिक उत्थान और पेशेवर सफलता में इस योग की भूमिका
- PAGE 19 (अध्याय 16): तृतीय प्रमुख सकारात्मक योग: लग्न (D1) और नवमांश (D9) के समन्वय से बनने वाला विशेष शुभ प्रभाव
- PAGE 20 (अध्याय 17): चतुर्थ प्रमुख सकारात्मक योग: सामाजिक प्रतिष्ठा, नेतृत्व क्षमता और अचल संपत्ति का विशेष योग
- PAGE 21 (अध्याय 18): पंचम प्रमुख सकारात्मक योग: इन्दु लग्न एवं भाग्योदय से जुड़ा विशेष समृद्धि योग
- PAGE 22 (अध्याय 19): प्रथम प्रमुख जीवन चुनौती / संघर्ष योग: ग्रहों का तनाव और उससे बचने का व्यावहारिक दृष्टिकोण
- PAGE 23 (अध्याय 20): द्वितीय प्रमुख चुनौती: करियर एवं धन संचय में आने वाली रुकावटें और उनका सटीक प्रबंधन
- PAGE 24 (अध्याय 21): तृतीय प्रमुख चुनौती: पारिवारिक एवं वैवाहिक जीवन में संतुलन बनाए रखने के व्यावहारिक सूत्र
- PAGE 25 (अध्याय 22): चतुर्थ प्रमुख चुनौती: स्वास्थ्य, मानसिक तनाव एवं ऊर्जा प्रबंधन की सावधानियां
- PAGE 26 (अध्याय 23): पंचम प्रमुख चुनौती: गोचर एवं दशा संधि के दौरान ध्यान रखने योग्य विशेष सावधानियां
- PAGE 27 (अध्याय 24): पिछली एवं वर्तमान महादशा का गहन काल-विश्लेषण एवं जीवन पर प्रभाव
- PAGE 28 (अध्याय 25): वर्तमान सक्रिय अंतर्दशा, प्रत्यंतर दशा एवं आगामी अंतर्दशाओं का सटीक भविष्यफल
- PAGE 29 (अध्याय 26): जातक के लिए 4 अचूक और व्यावहारिक वैदिक उपाय (बिना किसी रत्न/Gemstone की सलाह के केवल मंत्र, दान, सेवा और अनुशासन)
- PAGE 30 (अध्याय 27): कॉल कंसल्टेशन का अंतिम निचोड़ (5 सबसे बड़ी ताकतें, 5 मुख्य सावधानियां) और आगामी 5 वर्षों का स्वर्णिम रोडमैप

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "d1": """==================================================
[25-PAGE D1 LAGNA MASTER PROMPT - STRICT PARAGRAPH & WORD COUNT RULE]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ और प्रोफेशनल कुंडली रिपोर्ट लेखक की भूमिका में कार्य करें।
मुझे नीचे दी गई जन्म-कुंडली के आधार पर एक अत्यंत विस्तृत, गहन और प्रोफेशनल “लग्न रिपोर्ट (D1 LAGNA REPORT)” तैयार करनी है।

सबसे महत्वपूर्ण निर्देश (STRICT RULES):
1. यह रिपोर्ट ठीक 25 पन्नों की होनी चाहिए (Page 1 से Page 25 तक)।
2. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
3. किसी भी पेज पर केवल एक मुख्य हेडिंग (Top Heading) होगी। इसके अलावा कोई सब-हेडिंग या बुलेट पॉइंट्स (Bullet points) बिल्कुल नहीं होंगे।
4. हर एक पेज पर अनिवार्य रूप से 350 से 450 शब्द होने चाहिए (3 या 4 विस्तृत पैराग्राफ में)।
5. क्रमवार संरचना:
   - PAGE 1: जन्म विवरण, लग्न, नवमांश और कुंडली की मूल रूपरेखा।
   - PAGE 2 से PAGE 13: प्रथम भाव से द्वादश भाव (1 से 12 भाव) तक प्रत्येक भाव का अलग-अलग पन्ने पर D1, D9 और भावेश सहित विस्तृत विश्लेषण।
   - PAGE 14 से PAGE 18: कुंडली के 5 प्रमुख सकारात्मक राजयोग एवं धनयोग (प्रत्येक योग अलग पन्ने पर)।
   - PAGE 19 से PAGE 23: कुंडली की 5 प्रमुख जीवन चुनौतियां एवं संघर्षपूर्ण योग और उनका व्यावहारिक समाधान (प्रत्येक अलग पन्ने पर)।
   - PAGE 24: जातक के लिए 4 अचूक वैदिक उपाय (बिना किसी रत्न/Gemstone के केवल मंत्र, दान, सेवा और अनुशासन)।
   - PAGE 25: संपूर्ण कुंडली का अंतिम निष्कर्ष और जीवन की सफलता का मूल मंत्र।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की संयुक्त ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "career": """==================================================
[25-PAGE CAREER & BUSINESS MASTER PROMPT - STRICT PARAGRAPH & WORD COUNT RULE]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ, Career Astrologer और Business Astrology Analyst की भूमिका में कार्य करें।
मुझे नीचे दिए गए जन्म विवरण, D1, D9 और विम्शोत्तरी दशा के आधार पर 25 पन्नों की अत्यंत विस्तृत “करियर एवं व्यवसाय रिपोर्ट (CAREER & BUSINESS REPORT)” तैयार करनी है।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण:
   - PAGE 1: जन्म विवरण एवं करियर रूपरेखा।
   - PAGE 2 से PAGE 8: करियर से जुड़े मुख्य भावों (प्रथम, द्वितीय, षष्ठ, सप्तम, नवम, दशम और एकादश भाव) का अलग-अलग पन्नों पर गहरा विश्लेषण।
   - PAGE 9 से PAGE 15: नौकरी बनाम व्यापार, सबसे उपयुक्त कार्यक्षेत्र, सरकारी योग, साझेदारी और विदेश से लाभ का विश्लेषण।
   - PAGE 16 से PAGE 18: कुंडली के प्रमुख करियर राजयोग और धन योग।
   - PAGE 19 से PAGE 22: पिछली महादशा, वर्तमान महादशा और सभी अंतर्दशाओं का करियर व आर्थिक स्थिति पर प्रभाव।
   - PAGE 23: करियर की मुख्य चुनौतियां और सावधानियां।
   - PAGE 24: करियर में तरक्की के 4 अचूक वैदिक उपाय (बिना किसी रत्न के)।
   - PAGE 25: संपूर्ण करियर निष्कर्ष और आगामी 5 वर्षों का रोडमैप।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "love": """==================================================
[25-PAGE MARRIAGE & LOVE LIFE MASTER PROMPT - STRICT PARAGRAPH & WORD COUNT RULE]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ और Marriage Astrologer की भूमिका में कार्य करें।
मुझे नीचे दिए गए जन्म विवरण, D1, D9 (नवमांश) और विम्शोत्तरी दशा के आधार पर 25 पन्नों की अत्यंत विस्तृत “मैरिज और लव रिपोर्ट (MARRIAGE & LOVE LIFE REPORT)” तैयार करनी है।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण:
   - PAGE 1: जन्म विवरण, D1-D9 लग्न और वैवाहिक रूपरेखा।
   - PAGE 2 से PAGE 9: वैवाहिक सुख से जुड़े भावों (प्रथम, द्वितीय, चतुर्थ, पंचम, सप्तम, अष्टम, नवम, द्वादश) का गहरा विश्लेषण।
   - PAGE 10 से PAGE 15: प्रेम विवाह बनाम अरेंज मैरिज, जीवनसाथी का स्वभाव, रूप-रंग, करियर, ससुराल पक्ष और विवाह के बाद भाग्योदय।
   - PAGE 16 से PAGE 19: वैवाहिक जीवन के शुभ योग, मांगलिक/अन्य दोषों की वास्तविक स्थिति और सामंजस्य।
   - PAGE 20 से PAGE 23: वर्तमान महादशा एवं अंतर्दशाओं का प्रेम और वैवाहिक जीवन पर प्रभाव।
   - PAGE 24: सुखी वैवाहिक जीवन के लिए 4 अचूक वैदिक उपाय (बिना किसी रत्न के)।
   - PAGE 25: संपूर्ण वैवाहिक निष्कर्ष और सुखद रिश्ते का मूल मंत्र।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "health": """==================================================
[25-PAGE HEALTH, WEALTH & QUALITY OF LIFE MASTER PROMPT]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ (Medical & Lifestyle Astrologer) की भूमिका में कार्य करें।
नीचे दिए गए जन्म विवरण, D1, D9 और विम्शोत्तरी दशा के आधार पर 25 पन्नों की विस्तृत “हेल्थ एंड क्वालिटी ऑफ लाइफ रिपोर्ट” तैयार करें।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण:
   - PAGE 1: जन्म विवरण एवं शारीरिक-मानसिक ऊर्जा रूपरेखा।
   - PAGE 2 से PAGE 13: बारह भावों के अनुसार शारीरिक अंग, रोग प्रतिरोधक क्षमता, मानसिक शांति और जीवन-स्तर (Quality of Life) का विश्लेषण।
   - PAGE 14 से PAGE 18: कुंडली के 5 प्रमुख दीर्घायु, आरोग्य एवं सुख-समृद्धि योग।
   - PAGE 19 से PAGE 23: दशाओं के अनुसार संभावित स्वास्थ्य सावधानियां, खान-पान और मानसिक स्वास्थ्य।
   - PAGE 24: उत्तम स्वास्थ्य के लिए 4 अचूक वैदिक एवं जीवनशैली उपाय (बिना रत्न के)।
   - PAGE 25: अंतिम निष्कर्ष और स्वस्थ-सुखी जीवन का रोडमैप।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "mahadasha": """==================================================
[25-PAGE VIMSHOTTARI MAHADASHA & ANTARDASHA MASTER PROMPT]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ और विम्शोत्तरी दशा विश्लेषक की भूमिका में कार्य करें।
नीचे दिए गए जन्म विवरण, D1, D9 और विम्शोत्तरी दशा तालिका के आधार पर 25 पन्नों की अत्यंत विस्तृत “महादशा एवं अंतर्दशा एनालिसिस रिपोर्ट” तैयार करें।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण:
   - PAGE 1: जन्म विवरण एवं दशा रूपरेखा।
   - PAGE 2: विम्शोत्तरी दशाओं का समग्र अवलोकन।
   - PAGE 3 से PAGE 5: पिछली महादशा — ज्योतिषीय आधार, करियर, आर्थिक और व्यक्तिगत प्रभाव।
   - PAGE 6 से PAGE 9: वर्तमान महादशा — ग्रह की वास्तविक शक्ति (D1 व D9), करियर, धन, विवाह, रिश्ते और स्वास्थ्य पर प्रभाव।
   - PAGE 10 से PAGE 18: वर्तमान महादशा की सभी 9 अंतर्दशाओं का अलग-अलग पन्नों पर विस्तृत विश्लेषण।
   - PAGE 19 से PAGE 20: वर्तमान सक्रिय अंतर्दशा एवं प्रत्यंतर दशा की मौजूदा ऊर्जा, अवसर और सावधानियां।
   - PAGE 21 से PAGE 22: आगामी महादशा — जीवन की नई दिशा, करियर, धन और पारिवारिक बदलाव।
   - PAGE 23: दशा के दौरान सक्रिय होने वाले प्रमुख शुभ राजयोग और परिणाम।
   - PAGE 24: दशा आधारित चुनौतियां और 4 अचूक वैदिक उपाय (बिना रत्न के)।
   - PAGE 25: संपूर्ण दशा विश्लेषण का अंतिम निष्कर्ष (5 सबसे बड़ी ताकतें और 5 मुख्य सावधानियां)।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "premium": """==================================================
[60-PAGE PREMIUM KUNDLI MASTER PROMPT - STRICT PARAGRAPH & WORD COUNT RULE]
==================================================
आप एक वरिष्ठ वैदिक ज्योतिषाचार्य की भूमिका में कार्य करें।
मुझे नीचे दिए गए जन्म विवरण, D1, D9, D24, इन्दु लग्न और विम्शोत्तरी दशा के आधार पर 60 पन्नों की महा-विस्तृत “प्रीमियम कुंडली रिपोर्ट (60-PAGE MASTER REPORT)” तैयार करनी है।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार संरचना (Page 1 से Page 60):
   - PAGE 1: जन्म विवरण एवं कुंडली की संपूर्ण रूपरेखा।
   - PAGE 2 से PAGE 25: प्रथम भाव से द्वादश भाव तक (प्रत्येक भाव के 2 विस्तृत पन्ने: पहला पन्ना ज्योतिषीय आधार एवं व्यक्तित्व/जीवन प्रभाव, दूसरा पन्ना भावेश, D9 समन्वय एवं व्यावहारिक परिणाम)।
   - PAGE 26 से PAGE 35: कुंडली के 10 प्रमुख सकारात्मक राजयोग एवं धनयोग (10 अलग-अलग पन्ने)।
   - PAGE 36 से PAGE 45: कुंडली की 10 प्रमुख जीवन चुनौतियां, दोष एवं व्यावहारिक प्रबंधन (10 अलग-अलग पन्ने)।
   - PAGE 46 से PAGE 58: पिछली महादशा, वर्तमान महादशा की सभी 9 अंतर्दशाएं, प्रत्यंतर दशा और आगामी महादशा का विस्तृत विश्लेषण (13 पन्ने)।
   - PAGE 59: संपूर्ण जीवन के लिए अचूक वैदिक उपाय (बिना रत्न के)।
   - PAGE 60: 60-पेज महा-कुंडली का अंतिम निचोड़ और स्वर्णिम जीवन रोडमैप।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "indu lagna": """==================================================
[25-PAGE INDU LAGNA WEALTH MASTER PROMPT - STRICT PARAGRAPH & WORD COUNT RULE]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ और Financial Astrologer की भूमिका में कार्य करें।
मुझे नीचे दिए गए जन्म विवरण, इन्दु लग्न, D1, D9 और विम्शोत्तरी दशा के आधार पर 25 पन्नों की विस्तृत “INDU LAGNA & WEALTH REPORT” तैयार करनी है।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण:
   - PAGE 1: जन्म विवरण एवं इन्दु लग्न की गणना और महत्व।
   - PAGE 2 से PAGE 13: इन्दु लग्न से सभी 12 भावों का धन, संपत्ति, निवेश और आय के स्रोतों पर प्रभाव।
   - PAGE 14 से PAGE 18: कुंडली के 5 सबसे बड़े धनयोग और करोड़पति योग।
   - PAGE 19 से PAGE 23: वर्तमान महादशा एवं अंतर्दशाओं में आर्थिक उत्थान के वर्ष और निवेश काल।
   - PAGE 24: धन वृद्धि और आर्थिक स्थिरता के 4 अचूक वैदिक उपाय (बिना रत्न के)।
   - PAGE 25: संपूर्ण आर्थिक निष्कर्ष और धन प्रबंधन रोडमैप।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "education": """==================================================
[25-PAGE EDUCATION & INTELLIGENCE (D24) MASTER PROMPT]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ और शिक्षा एवं करियर काउंसलर की भूमिका में कार्य करें।
मुझे नीचे दिए गए जन्म विवरण, D1, D9, D24 (चतुर्विंशांश) और विम्शोत्तरी दशा के आधार पर 25 पन्नों की विस्तृत “एजुकेशन एवं बौद्धिक क्षमता रिपोर्ट” तैयार करनी है।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। कोई सब-हेडिंग या बुलेट पॉइंट्स बिल्कुल नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण:
   - PAGE 1: जन्म विवरण, D1, D9 एवं D24 लग्न की रूपरेखा।
   - PAGE 2 से PAGE 12: शिक्षा से जुड़े भावों (प्रथम, द्वितीय, तृतीय, चतुर्थ, पंचम, षष्ठ, नवम, दशम, एकादश) और बुध-गुरु-चंद्र का गहरा विश्लेषण।
   - PAGE 13 से PAGE 18: उच्च शिक्षा के क्षेत्र, प्रतियोगी परीक्षाएं, विदेश में शिक्षा और रिसर्च के योग।
   - PAGE 19 से PAGE 23: वर्तमान महादशा और अंतर्दशाओं का पढ़ाई और एकाग्रता पर प्रभाव।
   - PAGE 24: स्मरण शक्ति और शिक्षा में सफलता के 4 अचूक वैदिक उपाय (बिना रत्न के)।
   - PAGE 25: अंतिम शैक्षिक निष्कर्ष और करियर चयन मार्गदर्शन।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1, D9 और D24 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1, D9 और D24 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]""",

    "annual": """==================================================
[30-PAGE ANNUAL RASHIFAL 2027 MASTER PROMPT - STRICT PARAGRAPH & WORD COUNT RULE]
==================================================
आप एक अनुभवी वैदिक ज्योतिष विशेषज्ञ, गोचर एवं दशा विश्लेषक की भूमिका में कार्य करें।
मुझे नीचे दिए गए जन्म विवरण, D1, D9 और विम्शोत्तरी दशा (महादशा, अंतर्दशा, प्रत्यंतर, सूक्ष्म) के आधार पर वर्ष 2027 का अत्यंत विस्तृत “वार्षिक राशिफल 2027 (ANNUAL HOROSCOPE 2027)” तैयार करना है।

सबसे महत्वपूर्ण निर्देश:
1. हर नए पेज की शुरुआत में स्पष्ट रूप से "==================== PAGE BREAK ====================" लिखें।
2. किसी भी पेज पर केवल एक मुख्य हेडिंग होगी। इसके अलावा कोई सब-हेडिंग या बुलेट पॉइंट्स नहीं होंगे।
3. हर पेज पर 3 से 4 विस्तृत पैराग्राफ (लगभग 350-450 शब्द) लिखें।
4. क्रमवार विश्लेषण करें:
   - PAGE 1: जन्म विवरण, लग्न, राशि और वर्ष 2027 में सक्रिय महादशा-अंतर्दशा-प्रत्यंतर रूपरेखा।
   - PAGE 2: वर्ष 2027 का समग्र अवलोकन और मुख्य जीवन थीम।
   - PAGE 3 से PAGE 6: वर्ष 2027 में शनि गोचर, बृहस्पति गोचर, राहु-केतु गोचर और तीव्र ग्रहों का आपकी कुंडली पर प्रभाव।
   - PAGE 7 से PAGE 12: वर्ष 2027 में करियर, व्यवसाय, धन-संपत्ति, वैवाहिक/प्रेम जीवन, शिक्षा और स्वास्थ्य का विस्तृत भविष्यफल।
   - PAGE 13 से PAGE 24: जनवरी 2027 से दिसंबर 2027 तक (12 महीनों के 12 अलग-अलग पेज) हर महीने का विस्तृत मासिक भविष्यफल और प्रत्यंतर दशा का प्रभाव।
   - PAGE 25 से PAGE 28: वर्ष 2027 के सबसे शुभ अवसर, प्रमुख सावधानियां, आर्थिक निवेश काल और पारिवारिक सुख।
   - PAGE 29: वर्ष 2027 के 4 अचूक वैदिक उपाय (बिना किसी रत्न/Gemstone के केवल मंत्र, दान, सेवा और अनुशासन)।
   - PAGE 30: वर्ष 2027 का अंतिम निष्कर्ष और सफलता का मूल मंत्र।

━━━━━━━━━━━━━━━━━━━━
जन्म विवरण
━━━━━━━━━━━━━━━━━━━━
नाम: [नाम]
जन्म तारीख: [DD/MM/YYYY]
जन्म समय: [समय]
जन्म स्थान: [स्थान]
D1 लग्न: [D1 Lagna]
D9 लग्न: [D9 Lagna]

━━━━━━━━━━━━━━━━━━━━
D1 और D9 की पूरी ग्रह स्थिति
━━━━━━━━━━━━━━━━━━━━
[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]

━━━━━━━━━━━━━━━━━━━━
विम्शोत्तरी दशा तालिका
━━━━━━━━━━━━━━━━━━━━
[यहां Mahadasha और Antardasha की पूरी तालिका डालें]"""
}

# ============================================================
# AstroPulse India - रिपोर्ट पैकेजेस (डैशबोर्ड के कार्ड्स यहीं से बनते हैं)
# ============================================================
PACKAGES = {
    "premium": {"title": "Premium Complete Life Report", "title_hi": "प्रीमियम कम्प्लीट लाइफ रिपोर्ट", "price": 1100, "pages": 90, "prompt_key": "premium", "delivery": "html", "parts": 4, "group": "top", "desc": "जीवन के हर क्षेत्र का सबसे विस्तृत 90-पेज विश्लेषण"},
    "call": {"title": "Call Consultation Report", "title_hi": "कॉल कंसल्टेशन रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "consultation", "delivery": "html", "parts": 1, "group": "top", "desc": "कॉल कंसल्टेशन के लिए रॉयल बुक रिपोर्ट"},
    "kundli_analysis": {"title": "Kundli Analysis Report", "title_hi": "कुंडली एनालिसिस रिपोर्ट (लग्न + महादशा)", "price": 499, "pages": 60, "prompt_key": "kundli_analysis", "delivery": "html", "parts": 3, "group": "combined", "desc": "D1 लग्न + महादशा का संपूर्ण संयुक्त विश्लेषण"},
    "career_health_wealth": {"title": "Career, Health & Wealth Report", "title_hi": "करियर, हेल्थ एंड वेल्थ रिपोर्ट", "price": 499, "pages": 60, "prompt_key": "career_health_wealth", "delivery": "html", "parts": 3, "group": "combined", "desc": "करियर, धन (इन्दु लग्न) और स्वास्थ्य एक रिपोर्ट में"},
    "marriage_pro": {"title": "Complete Marriage Report", "title_hi": "संपूर्ण मैरिज और रिलेशनशिप रिपोर्ट", "price": 499, "pages": 60, "prompt_key": "marriage_pro", "delivery": "html", "parts": 3, "group": "combined", "desc": "विवाह और रिश्तों का 60-पेज गहन विश्लेषण"},
    "health_longevity": {"title": "Health & Longevity Report", "title_hi": "हेल्थ एंड लॉन्गेविटी रिपोर्ट", "price": 499, "pages": 60, "prompt_key": "health_longevity", "delivery": "html", "parts": 3, "group": "combined", "desc": "स्वास्थ्य, आयु-संकेत, इन्दु लग्न और D1 का संयुक्त विश्लेषण"},
    "education_career": {"title": "Education & Career Report", "title_hi": "एजुकेशन एंड करियर रिपोर्ट", "price": 499, "pages": 60, "prompt_key": "education_career", "delivery": "html", "parts": 3, "group": "combined", "desc": "शिक्षा (D24) और करियर का संयुक्त मार्गदर्शन"},
    "d1": {"title": "D1 Lagna Report", "title_hi": "D1 लग्न रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "d1", "delivery": "html", "parts": 1, "group": "single", "desc": "मुख्य लग्न, 12 भाव, योग और दशा संबंध"},
    "mahadasha": {"title": "Mahadasha Report", "title_hi": "विम्शोत्तरी महादशा रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "mahadasha", "delivery": "html", "parts": 1, "group": "single", "desc": "पिछली, वर्तमान और आगामी दशा, सभी अंतर्दशाएं"},
    "career": {"title": "Career & Business Report", "title_hi": "करियर और बिज़नेस रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "career", "delivery": "html", "parts": 1, "group": "single", "desc": "करियर, नौकरी बनाम व्यवसाय, दशा अनुसार समय"},
    "wealth": {"title": "Indu Lagna & Wealth Report", "title_hi": "इन्दु लग्न और धन रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "wealth", "delivery": "html", "parts": 1, "group": "single", "desc": "इन्दु लग्न, आय के स्रोत और धन वृद्धि"},
    "marriage": {"title": "Marriage & Love Report", "title_hi": "मैरिज और लव लाइफ रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "marriage", "delivery": "html", "parts": 1, "group": "single", "desc": "सप्तम भाव, D9, प्रेम और विवाह समय"},
    "health": {"title": "Health & Quality of Life Report", "title_hi": "हेल्थ एंड क्वालिटी ऑफ लाइफ रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "health", "delivery": "html", "parts": 1, "group": "single", "desc": "स्वास्थ्य, जीवनशैली और मानसिक शांति"},
    "education": {"title": "Education Report", "title_hi": "एजुकेशन और इंटेलिजेंस रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "education", "delivery": "html", "parts": 1, "group": "single", "desc": "शिक्षा, D24 और बौद्धिक क्षमता"},
    "annual": {"title": "Annual Rashifal 2027", "title_hi": "वार्षिक राशिफल 2027", "price": 299, "pages": 30, "prompt_key": "annual", "delivery": "html", "parts": 1, "group": "single", "desc": "2027 के गोचर और 12 महीनों का मासिक फल"},
    "numerology": {"title": "Numerology Report", "title_hi": "न्यूमरोलॉजी (अंक ज्योतिष) रिपोर्ट", "price": 299, "pages": 30, "prompt_key": "numerology", "delivery": "html", "parts": 1, "group": "single", "desc": "मूलांक, भाग्यांक, नामांक, लो-शू ग्रिड और 2027 का व्यक्तिगत वर्ष"},
}
_PACKAGE_BY_TITLE = {v["title"].lower(): k for k, v in PACKAGES.items()}
_PACKAGE_BY_TITLE.update({v["title_hi"]: k for k, v in PACKAGES.items()})

for _k, _v in PACKAGES.items():
    _v.setdefault("group", "package")

def resolve_package(name):
    if not name:
        return None
    if name in PACKAGES:
        return name
    return _PACKAGE_BY_TITLE.get(name.strip().lower()) or _PACKAGE_BY_TITLE.get(name.strip())

def part_instruction(total_pages, parts, part):
    if parts <= 1 or part < 1 or part > parts:
        return ""
    first = 4
    n = total_pages - first + 1
    size = -(-n // parts)
    start = first + (part - 1) * size
    end = min(total_pages, start + size - 1)
    return (f"

━━━━━━━━━━━━━━━━━━━━
PART INSTRUCTION (भाग {part}/{parts})
━━━━━━━━━━━━━━━━━━━━
"
            f"इस बार अध्याय-सूची में से केवल Page {start} से Page {end} तक के पेज लिखें। "
            f"Page {start} से ही शुरू करें और Page {end} पर रुक जाएं। इससे पहले या बाद के पेज न लिखें। "
            f"हर पेज की शुरुआत में PAGE BREAK लाइन और ऊपर के सभी नियम पहले की तरह लागू रहेंगे।")

COMBINED_PROMPTS_FILE = "all_prompts_combined.txt"
_PROMPT_KEY_MAP = {"indu lagna": "indu_lagna"}

def load_combined_prompts():
    import re
    for d in [".", "assets", "prompts"]:
        path = os.path.join(d, COMBINED_PROMPTS_FILE)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    text = f.read().replace("\r\n", "\n")
            except Exception:
                return {}
            found = {}
            pattern = r"#####\[PROMP'''TART\] key=([^\s|]+)[^\n]*\n(.*?)
#####\[PROMPT_END\] key="
            for m in re.finditer(pattern, text, flags=re.S):
                body = m.group(2).strip()
                if len(body) > 100:
                    found[m.group(1)] = body
            return found
    return {}

def get_prompt_content(report_type_decoded):
    report_lower = report_type_decoded.lower()
    if "numerology" in report_lower or "न्यूमरोलॉजी" in report_lower or "अंक ज्योतिष" in report_lower:
        target_keyword = "numerology"
    elif "consultation" in report_lower or "कॉल" in report_lower or "10" in report_lower:
        target_keyword = "consultation"
    elif "annual" in report_lower or "वार्षिक" in report_lower or "2027" in report_lower or "राशिफल" in report_lower:
        target_keyword = "annual"
    elif "indu" in report_lower or "इंदु" in report_lower:
        target_keyword = "indu lagna"
    elif "d1" in report_lower or "लग्न" in report_lower or "lagna" in report_lower:
        target_keyword = "d1"
    elif "career" in report_lower or "करियर" in report_lower:
        target_keyword = "career"
    elif "love" in report_lower or "marriage" in report_lower or "मैरिज" in report_lower or "लव" in report_lower:
        target_keyword = "love"
    elif "health" in report_lower or "हेल्थ" in report_lower:
        target_keyword = "health"
    elif "mahadasha" in report_lower or "महादशा" in report_lower:
        target_keyword = "mahadasha"
    elif "premium" in report_lower or "प्रीमियम" in report_lower:
        target_keyword = "premium"
    elif "education" in report_lower or "एजुकेशन" in report_lower:
        target_keyword = "education"
    else:
        target_keyword = "d1"

    ignored_prefixes = ("requirements", "runtime", "code_artifact", "all_prompts", "consultation_clean")
    search_dirs = [".", "assets", "prompts"]

    combined = load_combined_prompts()
    pkg_id = resolve_package(report_type_decoded)
    if pkg_id:
        pkg_key = PACKAGES[pkg_id]["prompt_key"]
        if pkg_key in combined:
            return combined[pkg_key], f"{COMBINED_PROMPTS_FILE}#{pkg_key}"
        if pkg_id != "call":
            raise FileNotFoundError(f"{COMBINED_PROMPTS_FILE} में '{pkg_key}' प्रॉम्प्ट नहीं मिला।")
    combined_key = _PROMPT_KEY_MAP.get(target_keyword, target_keyword)
    if combined_key in combined:
        return combined[combined_key], f"{COMBINED_PROMPTS_FILE}#{combined_key}"

    if target_keyword == "consultation":
        return DEFAULT_PROMPTS["consultation"], "consultation_clean_prompt.txt"

    for d in search_dirs:
        if os.path.exists(d) and os.path.isdir(d):
            for file in os.listdir(d):
                f_lower = file.lower()
                if f_lower.endswith(".txt") and not f_lower.startswith(ignored_prefixes):
                    if target_keyword in f_lower:
                        full_path = os.path.join(d, file)
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if len(content) > 100:
                                return content, file
    return DEFAULT_PROMPTS.get(target_keyword, DEFAULT_PROMPTS["d1"]), f"{target_keyword}.txt"

def format_vedic_tables_for_prompt(chart_data):
    lagna = chart_data.get("lagna", {})
    indu = chart_data.get("indu_lagna", {})
    planets = chart_data.get("planets", {})
    doshas = chart_data.get("doshas", {})
    dasha_tl = chart_data.get("dasha_timeline", {})
    active_h = dasha_tl.get("active_hierarchy_summary", {})

    d1_lines = [
        f"- D1 लग्न (Ascendant): राशि = {lagna.get('d1_sign')} ({lagna.get('degree_within_sign')}°), लग्नेश = {lagna.get('d1_lord')}",
        f"- इन्दु लग्न (Indu Lagna): राशि = {indu.get('indu_lagna_sign')}, स्वामी = {indu.get('indu_lagna_lord')}, लग्न से भाव = {indu.get('house_from_d1_lagna')}, स्थित ग्रह = {', '.join(indu.get('planets_in_indu_lagna', [])) or 'कोई नहीं'}"
    ]
    for p_name, p_val in planets.items():
        d1_lines.append(f"- {p_name}: D1 राशि = {p_val.get('d1_sign')} ({p_val.get('degree_within_sign')}°), D1 भाव = {p_val.get('d1_house')}, राशि स्वामी = {p_val.get('d1_lord')}")
    d1_only_text = "\n".join(d1_lines)

    d9_lines = [f"- D9 नवमांश लग्न: राशि = {lagna.get('d9_sign')}, नवमांश लग्नेश = {lagna.get('d9_lord')}"]
    for p_name, p_val in planets.items():
        d9_lines.append(f"- {p_name}: D9 राशि = {p_val.get('d9_sign')}, D9 भाव = {p_val.get('d9_house')}, नवमांश राशि स्वामी = {p_val.get('d9_lord')}")
    d9_only_text = "\n".join(d9_lines)

    combined_lines = [
        f"- Lagna (लग्न): D1 = {lagna.get('d1_sign')} ({lagna.get('degree_within_sign')}°, स्वामी: {lagna.get('d1_lord')}) | D9 = {lagna.get('d9_sign')} (स्वामी: {lagna.get('d9_lord')}) | D24 = {lagna.get('d24_sign')}",
        f"- Indu Lagna (इन्दु लग्न): राशि = {indu.get('indu_lagna_sign')}, स्वामी = {indu.get('indu_lagna_lord')}, लग्न से भाव = {indu.get('house_from_d1_lagna')}, स्थित ग्रह = {', '.join(indu.get('planets_in_indu_lagna', [])) or 'कोई नहीं'}"
    ]
    for p_name, p_val in planets.items():
        combined_lines.append(f"- {p_name}: D1 = {p_val.get('d1_sign')} ({p_val.get('degree_within_sign')}°, भाव {p_val.get('d1_house')}, स्वामी: {p_val.get('d1_lord')}) | D9 = {p_val.get('d9_sign')} (भाव {p_val.get('d9_house')}, स्वामी: {p_val.get('d9_lord')}) | D24 = {p_val.get('d24_sign')} (भाव {p_val.get('d24_house')})")
    combined_lines.append("\n=== प्रमुख दोष एवं योग जांच (Verified Dosha Status) ===")
    combined_lines.append(f"- मांगलिक दोष: {doshas.get('manglik', {}).get('details')}")
    combined_lines.append(f"- काल सर्प योग: {doshas.get('kaal_sarp', {}).get('details')}")
    combined_lines.append(f"- पितृ दोष: {doshas.get('pitra_dosh', {}).get('details')}")
    combined_lines.append(f"- शनि साढ़े साती: {doshas.get('sade_sati', {}).get('details')}")
    combined_planets_text = "\n".join(combined_lines)

    prev_md = dasha_tl.get("previous_mahadasha", {})
    curr_md = dasha_tl.get("current_mahadasha", {})
    next_md = dasha_tl.get("next_mahadasha", {})

    dasha_lines = [
        "=== वर्तमान सक्रिय दशा पदानुक्रम (STRICT HIERARCHY - DO NOT MIX) ===",
        f"1. वर्तमान महादशा (Mahadasha): {active_h.get('mahadasha', {}).get('lord')} ({active_h.get('mahadasha', {}).get('start_date')} से {active_h.get('mahadasha', {}).get('end_date')})",
        f"2. वर्तमान अंतर्दशा (Antardasha): {active_h.get('antardasha', {}).get('lord')} ({active_h.get('antardasha', {}).get('start_date')} से {active_h.get('antardasha', {}).get('end_date')})",
        f"3. वर्तमान प्रत्यंतर दशा (Pratyantardasha): {active_h.get('pratyantardasha', {}).get('lord')} ({active_h.get('pratyantardasha', {}).get('start_date')} से {active_h.get('pratyantardasha', {}).get('end_date')})",
        f"4. वर्तमान सूक्ष्म दशा (Sookshma Dasha): {active_h.get('sookshma_dasha', {}).get('lord')} ({active_h.get('sookshma_dasha', {}).get('start_date')} से {active_h.get('sookshma_dasha', {}).get('end_date')})",
        "",
        f"--- पिछली महादशा: {prev_md.get('lord')} ({prev_md.get('start_date')} से {prev_md.get('end_date')}) ---",
        f"--- वर्तमान महादशा ({curr_md.get('lord')}: {curr_md.get('start_date')} से {curr_md.get('end_date')}) की सभी 9 अंतर्दशाएं ---"
    ]
    for ad in curr_md.get("antardashas_breakdown", []):
        marker = " [★ वर्तमान सक्रिय अंतर्दशा ★]" if ad.get("is_current") else ""
        dasha_lines.append(f"  * {curr_md.get('lord')} महादशा -> {ad.get('lord')} अंतर्दशा: {ad.get('start_date')} से {ad.get('end_date')}{marker}")
        if ad.get("is_current"):
            for pd in ad.get("pratyantardashas_breakdown", []):
                pd_marker = " [★ सक्रिय प्रत्यंतर ★]" if pd.get("is_current") else ""
                dasha_lines.append(f"      -> प्रत्यंतर: {pd.get('lord')} ({pd.get('start_date')} से {pd.get('end_date')}){pd_marker}")

    dasha_lines.append(f"\n--- आगामी महादशा ({next_md.get('lord')}: {next_md.get('start_date')} से {next_md.get('end_date')}) की अंतर्दशाएं ---")
    for ad in next_md.get("antardashas_breakdown", []):
        dasha_lines.append(f"  * {next_md.get('lord')} महादशा -> {ad.get('lord')} अंतर्दशा: {ad.get('start_date')} से {ad.get('end_date')}")
    dasha_summary_text = "\n".join(dasha_lines)

    return d1_only_text, d9_only_text, combined_planets_text, dasha_summary_text

def build_transit_year_text(year, chart_data):
    import swisseph as swe
    from datetime import date, timedelta
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    lagna_idx = chart_data["lagna"]["d1_sign_index"]
    moon_idx = chart_data["planets"]["Moon"]["d1_sign_index"]
    bodies = [("Saturn", swe.SATURN), ("Jupiter", swe.JUPITER), ("Rahu", swe.MEAN_NODE), ("Mars", swe.MARS),
              ("Sun", swe.SUN), ("Venus", swe.VENUS), ("Mercury", swe.MERCURY)]

    def sign_of(planet, d):
        jd = swe.julday(d.year, d.month, d.day, 0.0)
        lon = swe.calc_ut(jd, planet, flags)[0][0]
        return int(lon // 30) % 12

    def label(idx):
        return f"{ZODIAC_SIGNS[idx]} (लग्न से भाव {(idx - lagna_idx) % 12 + 1}, चंद्र से भाव {(idx - moon_idx) % 12 + 1})"

    start = date(year, 1, 1)
    out = [f"━━━━━━━━━━━━━━━━━━━━\nवर्ष {year} के गोचर (VERIFIED ENGINE DATA - Lahiri, राशि परिवर्तन की तारीखें)\n━━━━━━━━━━━━━━━━━━━━",
           f"वर्ष के आरंभ ({start.isoformat()}) की स्थिति:"]
    for nm, pid in bodies:
        out.append(f"- {nm}: {label(sign_of(pid, start))}")
    k = sign_of(swe.MEAN_NODE, start)
    out.append(f"- Ketu: {label((k + 6) % 12)}")
    out.append("\nवर्ष के दौरान राशि परिवर्तन:")
    prev = {nm: sign_of(pid, start) for nm, pid in bodies}
    d = start
    end = date(year, 12, 31)
    while d < end:
        d += timedelta(days=1)
        for nm, pid in bodies:
            cur = sign_of(pid, d)
            if cur != prev[nm]:
                out.append(f"- {d.isoformat()}: {nm} -> {label(cur)}" + (f" | Ketu -> {label((cur + 6) % 12)}" if nm == "Rahu" else ""))
                prev[nm] = cur
    return "\n".join(out)

def build_merged_prompt(master_prompt, chart_data, report_type_decoded, name, gender, day, month, year, hour, minute, city):
    d1_text, d9_text, combined_text, dasha_text = format_vedic_tables_for_prompt(chart_data)
    lagna = chart_data.get("lagna", {})
    dob_str = f"{day:02d}/{month:02d}/{year}"
    tob_str = f"{hour:02d}:{minute:02d}"

    filled_prompt = master_prompt
    filled_prompt = filled_prompt.replace("[नाम]", name)
    filled_prompt = filled_prompt.replace("[DD/MM/YYYY]", dob_str)
    filled_prompt = filled_prompt.replace("[समय]", tob_str)
    filled_prompt = filled_prompt.replace("[स्थान]", city)
    filled_prompt = filled_prompt.replace("[D1 Lagna]", lagna.get("d1_sign", ""))
    filled_prompt = filled_prompt.replace("[D9 Lagna]", lagna.get("d9_sign", ""))
    filled_prompt = filled_prompt.replace("[यहां D1 की पूरी ग्रह स्थिति डालें]", d1_text)
    filled_prompt = filled_prompt.replace("[यहां D9 की पूरी ग्रह स्थिति डालें]", d9_text)
    filled_prompt = filled_prompt.replace("[यहां D1 और D9 की पूरी ग्रह स्थिति डालें]", combined_text)
    filled_prompt = filled_prompt.replace("[यहां D1, D9 और D24 की पूरी ग्रह स्थिति डालें]", combined_text)
    filled_prompt = filled_prompt.replace("[यहां Mahadasha और Antardasha की पूरी तालिका डालें]", dasha_text)

    is_numerology = ("numerology" in report_type_decoded.lower() or "न्यूमरोलॉजी" in report_type_decoded)
    if is_numerology:
        import numerology as _num
        num_text = _num.format_for_prompt(_num.compute(name, day, month, year))
        filled_prompt = filled_prompt.replace("[यहां अंक ज्योतिष डेटा डालें]", num_text)
        if num_text not in filled_prompt:
            filled_prompt += f"\n\n━━━━━━━━━━━━━━━━━━━━\nप्रमाणित अंक ज्योतिष डेटा\n━━━━━━━━━━━━━━━━━━━━\n{num_text}"

    if not is_numerology and d1_text not in filled_prompt and combined_text not in filled_prompt:
        filled_prompt += f"\n\n━━━━━━━━━━━━━━━━━━━━\nD1, D9 एवं D24 की पूरी ग्रह स्थिति (VERIFIED ENGINE DATA)\n━━━━━━━━━━━━━━━━━━━━\n{combined_text}"
    if not is_numerology and dasha_text not in filled_prompt:
        filled_prompt += f"\n\n━━━━━━━━━━━━━━━━━━━━\nविम्शोत्तरी दशा तालिका (VERIFIED DASHA TIMELINE)\n━━━━━━━━━━━━━━━━━━━━\n{dasha_text}"

    if "2027" in report_type_decoded or "annual" in report_type_decoded.lower() or "वार्षिक" in report_type_decoded:
        try:
            filled_prompt += "\n\n" + build_transit_year_text(2027, chart_data)
        except Exception:
            pass

    header_block = f"""==================================================
ASTROPULSE INDIA - VERIFIED BIRTH & KUNDLI HEADER
==================================================
REPORT TITLE : {report_type_decoded}
NAME (नाम)    : {name}
GENDER (लिंग) : {gender}
DOB (जन्म तिथि): {dob_str}
TIME (समय)   : {tob_str}
PLACE (स्थान) : {city}
D1 LAGNA     : {lagna.get('d1_sign')} ({lagna.get('degree_within_sign')}°)
D9 LAGNA     : {lagna.get('d9_sign')}
INDU LAGNA   : {chart_data.get('indu_lagna', {}).get('indu_lagna_sign')}
==================================================
[STRICT DASHA HIERARCHY & FORMAT RULE FOR GEMINI]
- महादशा (Mahadasha), अंतर्दशा (Antardasha), प्रत्यंतर दशा (Pratyantardasha), और सूक्ष्म दशा (Sookshma Dasha) के पदानुक्रम को बिल्कुल अलग-अलग और सटीक रखें।
- किसी भी पेज पर यह प्रॉम्प्ट या निर्देश वापस न दोहराएं, केवल शुद्ध और गहरा हिंदी ज्योतिषीय विश्लेषण (350-450 शब्द प्रति पेज) आउटपुट करें।
==================================================

"""
    return header_block + filled_prompt


# ... (Skipped redundant HTML and PDF generation code for brevity; keeping core logic intact) ...
# Please assume `generate_kundli_svg_server` and `build_full_30_page_consultation_html` are identical to original.
# The focus is modifying Gemini integration safely.

# ============================================================
# AstroPulse AI - GEMINI API INTEGRATION FIXES
# ============================================================
import threading as _th

_KEY_COOLDOWN = {}
_LAST_ERR = {}
_KEY_RR = [0]
_KEY_LOCK = _th.Lock()
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _gemini_keys():
    keys = []
    for var in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GOOGLE_API_KEY"):
        v = (os.environ.get(var) or "").strip()
        if v:
            keys.append(v)
    for v in (os.environ.get("GEMINI_API_KEYS") or "").split(","):
        if v.strip():
            keys.append(v.strip())
            
    # [FIX] Removed API KEYS folder tracking to prevent GitHub Secret Alerts.
    # We now strictly enforce loading from .env or environment variables.
    
    seen, out = set(), []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out

_CLIENTS = {}

def _client_for(k):
    """हर key का एक ही client बनाकर रखते हैं (बीच में बंद न हो, इसलिए cache)।"""
    if k not in _CLIENTS:
        from google import genai
        # [FIX] vertexai=True removed. Standard genai initialized for AIza keys.
        _CLIENTS[k] = genai.Client(api_key=k)
    return _CLIENTS[k]

def _generate(k, model, contents, config):
    """AI Studio API Key के साथ सुरक्षित रूप से जनरेट करता है।"""
    try:
        r = _client_for(k).models.generate_content(model=model, contents=contents, config=config)
        return r
    except Exception as e:
        raise RuntimeError(str(e))

def _quota_err(msg):
    m = (msg or "").lower()
    return "429" in m or "resource_exhausted" in m or "quota" in m or "rate limit" in m

def _badkey_err(msg):
    m = (msg or "").lower()
    return "api key not valid" in m or "api_key_invalid" in m or "permission_denied" in m or "api key expired" in m

def _gemini_run(fn, scope="", wait=True):
    keys = _gemini_keys()
    if not keys:
        raise RuntimeError("कोई Gemini API key नहीं मिली। कृपया GEMINI_API_KEY को .env फ़ाइल में सेट करें।")
    last = None
    for rnd in range(2):
        now = time.time()
        with _KEY_LOCK:
            start = _KEY_RR[0]
            _KEY_RR[0] += 1
        order = [keys[(start + i) % len(keys)] for i in range(len(keys))]
        usable = [k for k in order if _KEY_COOLDOWN.get((k, scope), 0) <= now]
        if not usable:
            if rnd == 0 and wait:
                time.sleep(min(max(min(_KEY_COOLDOWN.get((k, scope), 0) for k in keys) - now, 1), 75))
                continue
            break
        for k in usable:
            try:
                return fn(k)
            except Exception as e:
                msg = str(e)
                last = e
                _LAST_ERR[scope] = msg[:200]
                if _quota_err(msg):
                    _KEY_COOLDOWN[(k, scope)] = time.time() + 70
                    continue
                if _badkey_err(msg):
                    _KEY_COOLDOWN[(k, scope)] = time.time() + 3600
                    continue
                raise
    raise last or RuntimeError("सभी Gemini keys की सीमा खत्म है। " + _LAST_ERR.get(scope, "-"))

_DEFAULT_MODELS = "gemini-1.5-flash,gemini-1.5-pro"
_DEAD_MODELS = {}
_GOOD_MODEL = [None]

def _model_chain():
    raw = os.environ.get("GEMINI_MODELS") or _DEFAULT_MODELS
    out = []
    for m in raw.split(","):
        m = m.strip()
        if m and m not in out:
            out.append(m)
    return out

def _gen_chain(contents, config):
    now = time.time()
    chain = _model_chain()
    order = [m for m in chain if _DEAD_MODELS.get(m, 0) <= now] or chain
    g = _GOOD_MODEL[0]
    if g in order:
        order = [g] + [m for m in order if m != g]
    last = None
    for m in order:
        try:
            r = _gemini_run(lambda k, m=m: _generate(k, m, contents, config), scope=m, wait=False)
            _GOOD_MODEL[0] = m
            return r, m
        except Exception as e:
            msg = str(e)
            last = e
            if "limit: 0" in msg or "NOT_FOUND" in msg or "404" in msg:
                _DEAD_MODELS[m] = time.time() + 6 * 3600
                continue
            if _quota_err(msg) or "सीमा (quota)" in msg or _badkey_err(msg):
                continue
            raise
    raise last or RuntimeError("कोई मॉडल उपलब्ध नहीं मिला।")

# ... (End of modified Gemini logic, remaining APIs untouched) ...
