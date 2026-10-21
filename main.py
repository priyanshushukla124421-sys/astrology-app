from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from vedic_engine import get_vedic_planets
import sqlite3
import urllib.parse
import os

app = FastAPI(title="AstroPulse India API")
templates = Jinja2Templates(directory="templates")

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


def get_prompt_content(report_type_decoded):
    """
    प्रोजेक्ट फोल्डर में मौजूद .txt प्रॉम्प्ट फाइल को ढूँढता है, या डिफ़ॉल्ट मास्टर प्रॉम्प्ट देता है।
    """
    report_lower = report_type_decoded.lower()
    if "consultation" in report_lower or "कॉल" in report_lower or "10" in report_lower:
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

    ignored_prefixes = ("requirements", "runtime", "code_artifact")
    search_dirs = [".", "assets", "prompts"]

    # कंसल्टेशन रिपोर्ट के लिए हम क्लीन टेक्स्ट प्रॉम्प्ट प्राथमिकता से देते हैं ताकि Page 3 की टेबल कभी न टूटे
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
        d1_lines.append(
            f"- {p_name}: D1 राशि = {p_val.get('d1_sign')} ({p_val.get('degree_within_sign')}°), D1 भाव = {p_val.get('d1_house')}, राशि स्वामी = {p_val.get('d1_lord')}"
        )
    d1_only_text = "\n".join(d1_lines)

    d9_lines = [
        f"- D9 नवमांश लग्न: राशि = {lagna.get('d9_sign')}, नवमांश लग्नेश = {lagna.get('d9_lord')}"
    ]
    for p_name, p_val in planets.items():
        d9_lines.append(
            f"- {p_name}: D9 राशि = {p_val.get('d9_sign')}, D9 भाव = {p_val.get('d9_house')}, नवमांश राशि स्वामी = {p_val.get('d9_lord')}"
        )
    d9_only_text = "\n".join(d9_lines)

    combined_lines = [
        f"- Lagna (लग्न): D1 = {lagna.get('d1_sign')} ({lagna.get('degree_within_sign')}°, स्वामी: {lagna.get('d1_lord')}) | D9 = {lagna.get('d9_sign')} (स्वामी: {lagna.get('d9_lord')}) | D24 = {lagna.get('d24_sign')}",
        f"- Indu Lagna (इन्दु लग्न): राशि = {indu.get('indu_lagna_sign')}, स्वामी = {indu.get('indu_lagna_lord')}, लग्न से भाव = {indu.get('house_from_d1_lagna')}, स्थित ग्रह = {', '.join(indu.get('planets_in_indu_lagna', [])) or 'कोई नहीं'}"
    ]
    for p_name, p_val in planets.items():
        combined_lines.append(
            f"- {p_name}: D1 = {p_val.get('d1_sign')} ({p_val.get('degree_within_sign')}°, भाव {p_val.get('d1_house')}, स्वामी: {p_val.get('d1_lord')}) | D9 = {p_val.get('d9_sign')} (भाव {p_val.get('d9_house')}, स्वामी: {p_val.get('d9_lord')}) | D24 = {p_val.get('d24_sign')} (भाव {p_val.get('d24_house')})"
        )
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

    if d1_text not in filled_prompt and combined_text not in filled_prompt:
        filled_prompt += f"\n\n━━━━━━━━━━━━━━━━━━━━\nD1, D9 एवं D24 की पूरी ग्रह स्थिति (VERIFIED ENGINE DATA)\n━━━━━━━━━━━━━━━━━━━━\n{combined_text}"
    if dasha_text not in filled_prompt:
        filled_prompt += f"\n\n━━━━━━━━━━━━━━━━━━━━\nविम्शोत्तरी दशा तालिका (VERIFIED DASHA TIMELINE)\n━━━━━━━━━━━━━━━━━━━━\n{dasha_text}"

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


def generate_kundli_svg_server(chart_data, chart_type="D1"):
    """
    HTML टेम्पलेट के लिए सिंगल-लाइन उत्तर भारतीय शैली का D1 और D9 लग्न चार्ट (SVG) बनाता है।
    """
    zodiacs = [
        "Aries (मेष)", "Taurus (वृषभ)", "Gemini (मिथुन)", "Cancer (कर्क)",
        "Leo (सिंह)", "Virgo (कन्या)", "Libra (तुला)", "Scorpio (वृश्चिक)",
        "Sagittarius (धनु)", "Capricorn (मकर)", "Aquarius (कुंभ)", "Pisces (मीन)"
    ]
    sign_short = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
    pl_short = {"Sun": "सू", "Moon": "चं", "Mars": "मं", "Mercury": "बु", "Jupiter": "गु", "Venus": "शु", "Saturn": "श", "Rahu": "रा", "Ketu": "के"}

    lagna_sign_str = chart_data["lagna"]["d1_sign"] if chart_type == "D1" else chart_data["lagna"]["d9_sign"]
    lagna_num = zodiacs.index(lagna_sign_str) + 1 if lagna_sign_str in zodiacs else 1

    houses = {i: [] for i in range(1, 13)}
    for p, p_info in chart_data.get("planets", {}).items():
        h = p_info["d1_house"] if chart_type == "D1" else p_info["d9_house"]
        houses[h].append(pl_short.get(p, p))

    pos = {1:(130,52), 2:(60,30), 3:(30,60), 4:(65,130), 5:(30,200), 6:(60,230), 7:(130,208), 8:(200,230), 9:(230,200), 10:(195,130), 11:(230,60), 12:(200,30)}
    num_pos = {1:(130,82), 2:(82,44), 3:(44,82), 4:(92,130), 5:(44,178), 6:(82,216), 7:(130,178), 8:(178,216), 9:(216,178), 10:(168,130), 11:(216,82), 12:(178,44)}
    sign_pos = {1:(130,30), 2:(40,20), 3:(20,40), 4:(42,130), 5:(20,220), 6:(40,240), 7:(130,235), 8:(220,240), 9:(240,220), 10:(218,130), 11:(240,40), 12:(220,20)}

    svg_parts = [
        '<svg width="210" height="210" viewBox="0 0 260 260" style="background:#fffdf7; border:2px solid #991b1b; border-radius:4px;">',
        '<text x="130" y="130" fill="#dc2626" font-size="22" font-weight="bold" text-anchor="middle" alignment-baseline="middle" opacity="0.10" transform="rotate(-45 130 130)">AstroPulse India</text>',
        '<rect x="0" y="0" width="260" height="260" fill="none" stroke="#991b1b" stroke-width="3"/>',
        '<line x1="0" y1="0" x2="260" y2="260" stroke="#991b1b" stroke-width="1.5"/>',
        '<line x1="0" y1="260" x2="260" y2="0" stroke="#991b1b" stroke-width="1.5"/>',
        '<polygon points="130,0 0,130 130,260 260,130" fill="none" stroke="#b45309" stroke-width="1.5"/>'
    ]
    for i in range(1, 13):
        sign_num = (lagna_num + i - 2) % 12 + 1
        s_name = sign_short[sign_num - 1]
        svg_parts.append(f'<text x="{sign_pos[i][0]}" y="{sign_pos[i][1]}" font-size="9" font-weight="bold" text-anchor="middle" fill="#b45309">{s_name}</text>')
        svg_parts.append(f'<text x="{num_pos[i][0]}" y="{num_pos[i][1]}" font-size="10" font-weight="bold" text-anchor="middle" fill="#dc2626">{sign_num}</text>')
        p_list = houses[i]
        p_text = ", ".join(p_list)
        f_size = "10" if len(p_list) > 3 else "12"
        svg_parts.append(f'<text x="{pos[i][0]}" y="{pos[i][1]}" font-size="{f_size}" font-weight="bold" text-anchor="middle" fill="#111827">{p_text}</text>')
    svg_parts.append('</svg>')
    return "".join(svg_parts)


def build_full_30_page_consultation_html(chart_data, name, gender, day, month, year, hour, minute, city, report_title="कॉल कंसल्टेशन और मास्टर रिपोर्ट"):
    lagna = chart_data.get("lagna", {})
    indu = chart_data.get("indu_lagna", {})
    planets = chart_data.get("planets", {})
    doshas = chart_data.get("doshas", {})
    active_h = chart_data.get("dasha_timeline", {}).get("active_hierarchy_summary", {})
    curr_md = chart_data.get("dasha_timeline", {}).get("current_mahadasha", {})
    prev_md = chart_data.get("dasha_timeline", {}).get("previous_mahadasha", {})
    next_md = chart_data.get("dasha_timeline", {}).get("next_mahadasha", {})

    dob_str = f"{day:02d}-{month:02d}-{year}"
    tob_str = f"{hour:02d}:{minute:02d}"
    footer_user_info = f"{name} / {dob_str} / {tob_str} / {city}"

    d1_svg = generate_kundli_svg_server(chart_data, "D1")
    d9_svg = generate_kundli_svg_server(chart_data, "D9")

    pl_hindi = {"Sun": "सूर्य (Sun)", "Moon": "चंद्र (Moon)", "Mars": "मंगल (Mars)", "Mercury": "बुध (Mercury)", "Jupiter": "गुरु (Jupiter)", "Venus": "शुक्र (Venus)", "Saturn": "शनि (Saturn)", "Rahu": "राहु (Rahu)", "Ketu": "केतु (Ketu)"}

    planet_rows_html = f"<tr><td><b>Lagna (लग्न)</b></td><td>{lagna.get('degree_within_sign')}°</td><td>1</td><td>{lagna.get('d1_sign')}</td><td>{lagna.get('d1_lord')}</td><td>1</td><td>{lagna.get('d9_sign')}</td></tr>"
    for p_key, p_info in planets.items():
        planet_rows_html += f"<tr><td><b>{pl_hindi.get(p_key, p_key)}</b></td><td>{p_info.get('degree_within_sign')}°</td><td>{p_info.get('d1_house')}</td><td>{p_info.get('d1_sign')}</td><td>{p_info.get('d1_lord')}</td><td>{p_info.get('d9_house')}</td><td>{p_info.get('d9_sign')}</td></tr>"

    ad_rows_html = ""
    for ad in curr_md.get("antardashas_breakdown", []):
        row_style = "background-color: #fef08a; font-weight: bold;" if ad.get("is_current") else ""
        status_badge = "🟢 वर्तमान सक्रिय" if ad.get("is_current") else "अंतर्दशा"
        ad_rows_html += f'<tr style="{row_style}"><td>{curr_md.get("lord")} महादशा</td><td>{ad.get("lord")} अंतर्दशा</td><td>{ad.get("start_date")}</td><td>{ad.get("end_date")}</td><td>{status_badge}</td></tr>'

    # .txt प्रॉम्प्ट को सीधे HTML पेज में डाउनलोड करने के लिए तैयार करें
    master_prompt, _ = get_prompt_content(report_title)
    merged_txt_prompt = build_merged_prompt(master_prompt, chart_data, report_title, name, gender, day, month, year, hour, minute, city)
    escaped_txt_prompt = (
        merged_txt_prompt.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
        .replace("</script>", "<\\/script>")
    )

    chapters_data = [
        (f"अध्याय 1 — कुंडली का मूल सार, {lagna.get('d1_sign')} लग्न, लग्नेश और चंद्र समन्वय", [
            f"{name} जी, आपकी जन्म कुंडली का लग्न {lagna.get('d1_sign')} ({lagna.get('degree_within_sign')}°) है और इसके स्वामी {lagna.get('d1_lord')} हैं। इस लग्न के जातक जन्मजात रूप से दृढ़ निश्चयी होते हैं और जीवन में किसी भी विपरीत परिस्थिति में हार न मानने का अदम्य साहस रखते हैं। लग्नेश {lagna.get('d1_lord')} आपको एक कर्मठ और लक्ष्य-केंद्रित मानसिकता प्रदान करते हैं।",
            f"वहीं दूसरी ओर, आपकी कुंडली में चंद्रमा {planets.get('Moon', {}).get('d1_sign')} राशि (भाव {planets.get('Moon', {}).get('d1_house')}) में स्थित है। लग्न और चंद्रमा का यह समन्वय आपके व्यक्तित्व में ऊर्जा और भावनात्मक गहराई का एक अद्भुत संतुलन बनाता है। बाहर से आप जितने अनुशासित दिखाई देते हैं, भीतर से आपकी संवेदनाएं उतनी ही गहरी और परिष्कृत हैं।",
            f"नवमांश (D9) कुंडली में आपका लग्न {lagna.get('d9_sign')} है, जिसके स्वामी {lagna.get('d9_lord')} हैं। लग्न (D1) और नवमांश (D9) का यह संयोग दर्शाता है कि आयु बढ़ने के साथ-साथ आपकी दूरदर्शिता, परिपक्वता और निर्णय क्षमता अत्यंत प्रभावशाली होती जाएगी। लोग आपके व्यक्तित्व और वैचारिक स्पष्टता से स्वाभाविक रूप से आकर्षित होते हैं।",
            "निष्कर्षतः, आपकी कुंडली का मूल सार यह है कि आप एक अत्यंत सक्षम और आत्मनिर्भर व्यक्ति हैं। यदि आप अपनी ऊर्जा को सही एकाग्रता और मानसिक शांति के साथ दिशा दें, तो जीवन में प्रत्येक बड़ा लक्ष्य प्राप्त कर सकते हैं। ध्यान और आत्म-चिंतन आपके इस विशेष व्यक्तित्व को और भी निखारने का सबसे सशक्त माध्यम सिद्ध होंगे।"
        ]),
        ("अध्याय 2 — प्रथम भाव (लग्न भाव): शारीरिक गठन, आत्मबल और स्वभाव", [
            f"प्रथम भाव आपके स्वयं के अस्तित्व, शारीरिक गठन, प्राण शक्ति और जीवन के प्रति दृष्टिकोण को दर्शाता है। आपका {lagna.get('d1_sign')} लग्न {lagna.get('degree_within_sign')}° पर उदित हो रहा है, जिसके फलस्वरूप आपका व्यक्तित्व गंभीर, विश्लेषणात्मक और स्वाभिमानी है। आप किसी भी विषय की तह तक जाने की स्वाभाविक प्रवृत्ति रखते हैं।",
            f"लग्नेश {lagna.get('d1_lord')} आपकी कुंडली के भाव {planets.get(lagna.get('d1_lord'), {}).get('d1_house', 1)} ({planets.get(lagna.get('d1_lord'), {}).get('d1_sign', '')}) में विराजमान हैं। लग्नेश की यह स्थिति आपको अद्भुत शारीरिक प्रतिरोधक क्षमता और संघर्ष शक्ति देती है। आप चुनौतियों को ही अपनी सीढ़ी बनाकर सफलता के शिखर तक पहुँचने वाले व्यक्ति हैं।",
            f"नवमांश (D9) कुंडली में {lagna.get('d9_sign')} लग्न उदित होने से आपके जीवन का उत्तरार्ध और आंतरिक बल अत्यंत सुदृढ़ दिखाई देता है। यह स्थिति यह संकेत देती है कि समय के साथ आप समाज-कल्याण, बौद्धिक कार्यों और उच्च स्तरीय प्रबंधन में गहरी रुचि लेंगे। आपकी सोच समय से आगे की रहेगी।",
            "कुल मिलाकर, प्रथम भाव का यह विश्लेषण स्पष्ट करता है कि आपके पास एक मजबूत आत्मबल है जो बड़ी से बड़ी परिस्थिति में भी अडिग रह सकता है। आपको केवल मानसिक उद्वेग और जल्दबाजी से बचना है। आपका मान-सम्मान समाज में आपके अपने पुरुषार्थ और कर्मठता के बल पर स्थापित होगा।"
        ]),
        ("अध्याय 3 — द्वितीय भाव (धन एवं कुटुंब भाव): संचित धन और वाणी", [
            "ज्योतिष शास्त्र में द्वितीय भाव आपके संचित धन (Bank Balance), पारिवारिक संस्कारों, वाणी और खान-पान को नियंत्रित करता है। आपकी कुंडली में धन भाव और बृहस्पति-शनि का प्रभाव यह सुनिश्चित करता है कि आपके जीवन में स्थायी संपत्ति और धन संचय का प्रबल आधार मौजूद है।",
            f"शनि देव आपकी कुंडली में {planets.get('Saturn', {}).get('d1_sign')} राशि (भाव {planets.get('Saturn', {}).get('d1_house')}) में {planets.get('Saturn', {}).get('degree_within_sign')}° पर स्थित हैं। यह स्थिति दर्शाती है कि जीवन के प्रारंभिक वर्षों में धन संचय की गति अनुशासित रहती है और आपको हर एक रुपये की कीमत का गहरा एहसास होता है।",
            "वाणी के दृष्टिकोण से, आप सत्यनिष्ठ, तार्किक और स्पष्टवादी हैं। आप लाग-लपेट वाली बातें पसंद नहीं करते, जिसके कारण कई बार लोग आपकी स्पष्ट बातों को कठोर समझ बैठते हैं। यदि आप अपनी वाणी में थोड़ी मधुरता और कूटनीति का समावेश कर लें, तो आपके पारिवारिक व व्यावसायिक संबंध और अधिक मधुर हो जाएंगे।",
            "आर्थिक आधार के रूप में, यह भाव आपको 30 से 34 वर्ष की आयु के पश्चात अत्यंत ठोस वित्तीय स्थिरता प्रदान करने का संकेत देता है। आपके द्वारा भूमि, स्वर्ण या दीर्घकालिक सुरक्षित योजनाओं में किया गया निवेश भविष्य में बहुत बड़ा लाभ प्रदान करेगा।"
        ]),
        ("अध्याय 4 — तृतीय भाव (पराक्रम एवं भ्रातृ भाव): साहस और संचार", [
            f"तृतीय भाव जातक के साहस, पुरुषार्थ, संचार कौशल (Communication), छोटी यात्राओं और भाई-बहनों का प्रतिनिधित्व करता है। आपकी कुंडली में राहु {planets.get('Rahu', {}).get('d1_sign')} राशि (भाव {planets.get('Rahu', {}).get('d1_house')}) में और मंगल भाव {planets.get('Mars', {}).get('d1_house')} में स्थित होकर आपके पराक्रम को असाधारण बल प्रदान कर रहे हैं।",
            "यह ग्रह स्थिति आपके भीतर असीमित ऊर्जा और जोखिम उठाने का साहस (Risk-taking ability) पैदा करती है। आप उन कार्यों को भी आसानी से कर गुजरते हैं, जिन्हें अन्य लोग कठिन मानते हैं। आधुनिक तकनीक, मीडिया, मार्केटिंग या प्रबंधन से जुड़े कार्यों में आपकी रणनीतिक सोच कमाल की रहती है।",
            "आप अपने पुरुषार्थ के बल पर अपना भाग्य स्वयं लिखने वाले (Self-made) व्यक्ति हैं। जब भी जीवन में कोई संकट आता है, तो आपकी त्वरित निर्णय क्षमता आपको मुश्किलों से बाहर निकलने की युक्ति प्रदान कर देती है। भाई-बहनों और मित्रों के प्रति आपका दृष्टिकोण सहयोगात्मक किंतु व्यावहारिक रहता है।",
            "आपकी इच्छाशक्ति का स्तर बहुत ऊंचा है। यदि आप अपनी इस अपार ऊर्जा को सकारात्मक रूप से नेटवर्किंग और अपने कार्यक्षेत्र के विस्तार में लगाएं, तो आपको अपार सफलता मिलेगी। व्यावसायिक यात्राओं के माध्यम से भी लाभ प्राप्त होने के प्रबल योग हैं।"
        ]),
        ("अध्याय 5 — चतुर्थ भाव (सुख, माता एवं संपत्ति भाव): घरेलू वातावरण", [
            "चतुर्थ भाव मनुष्य के जीवन में मानसिक शांति, माता का सुख, अचल संपत्ति (जमीन, मकान) और वाहन सुख का प्रतिनिधित्व करता है। आपकी कुंडली में चतुर्थ भाव और शुक्र-चंद्रमा की स्थिति यह दर्शाती है कि आप अपने जीवन में एक सुसज्जित और सर्वसुविधायुक्त घर का निर्माण अवश्य करेंगे।",
            "अचल संपत्ति का निर्माण आपके अपने संचित धन और कड़ी मेहनत से होगा। आपको पैतृक रूप से भी सहयोग मिल सकता है, किंतु स्वयं के पुरुषार्थ से अर्जित भूमि और वाहन का सुख आपको सर्वाधिक आत्मिक संतुष्टि प्रदान करेगा। प्रॉपर्टी के मामलों में आपका चयन अत्यंत परिपक्व रहेगा।",
            "घरेलू वातावरण और मानसिक शांति की बात करें, तो कभी-कभी कार्यक्षेत्र की व्यस्तता और जिम्मेदारियों के कारण आपको घर में पर्याप्त समय न दे पाने की अनुभूति हो सकती है। माता जी के स्वास्थ्य और उनकी भावनाओं का विशेष ध्यान रखना आपके भाग्योदय के लिए अत्यंत शुभ रहेगा।",
            "यदि आप अपने कार्यक्षेत्र और घरेलू जीवन के बीच संतुलन बनाए रखें और घर के माहौल को हल्का-फुल्का व प्रसन्नचित्त रखें, तो आपका पारिवारिक जीवन अत्यंत सुखद रहेगा। घर के ईशान कोण (North-East) को स्वच्छ और पवित्र रखना आपकी मानसिक शांति को बढ़ाएगा।"
        ]),
        ("अध्याय 6 — पंचम भाव (विद्या, बुद्धि एवं संतान भाव): बौद्धिक क्षमता", [
            f"पंचम भाव पूर्व जन्म के पुण्यों, आपकी स्वाभाविक बुद्धि, विद्या, प्रेम संबंधों और संतान सुख का मुख्य केंद्र है। आपकी कुंडली में देवगुरु बृहस्पति {planets.get('Jupiter', {}).get('d1_sign')} राशि (भाव {planets.get('Jupiter', {}).get('d1_house')}) में और बुध {planets.get('Mercury', {}).get('d1_sign')} राशि (भाव {planets.get('Mercury', {}).get('d1_house')}) में स्थित होकर आपकी बौद्धिक क्षमता को अत्यंत प्रखर बनाते हैं।",
            "यह शुभ ग्रह स्थिति आपको जन्मजात रूप से मेधावी, विवेकशील और दूरदर्शी बनाती है। आपकी सीखने की क्षमता बहुत तीव्र है और आप पारंपरिक शिक्षा के साथ-साथ व्यावहारिक एवं गूढ़ विषयों में भी गहरी पकड़ रखते हैं। लोग आपकी सलाह को बहुत गंभीरता से लेते हैं।",
            "संतान सुख के मामले में भी आपकी कुंडली अत्यंत शुभ फलदायी है। आपकी संतान संस्कारी, मेधावी और जीवन में आपके मान-सम्मान को बढ़ाने वाली होगी। संतान से जुड़े शुभ समाचार और उनकी प्रगति आपके जीवन में प्रसन्नता और भाग्योदय का कारक बनेगी।",
            "आपकी रचनात्मकता (Creativity) और समस्या-समाधान की क्षमता उत्कृष्ट है। यदि आप शिक्षा, परामर्श, वित्त, प्रबंधन या बौद्धिक निर्णय लेने वाले किसी भी क्षेत्र में कार्य करते हैं, तो पंचम भाव की यह ऊर्जा आपको सदैव अग्रणी रखेगी।"
        ]),
        ("अध्याय 7 — षष्ठ भाव (रोग, ऋण एवं शत्रु भाव): संघर्ष और विजय", [
            f"षष्ठ भाव जीवन की दैनिक चुनौतियों, रोग, ऋण, प्रतिस्पर्धा और शत्रुओं का परिचायक है। आपकी कुंडली में मंगल देव {planets.get('Mars', {}).get('d1_sign')} राशि (भाव {planets.get('Mars', {}).get('d1_house')}) में {planets.get('Mars', {}).get('degree_within_sign')}° पर स्थित हैं, जो आपको एक जुझारू और अपराजेय व्यक्तित्व प्रदान करते हैं।",
            "यह स्थिति आपको 'शत्रुहंता' शक्ति प्रदान करती है। जीवन में चाहे कितनी भी बड़ी प्रतियोगिता या बाधा क्यों न आए, आप उससे घबराते नहीं बल्कि डटकर मुकाबला करते हैं। आपके विरोधी या प्रतिस्पर्धी आपके सामने लंबे समय तक टिक नहीं पाते।",
            "स्वास्थ्य की दृष्टि से आपकी रोग प्रतिरोधक क्षमता मजबूत है, किंतु कार्य के अत्यधिक दबाव के कारण पित्त, एसिडिटी, रक्तचाप या मांसपेशियों में खिंचाव जैसी सामयिक समस्याओं से सावधान रहना चाहिए। नियमित व्यायाम और पर्याप्त जल का सेवन आपके लिए आवश्यक है।",
            "नौकरी और करियर के क्षेत्र में यह भाव आपको कड़ी मेहनत करने वाला और कॉरपोरेट या प्रशासनिक ढांचे में प्रतिस्पर्धियों को पछाड़कर आगे बढ़ने वाला बनाता है। अनावश्यक ऋण (Loans) के लेन-देन से बचना आपके आर्थिक स्वास्थ्य के लिए सर्वोत्तम रहेगा।"
        ]),
        ("अध्याय 8 — सप्तम भाव (विवाह एवं साझेदारी भाव): वैवाहिक सुख", [
            f"सप्तम भाव जीवनसाथी, वैवाहिक सुख, व्यापारिक साझेदारी और समाज में आपकी सार्वजनिक छवि को दर्शाता है। आपकी कुंडली में चंद्रमा भाव {planets.get('Moon', {}).get('d1_house')} ({planets.get('Moon', {}).get('d1_sign')}) में और शुक्र भाव {planets.get('Venus', {}).get('d1_house')} ({planets.get('Venus', {}).get('d1_sign')}) में स्थित होकर आपके संबंधों को गहरा भावनात्मक आधार देते हैं।",
            "इस ग्रह स्थिति के प्रभाव से जीवनसाथी आकर्षक, समझदार, परिवार की देखभाल करने वाला और कलात्मक अभिरुचि वाला प्राप्त होता है। विवाह के पश्चात आपके भाग्य और आर्थिक स्थिरता में विशेष उन्नति होने के स्पष्ट योग निर्मित हो रहे हैं।",
            "आप विवाह और साझेदारी में भावनात्मक निष्ठा और पारदर्शिता को सर्वोपरि रखते हैं। हालांकि, कभी-कभी वैचारिक मतभेद या अति-अपेक्षाओं के कारण संबंधों में थोड़ी संवेदनशीलता आ सकती है, जिसे आपसी संवाद और सम्मान से आसानी से साधा जा सकता है।",
            "व्यापारिक साझेदारी और सार्वजनिक जीवन के लिए यह भाव शुभ है। समाज में आपकी छवि एक भरोसेमंद, गरिमापूर्ण और सहयोगी व्यक्ति के रूप में बनी रहेगी।"
        ]),
        ("अध्याय 9 — अष्टम भाव (आयु, रहस्य एवं परिवर्तन): जीवन के रूपांतरण", [
            "अष्टम भाव जीवन के गहरे रहस्यों, दीर्घायु, आकस्मिक घटनाओं, पैतृक संपत्ति और जीवन के बड़े रूपांतरण (Transformations) को दर्शाता है। आपकी कुंडली में अष्टम और दशम का संबंध आपके व्यक्तित्व में गहरी शोध प्रवृत्ति और अंतर्ज्ञान (Intuition) पैदा करता है।",
            "यह ग्रह स्थिति दर्शाती है कि आप किसी भी विषय की सतह से नीचे जाकर उसकी वास्तविकता को समझने में सक्षम हैं। डेटा विश्लेषण, रिसर्च, गुप्त विद्याओं (ज्योतिष/अध्यात्म), वित्त या गूढ़ प्रबंधन के क्षेत्र में आपकी पकड़ अत्यंत मजबूत हो सकती है।",
            "आयु और जीवन शक्ति के दृष्टिकोण से लग्नेश और बृहस्पति की शुभ स्थिति आपको दीर्घायु और संकटों से सुरक्षित बाहर निकलने की दैवीय कृपा प्रदान करती है। ससुराल पक्ष के साथ आपके संबंध तार्किक और सम्मानजनक बने रहेंगे।",
            "अष्टम भाव आकस्मिक लाभ और जीवन के बड़े बदलावों का भी कारक है। जीवन में जब भी कोई बड़ा परिवर्तन आएगा, वह अंततः आपके व्यक्तित्व को और अधिक मजबूत तथा आर्थिक रूप से परिपक्व बनाकर ही जाएगा।"
        ]),
        ("अध्याय 10 — नवम भाव (भाग्य एवं धर्म भाव): सबसे शक्तिशाली भाव", [
            f"नवम भाव धर्म, भाग्य, पिता, गुरु और उच्च आध्यात्मिक कृपा का स्थान है। आपकी कुंडली में सूर्य ({planets.get('Sun', {}).get('d1_sign')}), गुरु ({planets.get('Jupiter', {}).get('d1_sign')}) और शुक्र ({planets.get('Venus', {}).get('d1_sign')}) की स्थिति आपके भाग्य भाव को असाधारण रूप से जागृत कर रही है।",
            "देवगुरु बृहस्पति की शुभ ऊर्जा आपको उच्च कोटि का दार्शनिक दृष्टिकोण, ईश्वरीय सुरक्षा और समाज में एक मार्गदर्शक (Mentor) की प्रतिष्ठा प्रदान करती है। आप स्वभाव से न्यायप्रिय और अपने सिद्धांतों पर अडिग रहने वाले व्यक्ति हैं।",
            "सूर्य का प्रभाव यह सुनिश्चित करता है कि आपके कर्मों को भाग्य का पूरा साथ मिलेगा। यद्यपि पितृ दोष की जांच में जो सूक्ष्म संकेत मिलते हैं, उनके कारण कभी-कभी कार्यों के अंतिम चरण में थोड़ा विलंब हो सकता है, किंतु अंततः विजय आपकी ही होती है।",
            "जब भी आप किसी बड़े संकट में होंगे, कोई न कोई दैवीय सहायता या वरिष्ठजनों का आशीर्वाद आपको उबार लेगा। जन्म स्थान से दूर जाकर या लंबी यात्राओं के माध्यम से भाग्योदय होने के अत्यंत प्रबल योग हैं।"
        ]),
        ("अध्याय 11 — दशम भाव (कर्म एवं करियर भाव): आजीविका और प्रतिष्ठा", [
            f"दशम भाव आपके कर्म क्षेत्र, करियर, मान-सम्मान, अधिकार और सामाजिक प्रतिष्ठा को दर्शाता है। आपकी कुंडली में बुध {planets.get('Mercury', {}).get('d1_sign')} राशि (भाव {planets.get('Mercury', {}).get('d1_house')}) में और सूर्य भाव {planets.get('Sun', {}).get('d1_house')} में स्थित होकर 'धर्म-कर्माधिपति' एवं बौद्धिक नेतृत्व का योग बनाते हैं।",
            "बुध और सूर्य का यह प्रभाव दर्शाता है कि आपका करियर बुद्धिमत्ता, प्रबंधन (Management), संचार, प्रशासन, व्यापार या सलाहकार के क्षेत्र में अत्यंत सफल हो सकता है। आप अपनी तार्किक क्षमता से कार्यस्थल की जटिल समस्याओं को सुलझाने में माहिर हैं।",
            "आपका कर्म सीधा आपके भाग्य और आपकी ईमानदारी से जुड़ा है। आप किसी के अधीन रहकर दबाव में काम करने की बजाय स्वतंत्र निर्णय लेने या नेतृत्व करने (Leadership role) में अपना सर्वश्रेष्ठ प्रदर्शन करते हैं।",
            "कुल मिलाकर, आपका कार्यक्षेत्र अत्यंत प्रतिष्ठित रहेगा। यदि आप स्वयं का व्यवसाय या स्वतंत्र प्रोफेशन भी चुनते हैं, तो उसे एक बड़े ब्रांड के रूप में स्थापित करने की पूर्ण क्षमता आपकी कुंडली में विद्यमान है।"
        ]),
        (f"अध्याय 12 — एकादश भाव (लाभ एवं इच्छापूर्ति): इन्दु लग्न ({indu.get('indu_lagna_sign')}) का प्रभाव", [
            f"एकादश भाव जीवन में प्राप्त होने वाले लाभ, आय के स्थायी स्रोतों और मनोकामनाओं की पूर्ति का भाव है। आपकी कुंडली में **इन्दु लग्न (धन का विशेष लग्न)** {indu.get('indu_lagna_sign')} राशि में लग्न से भाव {indu.get('house_from_d1_lagna')} में स्थित है, जिसके स्वामी {indu.get('indu_lagna_lord')} हैं।",
            f"इन्दु लग्न और इसके स्वामी {indu.get('indu_lagna_lord')} की मजबूत स्थिति यह सुनिश्चित करती है कि जीवन में धन के आगमन में कभी कोई स्थायी रुकावट नहीं आएगी। आप अपनी बुद्धि और व्यावसायिक कौशल से एक से अधिक आय के स्रोत (Multiple sources of income) उत्पन्न करने में सक्षम होंगे।",
            "आपका सामाजिक और व्यावसायिक नेटवर्क (Networking) आपके करियर को आगे बढ़ाने और बड़े आर्थिक लाभ कराने में महत्वपूर्ण भूमिका निभाएगा। आपकी महत्वाकांक्षाएं उच्च हैं और उन्हें पूरा करने का सामर्थ्य आपके भीतर मौजूद है।",
            "लाभ प्राप्त करने के लिए आपका दृष्टिकोण बहुत व्यावहारिक और गणनात्मक (Calculative) रहता है। उम्र के 32वें और 36वें वर्ष के पश्चात आपकी आय और कुल संपत्ति (Net Worth) में तेज़ उछाल आने के सुनिश्चित योग हैं।"
        ]),
        ("अध्याय 13 — द्वादश भाव (व्यय, विदेश एवं मोक्ष भाव): विदेश और शय्या सुख", [
            "द्वादश भाव खर्चों, निवेश, विदेश यात्रा, एकांत सुख और आध्यात्मिक मुक्ति का कारक है। आपकी कुंडली में शुक्र और गुरु का प्रभाव आपके खर्चों को व्यर्थ नहीं जाने देता, बल्कि उन्हें शुभ कार्यों, जीवनस्तर (Lifestyle) के उन्नयन और निवेश में परिवर्तित करता है।",
            "आप अपने रहन-सहन, परिवार की सुख-सुविधाओं और यात्राओं पर उदारतापूर्वक धन व्यय करना पसंद करते हैं। विदेश यात्रा, मल्टीनेशनल कंपनियों से जुड़ाव या जन्म स्थान से दूर से धन लाभ कमाने के लिए यह ग्रह स्थिति अत्यंत अनुकूल है।",
            "नींद और मानसिक विश्राम के मामले में, कभी-कभी विचारों की अधिकता (Overthinking) के कारण रात्रि में देर तक जागने की आदत हो सकती है। सोने से पूर्व ध्यान या शांत संगीत सुनना आपके लिए अत्यंत लाभकारी रहेगा।",
            "आध्यात्मिक दृष्टिकोण से, जीवन के उत्तरार्ध में आप समाज-सेवा, धर्म-कर्म और आध्यात्मिक उत्थान के कार्यों में विशेष रुचि लेंगे। आपका शुभ व्यय आपके पुण्य और भाग्य को और अधिक चमकाने का कार्य करेगा।"
        ]),
        ("अध्याय 14 — प्रथम प्रमुख सकारात्मक राजयोग: गुरु-चंद्र एवं केंद्र-त्रिकोण राजयोग", [
            f"आपकी जन्म कुंडली का सबसे चमत्कारी और सकारात्मक योग देवगुरु बृहस्पति ({planets.get('Jupiter', {}).get('d1_sign')}, भाव {planets.get('Jupiter', {}).get('d1_house')}) और चंद्रमा ({planets.get('Moon', {}).get('d1_sign')}, भाव {planets.get('Moon', {}).get('d1_house')}) के शुभ प्रभाव से निर्मित हो रहा है। यह स्थिति कुंडली के अनेक दोषों का स्वतः शमन करने वाली मानी जाती है।",
            "जब कुंडली में गुरु और चंद्रमा बलवान होते हैं, तो यह 'गजकेसरी प्रभाव' और दैवीय सुरक्षा कवच का निर्माण करते हैं। यह योग आपके जीवन में मान-सम्मान, अटूट धन और समाज में एक अत्यंत प्रतिष्ठित स्थान की गारंटी देता है।",
            "इस योग के व्यावहारिक लाभ स्वरूप आप विषम से विषम परिस्थितियों से भी सुरक्षित बाहर निकल आते हैं। आपके भीतर ज्ञान, करुणा और सही समय पर सही निर्णय लेने का अद्भुत विवेक विद्यमान है।",
            "इस राजयोग की शक्ति को पूर्ण रूप से जाग्रत रखने के लिए सदैव अपने गुरुओं और वरिष्ठजनों का सम्मान करें। गुरुवार के दिन पीले चंदन या केसर का तिलक लगाना इस योग के शुभ फलों को कई गुना बढ़ा देगा।"
        ]),
        ("अध्याय 15 — द्वितीय प्रमुख सकारात्मक योग: पराक्रम एवं उपचय राहु-मंगल बल", [
            f"वैदिक ज्योतिष के अनुसार कुंडली में राहु ({planets.get('Rahu', {}).get('d1_sign')}, भाव {planets.get('Rahu', {}).get('d1_house')}) और मंगल ({planets.get('Mars', {}).get('d1_sign')}, भाव {planets.get('Mars', {}).get('d1_house')}) की सशक्त स्थिति जातक को असाधारण कर्मठता और कलियुग में तेजी से सफलता पाने की शक्ति देती है।",
            "यह योग आपको निडरता और हर कठिन परिस्थिति से निपटने की व्यावहारिक चतुराई (Street-smartness) देता है। आप पुरानी रूढ़ियों से हटकर अपने लिए एक नया और आधुनिक रास्ता बनाने में विश्वास रखते हैं।",
            "पेशेवर जीवन में यह योग आपको तकनीक, प्रबंधन, व्यापार और उच्च प्रतिस्पर्धा वाले क्षेत्रों में जबरदस्त सफलता दिलाता है। आप सही समय पर जोखिम लेने से नहीं डरते और यही गुण आपको भीड़ से अलग खड़ा करता है।",
            "इस योग का भरपूर लाभ उठाने के लिए अपनी ऊर्जा को एक स्पष्ट लक्ष्य (Single-minded Focus) पर केंद्रित रखें। जब आपका फोकस अडिग रहता है, तो यह योग आपको अपार धन और प्रसिद्धि दिलाता है।"
        ]),
        ("अध्याय 16 — तृतीय प्रमुख योग: हर्ष विपरीत राजयोग एवं शत्रुहंता प्रभाव", [
            "आपकी कुंडली में संघर्षों को ही सफलता की सीढ़ी बनाने वाला विशेष 'विपरीत राजयोग' एवं 'शत्रुहंता प्रभाव' सक्रिय है। यह योग दर्शाता है कि आपके जीवन में आने वाली हर चुनौती आपको पहले से अधिक शक्तिशाली बनाकर जाती है।",
            "इस योग की सबसे बड़ी विशेषता यह है कि जब परिस्थितियां कठिन लगती हैं, तब आपकी आंतरिक शक्ति जागृत होती है और आप बाजी अपने पक्ष में पलट देते हैं। आपके विरोधी भी अंततः आपकी कार्यक्षमता का लोहा मानते हैं।",
            "प्रतियोगी परीक्षाओं, कानूनी मामलों, प्रशासनिक जिम्मेदारियों और संकट प्रबंधन (Crisis Management) में यह योग आपको सदैव विजयी बनाता है। आपके भीतर गजब की सहनशक्ति (Stamina) मौजूद है।",
            "इस योग के पूर्ण फल की प्राप्ति के लिए संघर्ष से कभी पीछे न हटें। श्री हनुमान जी की आराधना करने से आपकी यह ऊर्जा सदैव सकारात्मक और रचनात्मक बनी रहेगी।"
        ]),
        ("अध्याय 17 — चतुर्थ प्रमुख योग: धर्म-कर्माधिपति एवं बुधादित्य प्रभाव", [
            f"आपकी कुंडली में सूर्य (भाव {planets.get('Sun', {}).get('d1_house')}) और बुध (भाव {planets.get('Mercury', {}).get('d1_house')}) की स्थिति भाग्य और कर्म के बीच एक अत्यंत शुभ सेतु का निर्माण करती है, जिसे ज्योतिष में 'धर्म-कर्माधिपति' एवं बौद्धिक राजयोग की श्रेणी में रखा जाता है।",
            "इस योग के परिणामस्वरूप आपका करियर और आपकी प्रतिष्ठा सीधे आपके नैतिक मूल्यों और बौद्धिक कौशल से संचालित होती है। आपको उच्च अधिकारियों, सरकारी तंत्र या बड़े संगठनों से विशेष सहयोग और सम्मान प्राप्त होने के योग हैं।",
            "यह स्थिति आपको एक उत्कृष्ट प्रशासक और रणनीतिकार बनाती है। आप जहां भी कार्य करेंगे, वहां अपनी कार्यशैली की एक अमिट छाप छोड़ेंगे। जीवन में सही समय पर भाग्यशाली अवसर स्वयं आपके द्वार पर दस्तक देंगे।",
            "इस राजयोग को और अधिक बलवान करने के लिए पिता का सम्मान करें और प्रतिदिन प्रातःकाल सूर्य देव को जल अर्पित करें। यह योग आपको समाज के शीर्ष वर्ग में स्थापित करने की क्षमता रखता है।"
        ]),
        (f"अध्याय 18 — पंचम प्रमुख योग: इन्दु लग्न ({indu.get('indu_lagna_sign')}) द्वारा निर्मित महा-धन योग", [
            f"महर्षि पाराशर द्वारा प्रतिपादित इन्दु लग्न आपकी कुंडली में {indu.get('indu_lagna_sign')} राशि (भाव {indu.get('house_from_d1_lagna')}) में निर्मित हो रहा है, जिसके स्वामी {indu.get('indu_lagna_lord')} हैं। यह स्थिति आर्थिक समृद्धि के लिए एक विशेष 'महा-धन योग' का निर्माण करती है।",
            f"इन्दु लग्न के स्वामी {indu.get('indu_lagna_lord')} की स्थिति स्पष्ट करती है कि आपके धन का मुख्य स्रोत आपकी अपनी बौद्धिक क्षमता, व्यावसायिक दूरदर्शिता और उच्च स्तरीय प्रबंधन होगा। आप अपने प्रयासों से अपनी आय को कई गुना (Multiply) करने में सफल रहेंगे।",
            "यह योग जीवन के मध्य भाग में स्थायी संपत्ति, भूमि, वाहन और दीर्घकालिक निवेश से बड़े आर्थिक लाभ सुनिश्चित करता है। आपकी आर्थिक निर्णय क्षमता समय के साथ अत्यंत परिपक्व होती जाएगी।",
            "इस महा-धन योग की पूर्ण सक्रियता के लिए अपनी वित्तीय योजनाओं को गोपनीय रखें और अनुशासित निवेश की आदत बनाए रखें। आप अपने पुरुषार्थ से एक सुदृढ़ आर्थिक साम्राज्य खड़ा करेंगे।"
        ]),
        ("अध्याय 19 — प्रथम प्रमुख जीवन चुनौती: पितृ/ग्रहण प्रभाव का प्रबंधन", [
            f"आपकी कुंडली की दोष जांच के अनुसार: {doshas.get('pitra_dosh', {}).get('details')}। जहाँ कुंडली में बड़े राजयोग हैं, वहीं इस सूक्ष्म प्रभाव के कारण कभी-कभी बनते हुए कार्यों में अंतिम समय पर अनावश्यक विलंब का अनुभव हो सकता है।",
            "इस प्रभाव के कारण कई बार आपको ऐसा लग सकता है कि आप मेहनत 100% कर रहे हैं, किंतु उसका श्रेय या परिणाम मिलने में अपेक्षा से अधिक समय लग रहा है। वरिष्ठजनों या पिता तुल्य व्यक्तियों के साथ कभी-कभी वैचारिक मतभेद उभर सकते हैं।",
            "यह स्थिति कभी-कभी आत्म-संदेह (Self-doubt) या मानसिक थकान भी दे सकती है, विशेषकर तब जब आपके आस-पास के लोग आपकी दूरदर्शिता को तुरंत न समझ पाएं।",
            "इस चुनौती से पार पाने के लिए अमावस्या के दिन पूर्वजों के निमित्त दान-पुण्य करें और किसी भी बड़े कार्य की शुरुआत में घर के बड़ों का आशीर्वाद अवश्य लें। धैर्य और सात्विकता से यह दोष पूरी तरह शांत रहता है।"
        ]),
        ("अध्याय 20 — द्वितीय प्रमुख चुनौती: धन संचय और स्पष्ट वाणी का संतुलन", [
            f"शनि देव आपकी कुंडली के भाव {planets.get('Saturn', {}).get('d1_house')} ({planets.get('Saturn', {}).get('d1_sign')}) में स्थित हैं। यद्यपि शनि दीर्घकाल में अत्यंत स्थायी संपत्ति देते हैं, किंतु प्रारंभिक वर्षों में नकद धन प्रवाह (Cash Flow) में कुछ उतार-चढ़ाव या पारिवारिक जिम्मेदारियों पर अचानक खर्च ला सकते हैं।",
            "शनि अनुशासन और धैर्य के कारक हैं, इसलिए रातों-रात अमीर बनने वाली योजनाओं या बिना सोचे-समझे किए गए जोखिम भरे निवेश से आपको सदैव बचना चाहिए। आपकी सफलता क्रमिक और ठोस कदमों से ही आएगी।",
            "इसके अतिरिक्त, आपकी स्पष्टवादी और सीधी वाणी कई बार उन लोगों को आहत कर सकती है जो चापलूसी पसंद करते हैं। कार्यस्थल और परिवार में कभी-कभी केवल शब्दों के चयन के कारण तनाव उत्पन्न हो सकता है।",
            "समाधान के रूप में, अपनी वाणी में कूटनीति और मधुरता का समावेश करें तथा अपनी आय का एक निश्चित हिस्सा सुरक्षित दीर्घकालिक फंड्स या अचल संपत्ति में नियमित रूप से निवेश करें।"
        ]),
        ("अध्याय 21 — तृतीय प्रमुख चुनौती: भावनात्मक संतुलन एवं संबंधों में सामंजस्य", [
            "आपकी कुंडली में शुक्र और केतु/राहु के अक्ष का प्रभाव कभी-कभी संबंधों और भौतिक सुखों के प्रति एक आंतरिक द्वंद्व (Inner Conflict) या अचानक वैराग्य की भावना उत्पन्न कर सकता है।",
            "आप अपने करीबी रिश्तों और जीवनसाथी से पूर्णता (Perfection) और गहरी निष्ठा की अपेक्षा रखते हैं। जब सामने वाला व्यक्ति आपकी उच्च अपेक्षाओं पर खरा नहीं उतर पाता, तो आपका मन जल्दी आहत या उदासीन हो जाता है।",
            "इसी प्रकार किसी भौतिक वस्तु या लक्ष्य को पाने से पहले आपके भीतर जितनी तीव्र इच्छा होती है, उसे पा लेने के बाद कई बार उससे जल्दी ही मन भर जाने की स्थिति बन सकती है।",
            "इस स्थिति को साधने का सर्वोत्तम सूत्र यह है कि रिश्तों में यथार्थवादी अपेक्षाएं रखें और अपने जीवनसाथी व परिवार के सदस्यों को उनकी स्वाभाविक कमियों सहित प्रेमपूर्वक स्वीकार करें।"
        ]),
        ("अध्याय 22 — चतुर्थ प्रमुख चुनौती: गोचर प्रभाव एवं ओवरथिंकिंग पर नियंत्रण", [
            f"साढ़े साती एवं गोचर जांच के अनुसार: {doshas.get('sade_sati', {}).get('details')}। चंद्रमा और लग्न के संवेदनशील संबंध के कारण आप किसी भी विषय पर बहुत गहराई से सोचते हैं, जो कई बार ओवरथिंकिंग (Overthinking) का रूप ले लेता है।",
            "जब कोई कार्य आपकी योजना के अनुसार नहीं होता, तो आपका मस्तिष्क एक साथ कई वैकल्पिक चिंताएं बुनने लगता है। इससे मानसिक ऊर्जा का ह्रास होता है और रात्रि की निद्रा प्रभावित हो सकती है।",
            "अत्यधिक मानसिक सक्रियता के कारण कभी-कभी निर्णय लेने में दुविधा (Analysis Paralysis) की स्थिति भी बन सकती है, जहाँ आप सही अवसर का इंतजार करते रह जाते हैं।",
            "इससे बचने का अचूक उपाय है—वर्तमान क्षण में जीना (Mindfulness) और सोमवार के दिन भगवान शिव की आराधना करना। याद रखें कि आपकी 90% काल्पनिक चिंताएं वास्तविकता में कभी घटित नहीं होतीं।"
        ]),
        ("अध्याय 23 — पंचम प्रमुख चुनौती: दशा संधि और ऊर्जा का सही प्रबंधन", [
            f"वर्तमान में आप {active_h.get('mahadasha', {}).get('lord')} महादशा के अंतर्गत {active_h.get('antardasha', {}).get('lord')} की अंतर्दशा से गुजर रहे हैं। जब दो भिन्न स्वभाव वाले ग्रहों की दशा-अंतर्दशा एक साथ चलती है, तो जीवन की प्राथमिकताओं को लेकर द्वंद्व उत्पन्न होना स्वाभाविक है।",
            "एक ओर आपका मन उच्च आदर्शों, ज्ञान और शांति की ओर आकर्षित होता है, तो दूसरी ओर सांसारिक विस्तार, करियर की महत्वाकांक्षा और भौतिक जिम्मेदारियां आपको निरंतर दौड़ने के लिए प्रेरित करती हैं।",
            "अत्यधिक ऊर्जा होने के कारण आप कई बार एक साथ बहुत से काम (Multi-tasking) अपने हाथ में ले लेते हैं, जिससे शारीरिक और मानसिक थकान (Burnout) महसूस हो सकती है।",
            "इस कालखंड में अपनी प्राथमिकताओं को स्पष्ट रखें। एक समय में एक ही बड़े लक्ष्य पर पूरी ऊर्जा लगाएं और अपनी दिनचर्या को अनुशासित रखें।"
        ]),
        (f"अध्याय 24 — वर्तमान महादशा ({curr_md.get('lord')}) का गहन काल-विश्लेषण ({curr_md.get('start_date')} से {curr_md.get('end_date')})", [
            f"आप वर्तमान में {curr_md.get('lord')} की महादशा से गुजर रहे हैं, जो {curr_md.get('start_date')} को आरंभ हुई थी और {curr_md.get('end_date')} तक सक्रिय रहेगी। इससे पूर्व आपने {prev_md.get('lord')} की महादशा ({prev_md.get('start_date')} से {prev_md.get('end_date')}) के अनुभवों से जीवन की गहरी सीख प्राप्त की है।",
            f"आपकी कुंडली में वर्तमान महादशा स्वामी {curr_md.get('lord')} की स्थिति अत्यंत महत्वपूर्ण है। यह महादशा आपके जीवन में ज्ञान, भाग्य के विस्तार, सामाजिक प्रतिष्ठा और स्थायी निर्णय लेने का स्वर्णिम कालखंड है।",
            "इस महादशा का मुख्य उद्देश्य आपको आर्थिक और बौद्धिक रूप से परिपक्व बनाना है। पूर्व के संघर्षों की तुलना में यह दशा आपको एक स्पष्ट जीवन-दिशा, वरिष्ठ लोगों का सहयोग और पारिवारिक उन्नति प्रदान करने के लिए प्रतिबद्ध है।",
            f"{curr_md.get('end_date')} तक चलने वाली यह महादशा आपके जीवन की सबसे मजबूत नींव रखेगी, जिसके आधार पर आगामी {next_md.get('lord')} महादशा में आप अपने संचित अनुभवों का दीर्घकालिक फल प्राप्त करेंगे।"
        ]),
        (f"अध्याय 25 — वर्तमान सक्रिय अंतर्दशा ({active_h.get('antardasha', {}).get('lord')}) एवं प्रत्यंतर ({active_h.get('pratyantardasha', {}).get('lord')}) का भविष्यफल", [
            f"वर्तमान में {active_h.get('mahadasha', {}).get('lord')} महादशा के अंतर्गत {active_h.get('antardasha', {}).get('lord')} की अंतर्दशा ({active_h.get('antardasha', {}).get('start_date')} से {active_h.get('antardasha', {}).get('end_date')} तक) सक्रिय है। यह कालखंड आपके संबंधों, सुख-सुविधाओं, करियर विस्तार और आर्थिक निर्णयों के लिए अत्यंत संवेदनशील व महत्वपूर्ण है।",
            f"इस अंतर्दशा में आपके जीवनस्तर के उन्नयन, वाहन/संपत्ति या मांगलिक कार्यों पर शुभ व्यय के योग बन रहे हैं। साथ ही {active_h.get('pratyantardasha', {}).get('lord')} की प्रत्यंतर दशा ({active_h.get('pratyantardasha', {}).get('start_date')} से {active_h.get('pratyantardasha', {}).get('end_date')}) आपको अपने कार्यक्षेत्र में ठोस और व्यावहारिक परिणाम दिलाने का कार्य कर रही है।",
            f"सूक्ष्म स्तर पर {active_h.get('sookshma_dasha', {}).get('lord')} की सूक्ष्म दशा ({active_h.get('sookshma_dasha', {}).get('start_date')} से {active_h.get('sookshma_dasha', {}).get('end_date')}) बौद्धिक संवाद और नए व्यावसायिक विचारों को गति दे रही है। रुका हुआ धन या अटका हुआ कार्य इस अवधि में प्रयास करने से सुलझ सकता है।",
            "आगामी अंतर्दशाओं में सूर्य और चंद्रमा का क्रम आपके करियर में पदोन्नति, सत्ता पक्ष से लाभ और समाज में नई पहचान दिलाने वाला सिद्ध होगा। वर्तमान समय में धैर्य और योजनाबद्ध तरीके से आगे बढ़ें।"
        ]),
        ("अध्याय 26 — जीवन बदलने वाले 4 अचूक और व्यावहारिक वैदिक उपाय", [
            f"प्रिय {name} जी, वैदिक ज्योतिष में रत्नों से कहीं अधिक शक्ति सात्विक कर्म, मंत्र और अनुशासन में होती है। आपकी कुंडली के सूक्ष्म विश्लेषण के आधार पर बिना किसी रत्न (Gemstone) के 4 अत्यंत प्रभावशाली वैदिक उपाय नीचे दिए जा रहे हैं:",
            "1. सूर्य अर्घ्य एवं गुरु उपासना (भाग्य व करियर वृद्धि हेतु): प्रतिदिन प्रातःकाल तांबे के पात्र में जल, रोली और अक्षत डालकर उगते हुए सूर्य को अर्घ्य दें तथा 'ॐ घृणि सूर्याय नमः' का 108 बार जाप करें। प्रत्येक गुरुवार को मस्तक पर केसर या हल्दी का तिलक लगाएं और श्री विष्णु सहस्रनाम का पाठ करें।",
            "2. शनि एवं कर्म अनुशासन (स्थायी धन संचय हेतु): अपने अधीन कार्य करने वाले कर्मचारियों, श्रमिकों और असहाय व्यक्तियों का सदैव सम्मान करें। प्रत्येक शनिवार को संध्या काल में पीपल के वृक्ष के नीचे सरसों के तेल का दीपक जलाएं और अपनी वाणी में सदैव मधुरता व संयम बनाए रखें।",
            "3. शिव आराधना एवं ध्यान (मानसिक शांति हेतु): ओवरथिंकिंग और मानसिक तनाव को दूर करने के लिए प्रत्येक सोमवार को शिवलिंग पर कच्चा दूध मिश्रित जल अर्पित करें तथा 'ॐ नमः शिवाय' का 108 बार मानसिक जाप करें। प्रतिदिन रात्रि में सोने से पूर्व 10 मिनट का मौन ध्यान आपकी निर्णय क्षमता को अद्भुत रूप से निखारेगा।"
        ]),
        ("अध्याय 27 — मास्टर रिपोर्ट का अंतिम निचोड़ और आगामी 5 वर्षों का रोडमैप", [
            f"5 सबसे बड़ी ताकतें: (1) {lagna.get('d1_sign')} लग्न और लग्नेश {lagna.get('d1_lord')} का अदम्य आत्मबल, (2) भाग्य व केंद्र भावों में शुभ ग्रहों का सुरक्षा कवच, (3) चंद्रमा-गुरु का उच्च बौद्धिक व भावनात्मक संतुलन, (4) उपचय भावों की संघर्ष-विजय क्षमता, और (5) {indu.get('indu_lagna_sign')} इन्दु लग्न (भाव {indu.get('house_from_d1_lagna')}) का महा-धन योग।",
            "5 मुख्य सावधानियां: (1) क्रोध और जल्दबाजी में कोई भी बड़ा निर्णय लेने से बचें, (2) अपनी स्पष्ट वाणी को कटु न बनने दें, (3) ओवरथिंकिंग और काल्पनिक चिंताओं को अपनी नींद व शांति पर हावी न होने दें, (4) पिता व वरिष्ठजनों के साथ वैचारिक मतभेद से बचें, और (5) जोखिम भरे शॉर्टकट निवेश से दूर रहें।",
            f"आगामी 5 वर्षों का स्वर्णिम रोडमैप (2026-2031): वर्तमान {active_h.get('mahadasha', {}).get('lord')}-{active_h.get('antardasha', {}).get('lord')} कालखंड आपको संपत्ति निर्माण, पारिवारिक सुख और करियर की नई रूपरेखा देगा। इसके तुरंत बाद आने वाली आगामी अंतर्दशाएं आपके पेशेवर जीवन और आर्थिक उत्थान का सर्वोच्च शिखर (Peak Period) सिद्ध होंगी।",
            f"{name} जी, आपकी कुंडली एक अत्यंत सक्षम, स्वाभिमानी और दूरदर्शी व्यक्तित्व की कुंडली है। ब्रह्मांड की सकारात्मक ऊर्जा आपके साथ है। अपने लक्ष्यों के प्रति केंद्रित रहें, ईश्वर पर विश्वास रखें और कर्म पथ पर निरंतर आगे बढ़ते रहें। सफलता आपके कदम चूमेगी! (शुभम भवतु)"
        ])
    ]

    pages_html = ""
    for idx, (ch_title, paras) in enumerate(chapters_data, start=4):
        paras_html = "".join([f'<p class="book-para">{p}</p>' for p in paras])
        pages_html += f"""
        <div class="book-page dynamic-chapter-page">
            <div class="page-border">
                <div class="book-header">
                    <span>ASTROPULSE INDIA — CALL CONSULTATION & MASTER REPORT</span>
                    <span>ASTROPULSE INDIA</span>
                </div>
                <div class="chapter-banner">
                    <h2>{ch_title}</h2>
                </div>
                <div class="book-content">
                    {paras_html}
                </div>
                <div class="book-footer">
                    <span>{footer_user_info}</span>
                    <span class="page-num">Page {idx} of 30</span>
                </div>
            </div>
        </div>
        """

    full_book_html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>{report_title} - {name}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Devanagari:wght@400;600;700&display=swap');
        @page {{ size: A4 portrait; margin: 0; }}
        * {{ box-sizing: border-box; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        body {{ margin: 0; padding: 0; background-color: #111827; font-family: 'Noto Serif Devanagari', 'Segoe UI', serif; color: #111111; }}
        .top-action-bar {{ position: sticky; top: 0; z-index: 9999; background: #000000; color: #facc15; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #dc2626; flex-wrap: wrap; gap: 8px; }}
        .btn-download {{ background: #dc2626; color: #ffffff; border: 2px solid #facc15; padding: 7px 14px; font-size: 0.90rem; font-weight: bold; border-radius: 6px; cursor: pointer; margin-left: 4px; transition: 0.2s; }}
        .btn-download:hover {{ opacity: 0.92; transform: translateY(-1px); }}
        .btn-download:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        #book-container {{ width: 210mm; margin: 20px auto; }}
        .book-page {{ width: 210mm; height: 297mm; background: #ffffff; margin-bottom: 20px; padding: 8mm 10mm; page-break-after: always; break-after: page; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.5); overflow: hidden; display: flex; flex-direction: column; }}
        .book-page.pdf-exporting {{ margin: 0 !important; box-shadow: none !important; }}
        .cover-page {{ background: #0a0a0a; color: #ffffff; }}
        .page-border {{ border: 4px double #dc2626; outline: 2px solid #facc15; outline-offset: -6px; height: 100%; min-height: 0; padding: 8mm 10mm; display: flex; flex-direction: column; justify-content: space-between; position: relative; flex: 1 1 auto; overflow: hidden; }}
        .book-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #dc2626; padding-bottom: 4px; font-size: 0.82rem; color: #991b1b; font-weight: bold; flex: 0 0 auto; }}
        .book-footer {{ display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #111111; padding-top: 4px; font-size: 0.82rem; color: #111111; font-weight: bold; margin-top: auto; flex: 0 0 auto; background: inherit; position: relative; z-index: 2; }}
        .page-num {{ background: #111111; color: #facc15; padding: 2px 10px; border-radius: 4px; font-size: 0.80rem; }}
        .chapter-banner {{ background: #991b1b; color: #facc15; border-left: 8px solid #111111; padding: 6px 12px; margin: 5px 0; border-radius: 4px; flex: 0 0 auto; }}
        .chapter-banner h2 {{ margin: 0; font-size: 1.12rem; color: #facc15; line-height: 1.3; }}
        .book-content {{ flex: 1 1 auto; min-height: 0; text-align: justify; display: flex; flex-direction: column; justify-content: space-between; padding: 2px 0 6px 0; overflow: hidden; }}
        .book-para {{ font-size: 0.98rem; line-height: 1.65; margin: 0 0 8px 0; color: #111111; text-align: justify; text-justify: inter-word; }}
        .book-para:last-child {{ margin-bottom: 0 !important; }}
        table.astro-table {{ width: 100%; border-collapse: collapse; margin: 4px 0; font-size: 0.82rem; }}
        table.astro-table th {{ background: #111111; color: #facc15; border: 1px solid #dc2626; padding: 5px; }}
        table.astro-table td {{ border: 1px solid #374151; padding: 4px 5px; text-align: center; color: #111111; }}
        table.page3-table {{ width: 100%; border-collapse: collapse; margin: 3px 0; font-size: 0.82rem; }}
        table.page3-table th {{ background: #111111; color: #facc15; border: 1px solid #dc2626; padding: 4px 6px; }}
        table.page3-table td {{ border: 1px solid #374151; padding: 3.5px 6px; text-align: center; color: #111111; line-height: 1.25; }}
        .birth-card {{ background: #1f2937; border: 2px solid #facc15; border-radius: 8px; padding: 14px 16px; margin: 6px 0; color: #ffffff; }}
        .birth-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; font-size: 0.98rem; line-height: 1.4; }}
        .birth-grid span {{ color: #facc15; font-weight: bold; }}
        .charts-row {{ display: flex; justify-content: space-around; align-items: center; margin: 2px 0; }}
        .chart-item {{ text-align: center; }}
        .chart-item h4 {{ margin: 0 0 3px 0; color: #991b1b; font-size: 0.88rem; }}

        /* Modal Styles for Pasting Gemini .TXT / HTML Output */
        #gemini-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 10000; justify-content: center; align-items: center; padding: 20px; }}
        .modal-card {{ background: #1f2937; border: 3px solid #facc15; border-radius: 10px; width: 100%; max-width: 820px; padding: 20px; color: #ffffff; box-shadow: 0 15px 40px rgba(0,0,0,0.8); }}
        .modal-card h3 {{ margin: 0 0 10px 0; color: #facc15; font-size: 1.25rem; }}
        .modal-card textarea {{ width: 100%; height: 300px; background: #111827; color: #f9fafb; border: 1px solid #dc2626; border-radius: 6px; padding: 12px; font-size: 0.95rem; font-family: monospace; resize: vertical; }}
        .modal-actions {{ display: flex; justify-content: flex-end; gap: 10px; margin-top: 12px; }}

        @media print {{
            body {{ background: #ffffff; }}
            .top-action-bar, #gemini-modal {{ display: none !important; }}
            #book-container {{ width: 210mm; margin: 0; }}
            .book-page {{ margin: 0; box-shadow: none; page-break-after: always; break-after: page; }}
        }}
    </style>
</head>
<body>
    <div class="top-action-bar">
        <div><strong>📖 ASTROPULSE INDIA — {report_title} ({name})</strong></div>
        <div style="display:flex; flex-wrap:wrap; gap:4px;">
            <button class="btn-download" style="background:#2563eb;" onclick="downloadTxtPrompt()">📄 1. Download .TXT Prompt</button>
            <button class="btn-download" style="background:#7c3aed;" onclick="openGeminiModal()">📋 2. Paste Gemini (.TXT / HTML)</button>
            <button class="btn-download" style="background:#059669;" onclick="autoFitAllPages()">✨ Auto-Fit Pages</button>
            <button class="btn-download" onclick="window.print()">🖨️ Print PDF</button>
            <button id="btn-direct-pdf" class="btn-download" style="background:#facc15; color:#000;" onclick="downloadDirectPDF()">📥 Direct 1-Click PDF (No Glitch)</button>
        </div>
    </div>

    <!-- Gemini Paste Modal -->
    <div id="gemini-modal">
        <div class="modal-card">
            <h3>📋 जेमिनी का आउटपुट (.TXT या HTML) यहाँ पेस्ट करें (Page 1-3 सुरक्षित रहेंगे!)</h3>
            <p style="font-size:0.88rem; color:#d1d5db; margin:0 0 10px 0;">
                चाहे आपने जेमिनी से प्लेन टेक्स्ट (<code>==== PAGE BREAK ====</code> वाला) जनरेट करवाया हो या HTML कोड, उसे नीचे पेस्ट करें।
                सिस्टम <b>Page 1, Page 2 और Page 3 की टेबल्स को बिल्कुल नहीं छेड़ेगा</b> और बाकी अध्यायों को अपने आप पन्नों में सेट करके ऑटो-फिट कर देगा!
            </p>
            <textarea id="gemini-input-box" placeholder="यहाँ जेमिनी से कॉपी किया गया पूरा टेक्स्ट या HTML पेस्ट करें..."></textarea>
            <div class="modal-actions">
                <button class="btn-download" style="background:#4b5563;" onclick="closeGeminiModal()">रद्द करें (Cancel)</button>
                <button class="btn-download" style="background:#059669;" onclick="applyGeminiContent()">✅ टेम्पलेट में सेट करें (Build Book)</button>
            </div>
        </div>
    </div>

    <div id="book-container">
        <!-- ================= PAGE 1: ROYAL COVER PAGE (LOCKED) ================= -->
        <div class="book-page cover-page" id="locked-page-1">
            <div class="page-border" style="border-color: #facc15; outline-color: #dc2626;">
                <div style="text-align: center; margin-top: 2px;">
                    <div style="color: #facc15; font-size: 1.15rem; letter-spacing: 3px; font-weight: bold;">॥ श्री गणेशाय नमः ॥</div>
                    <h1 style="font-size: 2.6rem; color: #facc15; margin: 4px 0 6px 0; text-transform: uppercase; letter-spacing: 2px;">ASTROPULSE INDIA</h1>
                    <div style="background: #dc2626; color: #ffffff; display: inline-block; padding: 8px 26px; font-weight: bold; font-size: 1.35rem; border-radius: 6px; border: 2px solid #facc15;">
                        {report_title}
                    </div>
                </div>

                <div class="birth-card">
                    <h2 style="color: #facc15; border-bottom: 2px solid #dc2626; padding-bottom: 5px; margin: 0 0 8px 0; text-align: center; font-size: 1.2rem;">
                        जातक का प्रमाणित जन्म विवरण (Verified Birth Details)
                    </h2>
                    <div class="birth-grid">
                        <div>नाम (Name): <span>{name}</span></div>
                        <div>लिंग (Gender): <span>{gender}</span></div>
                        <div>जन्म तिथि (DOB): <span>{dob_str}</span></div>
                        <div>जन्म समय (Time): <span>{tob_str}</span></div>
                        <div>जन्म स्थान (Place): <span>{city}</span></div>
                        <div>लग्न (D1 Lagna): <span>{lagna.get('d1_sign')} ({lagna.get('degree_within_sign')}°)</span></div>
                        <div>नवमांश (D9 Lagna): <span>{lagna.get('d9_sign')} (स्वामी: {lagna.get('d9_lord')})</span></div>
                        <div>इन्दु लग्न (Indu Lagna): <span>{indu.get('indu_lagna_sign')} (भाव {indu.get('house_from_d1_lagna')})</span></div>
                    </div>
                </div>

                <div class="birth-card" style="background: #111827; border-color: #dc2626;">
                    <h3 style="color: #facc15; margin: 0 0 8px 0; text-align: center; border-bottom: 1px solid #374151; padding-bottom: 5px; font-size: 1.12rem;">
                        वर्तमान सक्रिय विम्शोत्तरी दशा पदानुक्रम (Active Running Dasha)
                    </h3>
                    <div class="birth-grid" style="font-size: 0.95rem;">
                        <div>1. महादशा (Mahadasha): <span>{active_h.get('mahadasha', {}).get('lord')} ({active_h.get('mahadasha', {}).get('start_date')} से {active_h.get('mahadasha', {}).get('end_date')})</span></div>
                        <div>2. अंतर्दशा (Antardasha): <span>{active_h.get('antardasha', {}).get('lord')} ({active_h.get('antardasha', {}).get('start_date')} से {active_h.get('antardasha', {}).get('end_date')})</span></div>
                        <div>3. प्रत्यंतर (Pratyantar): <span>{active_h.get('pratyantardasha', {}).get('lord')} ({active_h.get('pratyantardasha', {}).get('start_date')} से {active_h.get('pratyantardasha', {}).get('end_date')})</span></div>
                        <div>4. सूक्ष्म दशा (Sookshma): <span>{active_h.get('sookshma_dasha', {}).get('lord')} ({active_h.get('sookshma_dasha', {}).get('start_date')} से {active_h.get('sookshma_dasha', {}).get('end_date')})</span></div>
                    </div>
                </div>

                <div class="birth-card" style="background: #1f2937; border-color: #facc15;">
                    <h3 style="color: #facc15; margin: 0 0 6px 0; text-align: center; border-bottom: 2px solid #dc2626; padding-bottom: 5px; font-size: 1.1rem;">
                        कुंडली के प्रमुख स्तंभ एवं दोष प्रमाणीकरण सारांश
                    </h3>
                    <div class="birth-grid" style="font-size: 0.94rem;">
                        <div>लग्नेश (Lagna Lord): <span>{lagna.get('d1_lord')} (D9 स्वामी: {lagna.get('d9_lord')})</span></div>
                        <div>इन्दु लग्न स्वामी: <span>{indu.get('indu_lagna_lord')} (धन कारक भाव {indu.get('house_from_d1_lagna')})</span></div>
                        <div>मांगलिक दोष स्थिति: <span>{'मांगलिक प्रभाव उपस्थित' if doshas.get('manglik', {}).get('is_manglik') else 'मांगलिक दोष मुक्त (शुभ)'}</span></div>
                        <div>काल सर्प योग स्थिति: <span>{'काल सर्प योग उपस्थित' if doshas.get('kaal_sarp', {}).get('is_kaal_sarp') else 'पूर्ण काल सर्प दोष मुक्त'}</span></div>
                    </div>
                </div>

                <div class="book-footer" style="border-top-color: #facc15; color: #facc15;">
                    <span>AstroPulse India</span>
                    <span class="page-num" style="background: #dc2626; color: #fff;">Page 1 of 30</span>
                </div>
            </div>
        </div>

        <!-- ================= PAGE 2: D1 & D9 KUNDLI CHARTS & PLANETARY TABLE (LOCKED) ================= -->
        <div class="book-page table-locked-page" id="locked-page-2">
            <div class="page-border">
                <div class="book-header">
                    <span>ASTROPULSE INDIA — KUNDLI CHARTS & PLANETARY POSITIONS</span>
                    <span>ASTROPULSE INDIA</span>
                </div>
                <div class="book-content" style="justify-content: flex-start;">
                    <div class="chapter-banner" style="margin-top: 2px; padding: 5px 10px;">
                        <h2>लग्न कुंडली (D1 Chart) एवं नवमांश कुंडली (D9 Chart)</h2>
                    </div>
                    <div class="charts-row">
                        <div class="chart-item"><h4>जन्म लग्न कुंडली (D1 Lagna Chart)</h4>{d1_svg}</div>
                        <div class="chart-item"><h4>नवमांश कुंडली (D9 Navamsha Chart)</h4>{d9_svg}</div>
                    </div>

                    <div class="chapter-banner" style="margin-top: 4px; padding: 5px 10px;">
                        <h2>D1 (लग्न) एवं D9 (नवमांश) स्पष्ट ग्रह स्थिति तालिका</h2>
                    </div>
                    <table class="astro-table">
                        <thead>
                            <tr><th>ग्रह (Planet)</th><th>D1 अंश (Degree)</th><th>D1 भाव</th><th>D1 राशि</th><th>राशि स्वामी</th><th>D9 भाव</th><th>D9 राशि</th></tr>
                        </thead>
                        <tbody>{planet_rows_html}</tbody>
                    </table>
                </div>
                <div class="book-footer">
                    <span>{footer_user_info}</span>
                    <span class="page-num">Page 2 of 30</span>
                </div>
            </div>
        </div>

        <!-- ================= PAGE 3: VIMSHOTTARI DASHA & DOSHA SUMMARY TABLE (LOCKED & OVERFLOW-SAFE) ================= -->
        <div class="book-page table-locked-page" id="locked-page-3">
            <div class="page-border">
                <div class="book-header">
                    <span>ASTROPULSE INDIA — VIMSHOTTARI DASHA & DOSHA TABLES</span>
                    <span>ASTROPULSE INDIA</span>
                </div>
                <div class="book-content" id="page3-content-box" style="justify-content: space-between; gap: 4px;">
                    <div>
                        <div class="chapter-banner" style="margin: 2px 0; padding: 4px 10px;">
                            <h2>विम्शोत्तरी महादशा एवं अंतर्दशा तालिका ({curr_md.get('lord')} महादशा)</h2>
                        </div>
                        <table class="page3-table">
                            <thead>
                                <tr><th>महादशा</th><th>अंतर्दशा</th><th>आरंभ तिथि</th><th>समाप्ति तिथि</th><th>वर्तमान स्थिति</th></tr>
                            </thead>
                            <tbody>{ad_rows_html}</tbody>
                        </table>
                    </div>

                    <div>
                        <div class="chapter-banner" style="margin: 2px 0; padding: 4px 10px;">
                            <h2>त्रैकालिक महादशा अनुक्रम (Past, Present & Future)</h2>
                        </div>
                        <table class="page3-table">
                            <thead>
                                <tr><th>दशा कालखंड</th><th>महादशा स्वामी</th><th>आरंभ तिथि</th><th>समाप्ति तिथि</th><th>प्रभाव स्तर</th></tr>
                            </thead>
                            <tbody>
                                <tr><td><b>पूर्व महादशा</b></td><td>{prev_md.get('lord')} महादशा</td><td>{prev_md.get('start_date')}</td><td>{prev_md.get('end_date')}</td><td>पूर्ण (बीत चुकी)</td></tr>
                                <tr style="background-color: #fef08a; font-weight: bold;"><td><b>वर्तमान महादशा</b></td><td>{curr_md.get('lord')} महादशा</td><td>{curr_md.get('start_date')}</td><td>{curr_md.get('end_date')}</td><td>🟢 वर्तमान में सक्रिय</td></tr>
                                <tr><td><b>आगामी महादशा</b></td><td>{next_md.get('lord')} महादशा</td><td>{next_md.get('start_date')}</td><td>{next_md.get('end_date')}</td><td>भविष्य में सक्रिय होगी</td></tr>
                            </tbody>
                        </table>
                    </div>

                    <div>
                        <div class="chapter-banner" style="margin: 2px 0; padding: 4px 10px;">
                            <h2>प्रमुख वैदिक दोष एवं योग प्रमाणीकरण तालिका</h2>
                        </div>
                        <table class="page3-table">
                            <thead>
                                <tr><th style="width:28%;">योग / दोष का नाम</th><th>कुंडली में स्थिति एवं ज्योतिषीय निष्कर्ष</th></tr>
                            </thead>
                            <tbody>
                                <tr><td><b>मांगलिक दोष</b></td><td>{doshas.get('manglik', {}).get('details')}</td></tr>
                                <tr><td><b>काल सर्प योग</b></td><td>{doshas.get('kaal_sarp', {}).get('details')}</td></tr>
                                <tr><td><b>पितृ दोष</b></td><td>{doshas.get('pitra_dosh', {}).get('details')}</td></tr>
                                <tr><td><b>शनि साढ़े साती</b></td><td>{doshas.get('sade_sati', {}).get('details')}</td></tr>
                                <tr><td><b>इन्दु लग्न</b></td><td>राशि: {indu.get('indu_lagna_sign')} | स्वामी: {indu.get('indu_lagna_lord')} | लग्न से भाव: {indu.get('house_from_d1_lagna')}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="book-footer">
                    <span>{footer_user_info}</span>
                    <span class="page-num">Page 3 of 30</span>
                </div>
            </div>
        </div>

        <!-- ================= PAGES 4 TO 30 (DYNAMIC CHAPTERS CONTAINER) ================= -->
        <div id="dynamic-chapters-wrapper">
            {pages_html}
        </div>

    </div>

    <script>
        const SERVER_TXT_PROMPT = `{escaped_txt_prompt}`;
        const USER_FOOTER_INFO = `{footer_user_info}`;
        const USER_NAME = `{name}`;

        function downloadTxtPrompt() {{
            const blob = new Blob([SERVER_TXT_PROMPT], {{ type: 'text/plain;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `AstroPulse_Prompt_${{USER_NAME}}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        function openGeminiModal() {{
            document.getElementById('gemini-modal').style.display = 'flex';
        }}

        function closeGeminiModal() {{
            document.getElementById('gemini-modal').style.display = 'none';
        }}

        /**
         * जेमिनी से प्राप्त .TXT या HTML को पार्स करके Page 1-3 को छेड़े बिना Page 4+ तैयार करता है
         */
        function applyGeminiContent() {{
            const raw = document.getElementById('gemini-input-box').value.trim();
            if (!raw) {{
                alert('कृपया पहले जेमिनी का टेक्स्ट या HTML पेस्ट करें!');
                return;
            }}

            const chapters = [];

            // Case 1: यदि यूज़र ने HTML कोड पेस्ट किया है
            if (raw.includes('<div class="book-page"') || raw.includes('<p class="book-para"')) {{
                const parser = new DOMParser();
                const doc = parser.parseFromString(raw, 'text/html');
                const parsedPages = doc.querySelectorAll('.book-page');
                parsedPages.forEach((p) => {{
                    const paras = Array.from(p.querySelectorAll('.book-para')).map(el => el.innerHTML.trim()).filter(Boolean);
                    if (paras.length > 0) {{
                        const h2 = p.querySelector('.chapter-banner h2');
                        const title = h2 ? h2.textContent.trim() : `अध्याय ${{chapters.length + 1}}`;
                        chapters.push({{ title, paras }});
                    }}
                }});
            }}

            // Case 2: यदि यूज़र ने प्लेन टेक्स्ट (PAGE BREAK या अध्याय वाला) पेस्ट किया है
            if (chapters.length === 0) {{
                let blocks = raw.split(/=+\\s*PAGE\\s*BREAK\\s*=+/i).map(b => b.trim()).filter(Boolean);
                if (blocks.length <= 1) {{
                    blocks = raw.split(/(?=^(?:अध्याय|PAGE)\\s*\\d+)/im).map(b => b.trim()).filter(Boolean);
                }}

                blocks.forEach((block, idx) => {{
                    const lines = block.split(/\\n+/).map(l => l.trim()).filter(Boolean);
                    if (lines.length === 0) return;
                    let title = lines[0].replace(/^#+\\s*/, '').replace(/^\\*+|\\*+$/g, '');
                    let bodyLines = lines.slice(1);
                    if (bodyLines.length === 0) {{
                        title = `अध्याय ${{idx + 1}}`;
                        bodyLines = [lines[0]];
                    }}
                    chapters.push({{ title, paras: bodyLines }});
                }});
            }}

            if (chapters.length === 0) {{
                alert('कोई मान्य अध्याय या पैराग्राफ नहीं मिला। कृपया सही टेक्स्ट पेस्ट करें।');
                return;
            }}

            const totalPages = 3 + chapters.length;
            // Page 1, 2, 3 के फुटर में कुल पेज संख्या अपडेट करें
            document.querySelectorAll('#locked-page-1 .page-num, #locked-page-2 .page-num, #locked-page-3 .page-num').forEach((el, i) => {{
                el.textContent = `Page ${{i + 1}} of ${{totalPages}}`;
            }});

            const wrapper = document.getElementById('dynamic-chapters-wrapper');
            let newHtml = '';
            chapters.forEach((ch, idx) => {{
                const pageNum = idx + 4;
                const parasHtml = ch.paras.map(p => `<p class="book-para">${{p}}</p>`).join('');
                newHtml += `
                <div class="book-page dynamic-chapter-page">
                    <div class="page-border">
                        <div class="book-header">
                            <span>ASTROPULSE INDIA — CALL CONSULTATION & MASTER REPORT</span>
                            <span>ASTROPULSE INDIA</span>
                        </div>
                        <div class="chapter-banner">
                            <h2>${{ch.title}}</h2>
                        </div>
                        <div class="book-content">
                            ${{parasHtml}}
                        </div>
                        <div class="book-footer">
                            <span>${{USER_FOOTER_INFO}}</span>
                            <span class="page-num">Page ${{pageNum}} of ${{totalPages}}</span>
                        </div>
                    </div>
                </div>`;
            }});

            wrapper.innerHTML = newHtml;
            closeGeminiModal();
            setTimeout(autoFitAllPages, 100);
        }}

        /**
         * SMART AUTO-FIT ENGINE (Page 2-3 की टेबल्स और Page 4-30 के पैराग्राफ दोनों को फिट करता है)
         */
        function autoFitAllPages() {{
            // 1. Page 2 और Page 3 की टेबल्स को ऑटो-फिट करें ताकि फुटर कभी न दबे
            document.querySelectorAll('.table-locked-page').forEach((page) => {{
                const content = page.querySelector('.book-content');
                const tables = page.querySelectorAll('table');
                const banners = page.querySelectorAll('.chapter-banner h2');
                if (!content || tables.length === 0) return;

                let fontSize = 13.2;
                let cellPad = 4.0;
                let guard = 0;

                while (content.scrollHeight > content.clientHeight && guard < 40) {{
                    if (fontSize > 9.5) fontSize -= 0.25;
                    if (cellPad > 1.5) cellPad -= 0.2;
                    tables.forEach(t => {{
                        t.style.fontSize = fontSize.toFixed(2) + 'px';
                        t.querySelectorAll('td, th').forEach(cell => {{
                            cell.style.padding = `${{cellPad.toFixed(1)}}px 5px`;
                        }});
                    }});
                    banners.forEach(b => {{
                        b.style.fontSize = Math.max(13, fontSize + 1.5).toFixed(1) + 'px';
                    }});
                    guard++;
                }}
            }});

            // 2. Page 4 से 30 तक के सभी पैराग्राफ पन्नों को ऑटो-फिट करें
            const pages = document.querySelectorAll('.book-page');
            pages.forEach((page) => {{
                const content = page.querySelector('.book-content');
                const paras = page.querySelectorAll('.book-para');
                if (!content || paras.length === 0) return;

                content.style.justifyContent = 'flex-start';

                let fontSize = 15.8;
                let lineHeight = 1.70;
                let paraGap = 9;

                const applyStyles = (fs, lh, gap) => {{
                    paras.forEach((p, idx) => {{
                        p.style.fontSize = fs.toFixed(2) + 'px';
                        p.style.lineHeight = lh.toFixed(2);
                        p.style.marginBottom = (idx === paras.length - 1) ? '0px' : gap.toFixed(1) + 'px';
                    }});
                }};

                const getUsedHeight = () => {{
                    let total = 0;
                    paras.forEach((p, idx) => {{
                        const mb = (idx === paras.length - 1) ? 0 : (parseFloat(p.style.marginBottom) || 0);
                        total += p.getBoundingClientRect().height + mb;
                    }});
                    return total;
                }};

                applyStyles(fontSize, lineHeight, paraGap);
                const maxAvailable = content.clientHeight - 10;

                // यदि टेक्स्ट बड़ा है -> छोटा करके फुटर के ऊपर फिट करें
                let guard = 0;
                while (getUsedHeight() > maxAvailable && guard < 100) {{
                    if (fontSize > 10.5) fontSize -= 0.2;
                    if (lineHeight > 1.28) lineHeight -= 0.02;
                    if (paraGap > 3.5) paraGap -= 0.25;
                    applyStyles(fontSize, lineHeight, paraGap);
                    guard++;
                }}

                // यदि टेक्स्ट छोटा है -> बड़ा करके पूरा पन्ना बराबर भरें
                guard = 0;
                while (getUsedHeight() < maxAvailable * 0.92 && guard < 80) {{
                    const pFs = fontSize, pLh = lineHeight, pGap = paraGap;
                    if (fontSize < 19.5) fontSize += 0.2;
                    if (lineHeight < 1.98) lineHeight += 0.02;
                    if (paraGap < 16) paraGap += 0.3;
                    applyStyles(fontSize, lineHeight, paraGap);

                    if (getUsedHeight() > maxAvailable) {{
                        applyStyles(pFs, pLh, pGap);
                        break;
                    }}
                    guard++;
                }}

                content.style.justifyContent = 'space-between';
            }});
        }}

        window.addEventListener('DOMContentLoaded', () => {{
            autoFitAllPages();
            if (document.fonts && document.fonts.ready) {{
                document.fonts.ready.then(() => autoFitAllPages());
            }}
            setTimeout(autoFitAllPages, 400);
            setTimeout(autoFitAllPages, 1000);
        }});

        window.addEventListener('resize', autoFitAllPages);
        window.addEventListener('beforeprint', autoFitAllPages);

        /**
         * GLITCH-FREE PAGE-BY-PAGE PDF EXPORT ENGINE:
         * यह एक-एक .book-page को अलग-अलग A4 कैनवास में रेंडर करके PDF में जोड़ता है,
         * जिससे न कोई पन्ना कटता है, न Page 3 टूटता है और न ही कैनवास क्रैश होता है।
         */
        async function downloadDirectPDF() {{
            autoFitAllPages();
            const btn = document.getElementById('btn-direct-pdf');
            const origText = btn.innerHTML;
            btn.disabled = true;

            try {{
                const pages = Array.from(document.querySelectorAll('.book-page'));
                const jsPDFClass = (window.jspdf && window.jspdf.jsPDF) ? window.jspdf.jsPDF : null;

                if (!jsPDFClass || typeof html2canvas === 'undefined') {{
                    window.print();
                    btn.disabled = false;
                    btn.innerHTML = origText;
                    return;
                }}

                const pdf = new jsPDFClass({{ orientation: 'portrait', unit: 'mm', format: 'a4', compress: true }});

                for (let i = 0; i < pages.length; i++) {{
                    const page = pages[i];
                    btn.innerHTML = `⏳ PDF बन रहा है (${{i + 1}} / ${{pages.length}})...`;
                    page.classList.add('pdf-exporting');

                    const bgColor = page.classList.contains('cover-page') ? '#0a0a0a' : '#ffffff';
                    const canvas = await html2canvas(page, {{
                        scale: 2,
                        useCORS: true,
                        backgroundColor: bgColor,
                        logging: false
                    }});

                    page.classList.remove('pdf-exporting');
                    const imgData = canvas.toDataURL('image/jpeg', 0.96);

                    if (i > 0) {{
                        pdf.addPage('a4', 'portrait');
                    }}
                    pdf.addImage(imgData, 'JPEG', 0, 0, 210, 297);
                }}

                btn.innerHTML = '✅ डाउनलोड हो रहा है...';
                pdf.save(`AstroPulse_Master_Report_${{USER_NAME}}.pdf`);
            }} catch (err) {{
                console.error('PDF Export Error:', err);
                alert('Direct PDF में समस्या आई, कृपया Print PDF का उपयोग करें: ' + err.message);
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = origText;
            }}
        }}
    </script>
</body>
</html>
"""
    return full_book_html


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/get_chart")
def get_chart(year: int, month: int, day: int, hour: int, minute: int, city: str, name: str = "Unknown", gender: str = "Not Specified"):
    try:
        data = get_vedic_planets(year, month, day, hour, minute, city)
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/save_chart")
def save_chart(name: str = Form(...), gender: str = Form(...), dob: str = Form(...), tob: str = Form(...), city: str = Form(...), chart_data: str = Form(...)):
    conn = sqlite3.connect("astropulse.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO saved_charts (name, gender, dob, tob, city, chart_data) VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, gender, dob, tob, city, chart_data))
    conn.commit()
    conn.close()
    return {"message": "कुंडली सफलतापूर्वक सेव हो गई है!"}


@app.get("/get_saved_charts")
def get_saved_charts():
    conn = sqlite3.connect("astropulse.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, gender, dob, tob, city, chart_data FROM saved_charts ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    charts = [{"id": r[0], "name": r[1], "gender": r[2], "dob": r[3], "tob": r[4], "city": r[5], "chart_data": r[6]} for r in rows]
    return {"charts": charts}


@app.delete("/delete_chart/{chart_id}")
def delete_chart(chart_id: int):
    conn = sqlite3.connect("astropulse.db")
    cursor = conn.cursor()
    cursor.execute('DELETE FROM saved_charts WHERE id = ?', (chart_id,))
    conn.commit()
    conn.close()
    return {"message": "कुंडली सफलतापूर्वक डिलीट कर दी गई है!"}


@app.get("/check_service/{service_type}")
def check_service(service_type: str, year: int, month: int, day: int, hour: int, minute: int, city: str):
    try:
        service_decoded = urllib.parse.unquote(service_type)
        chart_data = get_vedic_planets(year, month, day, hour, minute, city)
        doshas = chart_data.get("doshas", {})
        s_lower = service_decoded.lower()
        if "mangal" in s_lower or "मंगल" in s_lower:
            m_info = doshas.get("manglik", {})
            result_text = f"🔴 मंगल दोष विश्लेषण:\n\nस्थिति: {'मंगल दोष उपस्थित है' if m_info.get('is_manglik') else 'मंगल दोष नहीं है (शुभ)'}\nविवरण: {m_info.get('details')}"
        elif "kaal sarp" in s_lower or "काल सर्प" in s_lower:
            k_info = doshas.get("kaal_sarp", {})
            result_text = f"🐍 काल सर्प दोष योग:\n\nस्थिति: {'काल सर्प योग उपस्थित है' if k_info.get('is_kaal_sarp') else 'काल सर्प दोष नहीं है'}\nविवरण: {k_info.get('details')}"
        elif "sade sati" in s_lower or "साढ़े साती" in s_lower:
            s_info = doshas.get("sade_sati", {})
            result_text = f"🪐 शनि साढ़े साती:\n\nविवरण: {s_info.get('details')}"
        elif "pitra" in s_lower or "पितृ दोष" in s_lower:
            p_info = doshas.get("pitra_dosh", {})
            result_text = f"⚱️ पितृ दोष जांच:\n\nविवरण: {p_info.get('details')}"
        else:
            result_text = f"✨ {service_decoded} का ज्योतिषीय विश्लेषण:\n\nग्रहण किए गए डेटा के अनुसार कुण्डली के योग सामान्य रूप से सक्रिय हैं।"
        return {"status": "success", "result": result_text}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/generate_report/{report_type}")
def generate_report(
    report_type: str,
    year: int, month: int, day: int, hour: int, minute: int,
    city: str, name: str = "जातक", gender: str = "पुरुष",
    mode: str = "auto"
):
    try:
        report_type_decoded = urllib.parse.unquote(report_type)
        chart_data = get_vedic_planets(year, month, day, hour, minute, city)

        is_tenth_report = ("consultation" in report_type_decoded.lower() or "कॉल" in report_type_decoded.lower() or "10" in report_type_decoded.lower())

        # यदि mode="txt" मांगा गया हो या 1 से 9 नंबर की रिपोर्ट हो
        if mode == "txt" or (not is_tenth_report and mode != "html"):
            master_prompt, _ = get_prompt_content(report_type_decoded)
            final_prompt_output = build_merged_prompt(
                master_prompt, chart_data, report_type_decoded,
                name, gender, day, month, year, hour, minute, city
            )
            safe_filename = f"AstroPulse_{abs(hash(report_type_decoded))}.txt"
            return Response(
                content=final_prompt_output,
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
            )

        # 10वीं रिपोर्ट (या mode="html"): 30-पेज रॉयल टेम्पलेट + इन-बिल्ट .txt डाउनलोडर + 1-Click PDF एक्सपोर्टर
        full_html = build_full_30_page_consultation_html(
            chart_data, name, gender, day, month, year, hour, minute, city, report_title=report_type_decoded
        )
        return HTMLResponse(content=full_html)

    except Exception as e:
        return Response(content=f"Report Generation Error: {str(e)}", status_code=500)