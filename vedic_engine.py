import swisseph as swe
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta

ZODIAC_SIGNS = [
    "Aries (मेष)", "Taurus (वृषभ)", "Gemini (मिथुन)", "Cancer (कर्क)", 
    "Leo (सिंह)", "Virgo (कन्या)", "Libra (तुला)", "Scorpio (वृश्चिक)", 
    "Sagittarius (धनु)", "Capricorn (मकर)", "Aquarius (कुंभ)", "Pisces (मीन)"
]

DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]
TOTAL_DASHA_YEARS = 120.0

def get_degree_info(degree):
    d1_sign_index = int(degree // 30)
    d9_sign_index = int(degree * 0.3) % 12
    return {
        "degree_within_sign": round(degree % 30, 4),
        "absolute_degree": round(degree, 4),
        "d1_sign": ZODIAC_SIGNS[d1_sign_index],
        "d9_sign": ZODIAC_SIGNS[d9_sign_index]
    }

# महादशा की पूरी परतें (AD, PD, SD) खोलने का फंक्शन
def build_md_breakdown(md_idx, md_start_date, today):
    all_ads = []
    ad_start = md_start_date
    for i in range(9):
        ad_idx = (md_idx + i) % 9
        ad_years = (DASHA_YEARS[md_idx] * DASHA_YEARS[ad_idx]) / TOTAL_DASHA_YEARS
        ad_end = ad_start + timedelta(days=ad_years * 365.2425)
        is_current_ad = ad_start <= today <= ad_end
        
        all_pds = []
        pd_start = ad_start
        for j in range(9):
            pd_idx = (ad_idx + j) % 9
            pd_years = (DASHA_YEARS[md_idx] * DASHA_YEARS[ad_idx] * DASHA_YEARS[pd_idx]) / (TOTAL_DASHA_YEARS**2)
            pd_end = pd_start + timedelta(days=pd_years * 365.2425)
            is_current_pd = pd_start <= today <= pd_end
            
            all_sds = []
            sd_start = pd_start
            for k in range(9):
                sd_idx = (pd_idx + k) % 9
                sd_years = (DASHA_YEARS[md_idx] * DASHA_YEARS[ad_idx] * DASHA_YEARS[pd_idx] * DASHA_YEARS[sd_idx]) / (TOTAL_DASHA_YEARS**3)
                sd_end = sd_start + timedelta(days=sd_years * 365.2425)
                is_current_sd = sd_start <= today <= sd_end
                
                all_sds.append({
                    "lord": DASHA_LORDS[sd_idx],
                    "start_date": sd_start.strftime("%Y-%m-%d"),
                    "end_date": sd_end.strftime("%Y-%m-%d"),
                    "is_current": is_current_sd
                })
                sd_start = sd_end
            
            all_pds.append({
                "lord": DASHA_LORDS[pd_idx],
                "start_date": pd_start.strftime("%Y-%m-%d"),
                "end_date": pd_end.strftime("%Y-%m-%d"),
                "is_current": is_current_pd,
                "sookshma_dashas_breakdown": all_sds
            })
            pd_start = pd_end
        
        all_ads.append({
            "lord": DASHA_LORDS[ad_idx],
            "start_date": ad_start.strftime("%Y-%m-%d"),
            "end_date": ad_end.strftime("%Y-%m-%d"),
            "is_current": is_current_ad,
            "pratyantardashas_breakdown": all_pds
        })
        ad_start = ad_end
    return all_ads

def calculate_comprehensive_dasha(moon_degree, birth_year, birth_month, birth_day):
    nakshatra_length = 360 / 27
    nakshatra_passed = moon_degree / nakshatra_length
    nakshatra_index = int(nakshatra_passed)
    
    lord_index = nakshatra_index % 9
    fraction_passed = nakshatra_passed - nakshatra_index
    fraction_left = 1.0 - fraction_passed
    balance_years = DASHA_YEARS[lord_index] * fraction_left
    
    birth_date = datetime(birth_year, birth_month, birth_day)
    dasha_start_date = birth_date - timedelta(days=(DASHA_YEARS[lord_index] - balance_years) * 365.2425)
    dasha_end_date = birth_date + timedelta(days=balance_years * 365.2425)
    
    today = datetime.now()
    current_md_idx = lord_index
    
    # वर्तमान महादशा खोजना
    while today > dasha_end_date:
        dasha_start_date = dasha_end_date
        current_md_idx = (current_md_idx + 1) % 9
        dasha_end_date = dasha_start_date + timedelta(days=DASHA_YEARS[current_md_idx] * 365.2425)
        
    # पिछली महादशा
    prev_md_idx = (current_md_idx - 1) % 9
    prev_md_start = dasha_start_date - timedelta(days=DASHA_YEARS[prev_md_idx] * 365.2425)
    
    # अगली महादशा
    next_md_idx = (current_md_idx + 1) % 9
    next_md_start = dasha_end_date
    
    # तीनों महादशाओं का पूरा ब्रेकडाउन
    prev_md = {
        "lord": DASHA_LORDS[prev_md_idx], "start_date": prev_md_start.strftime("%Y-%m-%d"),
        "end_date": dasha_start_date.strftime("%Y-%m-%d"), "is_current": False,
        "antardashas_breakdown": build_md_breakdown(prev_md_idx, prev_md_start, today)
    }
    current_md = {
        "lord": DASHA_LORDS[current_md_idx], "start_date": dasha_start_date.strftime("%Y-%m-%d"),
        "end_date": dasha_end_date.strftime("%Y-%m-%d"), "is_current": True,
        "antardashas_breakdown": build_md_breakdown(current_md_idx, dasha_start_date, today)
    }
    next_md = {
        "lord": DASHA_LORDS[next_md_idx], "start_date": next_md_start.strftime("%Y-%m-%d"),
        "end_date": (next_md_start + timedelta(days=DASHA_YEARS[next_md_idx] * 365.2425)).strftime("%Y-%m-%d"),
        "is_current": False, "antardashas_breakdown": build_md_breakdown(next_md_idx, next_md_start, today)
    }

    return {
        "today_date": today.strftime("%Y-%m-%d"),
        "previous_mahadasha": prev_md,
        "current_mahadasha": current_md,
        "next_mahadasha": next_md
    }

def get_vedic_planets(year, month, day, hour, minute, city_name, tz_offset=5.5):
    geolocator = Nominatim(user_agent="vedic_api_project")
    location = geolocator.geocode(city_name)
    if not location: return {"error": "City not found."}

    decimal_hour_local = hour + (minute / 60.0)
    decimal_hour_utc = decimal_hour_local - tz_offset
    jd = swe.julday(year, month, day, decimal_hour_utc)
    
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH

    cusps, ascmc = swe.houses_ex(jd, location.latitude, location.longitude, b'P', flags)
    
    lagna_d1_idx = int(ascmc[0] // 30)
    lagna_d9_idx = int(ascmc[0] * 0.3) % 12
    lagna_info = get_degree_info(ascmc[0])

    planets = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}
    planet_positions = {}
    moon_abs_deg = 0.0

    for name, planet_id in planets.items():
        calc_result, _ = swe.calc_ut(jd, planet_id, flags)
        deg = calc_result[0]
        if name == "Moon": moon_abs_deg = deg
        p_info = get_degree_info(deg)
        p_info["d1_house"] = ((int(deg // 30) - lagna_d1_idx) % 12) + 1
        p_info["d9_house"] = ((int(deg * 0.3) % 12 - lagna_d9_idx) % 12) + 1
        planet_positions[name] = p_info

    ketu_abs_deg = (planet_positions["Rahu"]["absolute_degree"] + 180) % 360
    k_info = get_degree_info(ketu_abs_deg)
    k_info["d1_house"] = ((int(ketu_abs_deg // 30) - lagna_d1_idx) % 12) + 1
    k_info["d9_house"] = ((int(ketu_abs_deg * 0.3) % 12 - lagna_d9_idx) % 12) + 1
    planet_positions["Ketu"] = k_info

    dasha_info = calculate_comprehensive_dasha(moon_abs_deg, year, month, day)

    # -------------------------------------------------------------------
    # नया लॉजिक: भावों (Houses 1 से 12) के अनुसार ग्रहों को डिक्शनरी में डालना
    # -------------------------------------------------------------------
    houses = {str(i): {"planets": []} for i in range(1, 13)}
    d9_houses = {str(i): {"planets": []} for i in range(1, 13)}

    # हर ग्रह को उसके सही भाव (D1 और D9) में सेट करना
    for planet_name, details in planet_positions.items():
        d1_house_num = str(details["d1_house"])
        d9_house_num = str(details["d9_house"])
        
        houses[d1_house_num]["planets"].append(planet_name)
        d9_houses[d9_house_num]["planets"].append(planet_name)

    return {
        "birth_details": {"city": city_name},
        "lagna": lagna_info,
        "planets": planet_positions,
        "houses": houses,            # D1 कुण्डली के भाव और उनमें बैठे ग्रह
        "d9_houses": d9_houses,      # D9 (नवमांश) के भाव और उनमें बैठे ग्रह
        "dasha_timeline": dasha_info
    }