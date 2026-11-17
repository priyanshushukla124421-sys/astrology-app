import swisseph as swe
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta

ZODIAC_SIGNS = [
    "Aries (मेष)", "Taurus (वृषभ)", "Gemini (मिथुन)", "Cancer (कर्क)", 
    "Leo (सिंह)", "Virgo (कन्या)", "Libra (तुला)", "Scorpio (वृश्चिक)", 
    "Sagittarius (धनु)", "Capricorn (मकर)", "Aquarius (कुंभ)", "Pisces (मीन)"
]

SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
]

INDU_KALAS = {
    "Sun": 30, "Moon": 16, "Mars": 6, "Mercury": 8,
    "Jupiter": 10, "Venus": 12, "Saturn": 1
}

DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]
TOTAL_DASHA_YEARS = 120.0

FALLBACK_CITIES = {
    "raebareli": (26.2345, 81.2409),
    "lucknow": (26.8467, 80.9462),
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "kanpur": (26.4499, 80.3319),
    "varanasi": (25.3176, 82.9739),
    "prayagraj": (25.4358, 81.8463),
    "ayodhya": (26.7922, 82.1998)
}

def get_d24_sign_index(degree):
    sign_idx = int(degree // 30)
    deg_in_sign = degree % 30
    part = int(deg_in_sign * 24 // 30)
    if sign_idx % 2 == 0:
        return (4 + part) % 12
    else:
        return (3 + part) % 12

def get_degree_info(degree):
    d1_sign_index = int(degree // 30) % 12
    d9_sign_index = int(degree * 0.3) % 12
    d24_sign_index = get_d24_sign_index(degree)
    return {
        "degree_within_sign": round(degree % 30, 4),
        "absolute_degree": round(degree, 4),
        "d1_sign_index": d1_sign_index,
        "d1_sign": ZODIAC_SIGNS[d1_sign_index],
        "d1_lord": SIGN_LORDS[d1_sign_index],
        "d9_sign_index": d9_sign_index,
        "d9_sign": ZODIAC_SIGNS[d9_sign_index],
        "d9_lord": SIGN_LORDS[d9_sign_index],
        "d24_sign_index": d24_sign_index,
        "d24_sign": ZODIAC_SIGNS[d24_sign_index]
    }

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

def extract_exact_active_hierarchy(current_md):
    active_ad = None
    active_pd = None
    active_sd = None
    for ad in current_md.get("antardashas_breakdown", []):
        if ad.get("is_current"):
            active_ad = ad
            for pd in ad.get("pratyantardashas_breakdown", []):
                if pd.get("is_current"):
                    active_pd = pd
                    for sd in pd.get("sookshma_dashas_breakdown", []):
                        if sd.get("is_current"):
                            active_sd = sd
                            break
                    break
            break

    return {
        "mahadasha": {
            "lord": current_md.get("lord"),
            "start_date": current_md.get("start_date"),
            "end_date": current_md.get("end_date")
        },
        "antardasha": {
            "lord": active_ad.get("lord") if active_ad else "N/A",
            "start_date": active_ad.get("start_date") if active_ad else "N/A",
            "end_date": active_ad.get("end_date") if active_ad else "N/A"
        },
        "pratyantardasha": {
            "lord": active_pd.get("lord") if active_pd else "N/A",
            "start_date": active_pd.get("start_date") if active_pd else "N/A",
            "end_date": active_pd.get("end_date") if active_pd else "N/A"
        },
        "sookshma_dasha": {
            "lord": active_sd.get("lord") if active_sd else "N/A",
            "start_date": active_sd.get("start_date") if active_sd else "N/A",
            "end_date": active_sd.get("end_date") if active_sd else "N/A"
        }
    }

def calculate_comprehensive_dasha(moon_degree, birth_year, birth_month, birth_day, birth_hour=0, birth_minute=0):
    nakshatra_length = 360 / 27
    nakshatra_passed = moon_degree / nakshatra_length
    nakshatra_index = int(nakshatra_passed)
    
    lord_index = nakshatra_index % 9
    fraction_passed = nakshatra_passed - nakshatra_index
    fraction_left = 1.0 - fraction_passed
    balance_years = DASHA_YEARS[lord_index] * fraction_left
    
    birth_date = datetime(birth_year, birth_month, birth_day, int(birth_hour), int(birth_minute))
    dasha_start_date = birth_date - timedelta(days=(DASHA_YEARS[lord_index] - balance_years) * 365.2425)
    dasha_end_date = birth_date + timedelta(days=balance_years * 365.2425)
    
    today = datetime.now()
    current_md_idx = lord_index
    
    while today > dasha_end_date:
        dasha_start_date = dasha_end_date
        current_md_idx = (current_md_idx + 1) % 9
        dasha_end_date = dasha_start_date + timedelta(days=DASHA_YEARS[current_md_idx] * 365.2425)
        
    prev_md_idx = (current_md_idx - 1) % 9
    prev_md_start = dasha_start_date - timedelta(days=DASHA_YEARS[prev_md_idx] * 365.2425)
    
    next_md_idx = (current_md_idx + 1) % 9
    next_md_start = dasha_end_date
    
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
        "active_hierarchy_summary": extract_exact_active_hierarchy(current_md),
        "previous_mahadasha": prev_md,
        "current_mahadasha": current_md,
        "next_mahadasha": next_md
    }

def calculate_indu_lagna(lagna_sign_idx, moon_sign_idx, planet_positions):
    lagna_9th_sign = (lagna_sign_idx + 8) % 12
    moon_9th_sign = (moon_sign_idx + 8) % 12
    
    lagna_9th_lord = SIGN_LORDS[lagna_9th_sign]
    moon_9th_lord = SIGN_LORDS[moon_9th_sign]
    
    total_kalas = INDU_KALAS[lagna_9th_lord] + INDU_KALAS[moon_9th_lord]
    rem = total_kalas % 12
    if rem == 0:
        rem = 12
        
    indu_sign_idx = (moon_sign_idx + rem - 1) % 12
    indu_house_from_lagna = ((indu_sign_idx - lagna_sign_idx) % 12) + 1
    
    planets_in_indu = [
        p for p, d in planet_positions.items() if d["d1_sign_index"] == indu_sign_idx
    ]
    
    return {
        "indu_lagna_sign": ZODIAC_SIGNS[indu_sign_idx],
        "indu_lagna_lord": SIGN_LORDS[indu_sign_idx],
        "house_from_d1_lagna": indu_house_from_lagna,
        "planets_in_indu_lagna": planets_in_indu
    }

def calculate_doshas(planet_positions, lagna_d1_idx, saturn_transit_idx=None):
    mars_house = planet_positions["Mars"]["d1_house"]
    is_manglik = mars_house in [1, 2, 4, 7, 8, 12]
    manglik_details = (
        f"मंगल लग्न कुंडली के भाव {mars_house} में स्थित है, जिससे मांगलिक प्रभाव निर्मित हो रहा है।"
        if is_manglik else
        f"मंगल लग्न कुंडली के भाव {mars_house} में स्थित है। कुंडली मांगलिक दोष से मुक्त है।"
    )

    rahu_deg = planet_positions["Rahu"]["absolute_degree"]
    other_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    side_1 = 0
    side_2 = 0
    for p in other_planets:
        p_deg = planet_positions[p]["absolute_degree"]
        diff = (p_deg - rahu_deg) % 360
        if diff < 180:
            side_1 += 1
        else:
            side_2 += 1
    is_kaal_sarp = (side_1 == 7 or side_2 == 7)
    kaal_sarp_details = (
        "सभी सात मुख्य ग्रह राहु और केतु के एक ही तरफ स्थित हैं, जिससे काल सर्प योग बन रहा है।"
        if is_kaal_sarp else
        "सभी ग्रह राहु-केतु अक्ष के एक ही तरफ बंद नहीं हैं, अतः पूर्ण काल सर्प दोष नहीं है।"
    )

    sun_house = planet_positions["Sun"]["d1_house"]
    rahu_house = planet_positions["Rahu"]["d1_house"]
    ketu_house = planet_positions["Ketu"]["d1_house"]
    saturn_house = planet_positions["Saturn"]["d1_house"]
    is_pitra = (sun_house == rahu_house) or (sun_house == ketu_house) or (rahu_house == 9) or (saturn_house == 9 and sun_house == 9)
    pitra_details = (
        "सूर्य/नवम भाव पर राहु-केतु या शनि के प्रभाव के कारण आंशिक पितृ दोष के संकेत हैं।"
        if is_pitra else
        "सूर्य और नवम भाव की स्थिति संतुलित है, कुंडली में कोई गंभीर पितृ दोष नहीं है।"
    )

    moon_idx = planet_positions["Moon"]["d1_sign_index"]
    moon_sign = planet_positions["Moon"]["d1_sign"]
    is_sade_sati = False
    sade_phase = ""
    if saturn_transit_idx is None:
        sade_sati_details = f"आपकी जन्म राशि {moon_sign} है। वर्तमान शनि गोचर की गणना उपलब्ध नहीं हो सकी।"
    else:
        transit_sign = ZODIAC_SIGNS[saturn_transit_idx]
        rel = (saturn_transit_idx - moon_idx) % 12   # 11 = चंद्र से 12वीं राशि, 0 = चंद्र राशि, 1 = चंद्र से 2री राशि
        today_str = datetime.now().strftime("%d-%m-%Y")
        base = f"आपकी जन्म राशि {moon_sign} है। आज ({today_str}) शनि {transit_sign} में गोचर कर रहे हैं।"
        if rel == 11:
            is_sade_sati, sade_phase = True, "पहला चरण"
            sade_sati_details = base + " शनि चंद्र राशि से 12वीं राशि में हैं, इसलिए साढ़े साती का पहला चरण चल रहा है।"
        elif rel == 0:
            is_sade_sati, sade_phase = True, "दूसरा चरण (मध्य)"
            sade_sati_details = base + " शनि आपकी जन्म राशि में ही हैं, इसलिए साढ़े साती का दूसरा (मध्य) चरण चल रहा है।"
        elif rel == 1:
            is_sade_sati, sade_phase = True, "तीसरा चरण"
            sade_sati_details = base + " शनि चंद्र राशि से दूसरी राशि में हैं, इसलिए साढ़े साती का अंतिम (तीसरा) चरण चल रहा है।"
        elif rel in (3, 7):
            sade_phase = "शनि ढैय्या"
            sade_sati_details = base + f" शनि चंद्र राशि से {'चौथी' if rel == 3 else 'आठवीं'} राशि में हैं, इसलिए शनि ढैय्या (छोटी पनौती) चल रही है। साढ़े साती नहीं है।"
        else:
            sade_sati_details = base + " इस समय साढ़े साती या शनि ढैय्या नहीं चल रही है।"

    return {
        "manglik": {"is_manglik": is_manglik, "details": manglik_details},
        "kaal_sarp": {"is_kaal_sarp": is_kaal_sarp, "details": kaal_sarp_details},
        "pitra_dosh": {"is_pitra": is_pitra, "details": pitra_details},
        "sade_sati": {"is_sade_sati": is_sade_sati, "phase": sade_phase, "details": sade_sati_details}
    }

def get_vedic_planets(year, month, day, hour, minute, city_name, tz_offset=5.5):
    lat, lon = 26.2345, 81.2409
    try:
        geolocator = Nominatim(user_agent="astropulse_india_engine", timeout=5)
        location = geolocator.geocode(city_name)
        if location:
            lat, lon = location.latitude, location.longitude
        else:
            for key, coords in FALLBACK_CITIES.items():
                if key in city_name.lower():
                    lat, lon = coords
                    break
    except Exception:
        for key, coords in FALLBACK_CITIES.items():
            if key in city_name.lower():
                lat, lon = coords
                break

    decimal_hour_local = hour + (minute / 60.0)
    decimal_hour_utc = decimal_hour_local - tz_offset
    jd = swe.julday(year, month, day, decimal_hour_utc)
    
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH

    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P', flags)
    
    lagna_d1_idx = int(ascmc[0] // 30) % 12
    lagna_d9_idx = int(ascmc[0] * 0.3) % 12
    lagna_d24_idx = get_d24_sign_index(ascmc[0])
    lagna_info = get_degree_info(ascmc[0])

    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
        "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE
    }
    planet_positions = {}
    moon_abs_deg = 0.0

    for name, planet_id in planets.items():
        calc_result, _ = swe.calc_ut(jd, planet_id, flags)
        deg = calc_result[0]
        if name == "Moon":
            moon_abs_deg = deg
        p_info = get_degree_info(deg)
        p_info["d1_house"] = ((p_info["d1_sign_index"] - lagna_d1_idx) % 12) + 1
        p_info["d9_house"] = ((p_info["d9_sign_index"] - lagna_d9_idx) % 12) + 1
        p_info["d24_house"] = ((p_info["d24_sign_index"] - lagna_d24_idx) % 12) + 1
        planet_positions[name] = p_info

    ketu_abs_deg = (planet_positions["Rahu"]["absolute_degree"] + 180) % 360
    k_info = get_degree_info(ketu_abs_deg)
    k_info["d1_house"] = ((k_info["d1_sign_index"] - lagna_d1_idx) % 12) + 1
    k_info["d9_house"] = ((k_info["d9_sign_index"] - lagna_d9_idx) % 12) + 1
    k_info["d24_house"] = ((k_info["d24_sign_index"] - lagna_d24_idx) % 12) + 1
    planet_positions["Ketu"] = k_info

    dasha_info = calculate_comprehensive_dasha(moon_abs_deg, year, month, day, hour, minute)

    houses = {str(i): {"sign": ZODIAC_SIGNS[(lagna_d1_idx + i - 1) % 12], "lord": SIGN_LORDS[(lagna_d1_idx + i - 1) % 12], "planets": []} for i in range(1, 13)}
    d9_houses = {str(i): {"sign": ZODIAC_SIGNS[(lagna_d9_idx + i - 1) % 12], "lord": SIGN_LORDS[(lagna_d9_idx + i - 1) % 12], "planets": []} for i in range(1, 13)}
    d24_houses = {str(i): {"sign": ZODIAC_SIGNS[(lagna_d24_idx + i - 1) % 12], "lord": SIGN_LORDS[(lagna_d24_idx + i - 1) % 12], "planets": []} for i in range(1, 13)}

    for planet_name, details in planet_positions.items():
        houses[str(details["d1_house"])]["planets"].append(planet_name)
        d9_houses[str(details["d9_house"])]["planets"].append(planet_name)
        d24_houses[str(details["d24_house"])]["planets"].append(planet_name)

    indu_info = calculate_indu_lagna(lagna_d1_idx, planet_positions["Moon"]["d1_sign_index"], planet_positions)
    try:
        _now = datetime.utcnow()
        _jd_now = swe.julday(_now.year, _now.month, _now.day, _now.hour + _now.minute / 60.0)
        _sat_now, _ = swe.calc_ut(_jd_now, swe.SATURN, flags)
        saturn_transit_idx = int(_sat_now[0] // 30) % 12
    except Exception:
        saturn_transit_idx = None
    doshas_info = calculate_doshas(planet_positions, lagna_d1_idx, saturn_transit_idx)

    return {
        "birth_details": {"city": city_name, "latitude": round(lat, 4), "longitude": round(lon, 4)},
        "lagna": lagna_info,
        "indu_lagna": indu_info,
        "planets": planet_positions,
        "houses": houses,
        "d9_houses": d9_houses,
        "d24_houses": d24_houses,
        "doshas": doshas_info,
        "dasha_timeline": dasha_info
    }