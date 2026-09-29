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
    
    if "indu" in report_lower or "इंदु" in report_lower:
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
    return {"message": "Kundli safalpurvak save ho gayi hai!"}

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
    return {"message": "Kundli safalpurvak delete kar di gayi hai!"}

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
            result_text = f"🔴 Mangal Dosh Analysis:\n\nSthiti: {'Mangal Dosh upasthit hai' if m_info.get('is_manglik') else 'Mangal Dosh nahi hai (Shubh)'}\nVivaran: {m_info.get('details', 'Kundli ke adhaar par Mangal ki sthiti samanya hai.')}"
        elif "kaal sarp" in s_lower or "काल सर्प" in s_lower:
            k_info = doshas.get("kaal_sarp", {})
            result_text = f"🐍 Kaal Sarp Dosh Yoga:\n\nSthiti: {'Kaal Sarp yog upasthit hai' if k_info.get('is_kaal_sarp') else 'Kaal Sarp dosh nahi hai'}\nVivaran: {k_info.get('details', 'Rahu-Ketu ke madhya sabhi grahon ki sthiti ka vishleshan purn hai.')}"
        elif "sade sati" in s_lower or "साढ़े साती" in s_lower:
            s_info = doshas.get("sade_sati", {})
            result_text = f"🪐 Shani Sade Sati:\n\nVivaran: {s_info.get('details', 'Vartman mein Shani ki gochar sthiti aur sade sati ka prabhav samanya hai.')}"
        elif "pitra" in s_lower or "पितृ दोष" in s_lower:
            p_info = doshas.get("pitra_dosh", {})
            result_text = f"⚱️ Pitra Dosh Jaanch:\n\nVivaran: {p_info.get('details', 'Kundli mein Surya, Rahu aur Pitra bhav ke vishleshan ke anusar sthiti anukul hai.')}"
        else:
            result_text = f"✨ {service_decoded} ka Jyotishiya Vishleshan:\n\nGrahan kiye gaye data ke anusar kundli ke yog samanya roop se sakriya hain."

        return {"status": "success", "result": result_text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 🚀 PDF REPORT GENERATOR ---
@app.get("/generate_report/{report_type}")
def generate_report(report_type: str, year: int, month: int, day: int, hour: int, minute: int, city: str, name: str, gender: str):
    try:
        report_type_decoded = urllib.parse.unquote(report_type)
        chart_data = get_vedic_planets(year, month, day, hour, minute, city)
        
        master_prompt, found_file = get_prompt_content(report_type_decoded)
        
        final_report_content = f"""{master_prompt}

==================================================
KUNDLI JSON DATA (ENGINE CALCULATED)
==================================================
{json.dumps(chart_data, ensure_ascii=False, indent=2)}
"""

        safe_filename = f"AstroPulse_Report_{abs(hash(report_type_decoded))}.txt"

        return Response(
            content=final_report_content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
        )

    except Exception as e:
        return Response(content=f"Report Generation Error: {str(e)}", status_code=500)