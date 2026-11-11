"""Type/severity/injury labels and fixed phrases in en/es/ur (mirrors frontend i18n keys)."""

LANGS = ("en", "es", "ur")

INCIDENT_TYPE = {
    "attack_shooting": {
        "en": "Shooting / attack",
        "es": "Tiroteo / ataque",
        "ur": "فائرنگ / حملہ",
    },
    "explosion": {"en": "Explosion", "es": "Explosión", "ur": "دھماکہ"},
    "fire": {"en": "Fire", "es": "Incendio", "ur": "آگ"},
    "road_accident": {
        "en": "Road accident",
        "es": "Accidente de tráfico",
        "ur": "سڑک کا حادثہ",
    },
    "building_collapse": {
        "en": "Building collapse",
        "es": "Derrumbe",
        "ur": "عمارت گرنا",
    },
    "medical": {
        "en": "Medical emergency",
        "es": "Emergencia médica",
        "ur": "طبی ایمرجنسی",
    },
    "riot_crowd": {
        "en": "Crowd / riot",
        "es": "Multitud / disturbio",
        "ur": "بھگدڑ / ہنگامہ",
    },
    "flood": {"en": "Flood", "es": "Inundación", "ur": "سیلاب"},
    "other": {"en": "Emergency", "es": "Emergencia", "ur": "ہنگامی صورتحال"},
}

SEVERITY = {
    "low": {"en": "LOW", "es": "BAJA", "ur": "کم"},
    "medium": {"en": "MEDIUM", "es": "MEDIA", "ur": "درمیانی"},
    "high": {"en": "HIGH", "es": "ALTA", "ur": "زیادہ"},
    "critical": {"en": "CRITICAL", "es": "CRÍTICA", "ur": "انتہائی شدید"},
}

INJURY = {
    "gunshot": {"en": "gunshot", "es": "herida de bala", "ur": "گولی کا زخم"},
    "blast_shrapnel": {
        "en": "blast injuries",
        "es": "heridas por explosión",
        "ur": "دھماکے کے زخم",
    },
    "burns": {"en": "burns", "es": "quemaduras", "ur": "جلنا"},
    "fracture": {"en": "fractures", "es": "fracturas", "ur": "ہڈی ٹوٹنا"},
    "head_injury": {
        "en": "head injury",
        "es": "lesión en la cabeza",
        "ur": "سر کی چوٹ",
    },
    "bleeding": {"en": "bleeding", "es": "hemorragia", "ur": "خون بہنا"},
    "crush": {"en": "crush injuries", "es": "aplastamiento", "ur": "دبنے کی چوٹیں"},
    "smoke_inhalation": {
        "en": "smoke inhalation",
        "es": "inhalación de humo",
        "ur": "دھوئیں کا اثر",
    },
    "drowning": {"en": "drowning", "es": "ahogamiento", "ur": "ڈوبنا"},
    "cardiac": {"en": "cardiac", "es": "cardíaco", "ur": "دل کا مسئلہ"},
    "unconscious": {"en": "unconscious", "es": "inconsciente", "ur": "بے ہوش"},
    "breathing_difficulty": {
        "en": "breathing difficulty",
        "es": "dificultad para respirar",
        "ur": "سانس کی تکلیف",
    },
    "unknown": {"en": "unknown", "es": "desconocido", "ur": "نامعلوم"},
}

# Fixed phrases used by messages.py (docs/07_AI_AGENTS.md §11), one entry per language.
PHRASE = {
    "casualties": {"en": "Casualties", "es": "Víctimas", "ur": "زخمی"},
    "injuries": {"en": "Injuries", "es": "Lesiones", "ur": "زخموں کی نوعیت"},
    "map": {"en": "Map", "es": "Mapa", "ur": "نقشہ"},
    "danger": {
        "en": "⚠ Danger may be ongoing",
        "es": "⚠ El peligro puede continuar",
        "ur": "⚠ خطرہ ابھی جاری ہو سکتا ہے",
    },
    "silent": {
        "en": "⚠ SILENT REPORT – DO NOT CALL REPORTER",
        "es": "⚠ REPORTE SILENCIOSO – NO LLAME AL REPORTERO",
        "ur": "⚠ خاموش رپورٹ – رپورٹر کو کال نہ کریں",
    },
    "press_ack": {
        "en": "Press ✅ to confirm you are responding.",
        "es": "Pulse ✅ para confirmar que está respondiendo.",
        "ur": "جواب دے رہے ہیں تو ✅ دبائیں۔",
    },
    "press_ack_er": {
        "en": "Press ✅ to confirm your ER is preparing.",
        "es": "Pulse ✅ para confirmar que su urgencias se prepara.",
        "ur": "ایمرجنسی تیار ہے تو ✅ دبائیں۔",
    },
    "unverified": {
        "en": "❓ UNVERIFIED – {n} report(s), confidence {pct}%",
        "es": "❓ SIN VERIFICAR – {n} reporte(s), confianza {pct}%",
        "ur": "❓ غیر تصدیق شدہ – {n} رپورٹ، اعتماد {pct}%",
    },
    "pre_arrival": {
        "en": "PRE-ARRIVAL",
        "es": "PRE-LLEGADA",
        "ur": "مریضوں کی آمد سے پہلے",
    },
    "standby": {
        "en": "STANDBY (UNVERIFIED)",
        "es": "EN ESPERA (SIN VERIFICAR)",
        "ur": "تیار رہیں (غیر تصدیق شدہ)",
    },
    "standby_note": {
        "en": "Prepare, but do not activate your mass-casualty plan yet.",
        "es": "Prepárese, pero aún no active su plan de víctimas masivas.",
        "ur": "تیاری کریں، مگر ابھی بڑے حادثے کا منصوبہ نہ چلائیں۔",
    },
    "expect": {
        "en": "Expect {n} patient(s): {c} critical, {m} minor",
        "es": "Espere {n} paciente(s): {c} críticos, {m} leves",
        "ur": "{n} مریض متوقع: {c} نازک، {m} معمولی",
    },
    "likely": {"en": "Likely injuries", "es": "Lesiones probables", "ur": "ممکنہ زخم"},
    "eta": {
        "en": "First ambulance ETA: ~{n} min",
        "es": "Primera ambulancia: ~{n} min",
        "ur": "پہلی ایمبولینس: تقریباً {n} منٹ",
    },
    "at": {"en": "at", "es": "en", "ur": "مقام:"},
}


def label(table: dict, key: str, lang: str) -> str:
    entry = table.get(key) or table.get("other") or {}
    return entry.get(lang) or entry.get("en") or key


def phrase(key: str, lang: str, **kw) -> str:
    text = PHRASE[key].get(lang) or PHRASE[key]["en"]
    return text.format(**kw) if kw else text


# Fixed calm phrases for the Voice Coach (docs/07_AI_AGENTS.md section 11). Used by the rules
# autopilot and whenever an agent ack fails validation.
COACH_ACK = {
    "next": {
        "en": "Okay. Next step.",
        "es": "Bien. Siguiente paso.",
        "ur": "ٹھیک ہے۔ اگلا قدم۔",
    },
    "repeat": {
        "en": "I will say it again.",
        "es": "Lo repito.",
        "ur": "میں دوبارہ بتاتا ہوں۔",
    },
    "previous": {
        "en": "Going back one step.",
        "es": "Un paso atrás.",
        "ur": "ایک قدم پیچھے۔",
    },
    "switch_card": {
        "en": "Okay, stay with me. I will tell you what to do.",
        "es": "Bien, quédese conmigo. Le diré qué hacer.",
        "ur": "ٹھیک ہے، میرے ساتھ رہیں۔ میں بتاتا ہوں کیا کرنا ہے۔",
    },
    "call_help": {
        "en": "Press the call button now.",
        "es": "Pulse el botón de llamada ahora.",
        "ur": "ابھی کال کا بٹن دبائیں۔",
    },
    "done": {
        "en": "Good. Stay with the person until help takes over.",
        "es": "Bien. Quédese con la persona hasta que llegue la ayuda.",
        "ur": "اچھا۔ مدد پہنچنے تک ان کے ساتھ رہیں۔",
    },
    "unclear": {
        "en": "I could not hear that well. Please say it again, simply.",
        "es": "No le oí bien. Por favor repítalo con palabras simples.",
        "ur": "میں ٹھیک سے سن نہیں سکا۔ براہ کرم آسان لفظوں میں دوبارہ بتائیں۔",
    },
}


def coach_ack(intent: str, lang: str) -> str:
    return COACH_ACK[intent].get(lang) or COACH_ACK[intent]["en"]
