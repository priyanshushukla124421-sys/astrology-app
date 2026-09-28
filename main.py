from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from vedic_engine import get_vedic_planets
import sqlite3
import urllib.parse
import os
import json

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

# --- Smart Prompt Mapping for Reports ---
def get_prompt_content(report_type_decoded):
    files = os.listdir(".")
    target_keyword = ""
    
    report_lower = report_type_decoded.lower()
    if "lagna" in report_lower or "लग्न" in report_lower:
        target_keyword = "lagna"
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
    else:
        target_keyword = "lagna"
        
    for file in files:
        if file.endswith(".txt") and target_keyword in file.lower():
            with open(file, "r", encoding="utf-8") as f:
                return f.read(), file
                
    for file in files:
        if file.endswith(".txt"):
            with open(file, "r", encoding="utf-8") as f:
                return f.read(), file
                
    return "Aapke liye vishesh Vedic report taiyar ki ja rahi hai.", "default.txt"

# --- Home & UI Routes ---
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

# --- 🛠️ SERVICES HUB ---
@app.get("/check_service/{service_type}")
def check_service(service_type: str, year: int, month: int, day: int, hour: int, minute: int, city: str):
    try:
        service_decoded = urllib.parse.unquote(service_type)
        chart_data = get_vedic_planets(year, month, day, hour, minute, city)
        
        doshas = chart_data.get("doshas", {})
        result_text = ""
        
        s_lower = service_decoded.lower()
        if "mangal" in s_lower or "मंगल" in s_lower:
            m_info = doshas.get("manglik", {})
            result_text = f"🔴 मंगल दोष विश्लेषण:\n\nस्थिति: {'मंगल दोष उपस्थित है' if m_info.get('is_manglik') else 'मंगल दोष नहीं है (शुभ)'}\nविवरण: {m_info.get('details', 'कुण्डली के आधार पर मंगल की स्थिति सामान्य है।')}"
        elif "kaal sarp" in s_lower or "काल सर्प" in s_lower:
            k_info = doshas.get("kaal_sarp", {})
            result_text = f"🐍 काल सर्प दोष योग:\n\nस्थिति: {'काल सर्प योग उपस्थित है' if k_info.get('is_kaal_sarp') else 'काल सर्प दोष नहीं है'}\nविवरण: {k_info.get('details', 'राहु-केतु के मध्य सभी ग्रहों की स्थिति का विश्लेषण पूर्ण है।')}"
        elif "sade sati" in s_lower or "साढ़े साती" in s_lower:
            s_info = doshas.get("sade_sati", {})
            result_text = f"🪐 शनि साढ़े साती:\n\nविवरण: {s_info.get('details', 'वर्तमान में शनि की गोचर स्थिति और साढ़े साती का प्रभाव सामान्य है।')}"
        elif "pitra" in s_lower or "पितृ दोष" in s_lower:
            p_info = doshas.get("pitra_dosh", {})
            result_text = f"⚱️ पितृ दोष जांच:\n\nविवरण: {p_info.get('details', 'कुण्डली में सूर्य, राहु और पितृ भाव के विश्लेषण के अनुसार स्थिति अनुकूल है।')}"
        else:
            result_text = f"✨ {service_decoded} का ज्योतिषीय विश्लेषण:\n\nग्रहण किए गए डेटा के अनुसार कुण्डली के योग सामान्य रूप से सक्रिय हैं।"

        return {"status": "success", "result": result_text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 🚀 PDF REPORT GENERATOR (Prompt + Vedic Engine JSON) ---
@app.get("/generate_report/{report_type}")
def generate_report(report_type: str, year: int, month: int, day: int, hour: int, minute: int, city: str, name: str = "जातक", gender: str = "पुरुष"):
    try:
        report_type_decoded = urllib.parse.unquote(report_type)
        chart_data = get_vedic_planets(year, month, day, hour, minute, city)
        
        master_prompt, found_file = get_prompt_content(report_type_decoded)
        
        final_report_content = f"""
==================================================
ASTROPULSE INDIA - PROFESSIONAL VEDIC REPORT
==================================================
Report Type: {report_type_decoded}
Source Master Prompt File: {found_file}
--------------------------------------------------
JAATAK VIVECHAN (USER DETAILS):
- Name: {name}
- Gender: {gender}
- DOB: {day}-{month}-{year}
- Time: {hour:02d}:{minute:02d}
- Birth Place: {city}
==================================================

[MASTER PROMPT GUIDELINES & FRAMEWORK]
{master_prompt}

==================================================
KUNDLI JSON DATA (ENGINE CALCULATED)
==================================================
{json.dumps(chart_data, ensure_ascii=False, indent=2)}

--------------------------------------------------
REPORT STATUS: Successfully Compiled & Generated via AstroPulse Engine.
==================================================
"""

        # Safe filename to prevent latin-1 encoding crashes
        safe_filename = "AstroPulse_Professional_Report.txt"

        return Response(
            content=final_report_content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
        )

    except Exception as e:
        return Response(content=f"Report Generation Error: {str(e)}", status_code=500)