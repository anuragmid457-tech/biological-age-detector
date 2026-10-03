"""
The full Chronos questionnaire. Every field is optional.

This is the single source of truth: the frontend renders the form from it
(GET /api/questions) and detector_manual uses it to turn raw answers into
labelled, sectioned text for the model.

Field keys:
    key       stored name of the answer
    label     what the user sees
    type      "number", "select" or "text"
    unit      shown after the label and sent to the model
    min/max   soft hints for the input box; out-of-range values are still sent
              and the model is told to flag them
    options   choices for a select
    show_if   {"other_key": [allowed values]}: field is shown only then
    help      one line of guidance under the field
    start     number the up/down arrows begin from when the box is empty
    step      how much one arrow click changes the value (default 1)
"""

from __future__ import annotations

FEMALE = {"gender": ["Female"]}

FREQ = ["Never", "Rarely", "Sometimes", "Often", "Almost always"]

QUESTIONNAIRE = [
    {
        "id": "personal",
        "title": "Personal aspects",
        "fields": [
            {"key": "age", "start": 30, "label": "Age", "type": "number", "unit": "years", "min": 1, "max": 120,
             "help": "Your age in years. Everything else is compared against this."},
            {"key": "gender", "label": "Gender", "type": "select",
             "options": ["Male", "Female", "Other / prefer not to say"]},
            {"key": "ethnicity", "label": "Ethnicity", "type": "select",
             "options": ["South Asian", "East Asian", "Southeast Asian", "Middle Eastern or North African",
                         "Black or African", "White or European", "Hispanic or Latino",
                         "Pacific Islander", "Indigenous", "Mixed", "Other", "Prefer not to say"],
             "help": "Some risks differ between populations."},
            {"key": "height", "start": 165, "label": "Height", "type": "number", "unit": "cm", "min": 50, "max": 250},
            {"key": "weight", "start": 65, "label": "Weight", "type": "number", "unit": "kg", "min": 10, "max": 350},
            {"key": "family_longevity", "label": "How long did your grandparents live?", "type": "select",
             "options": ["Most lived past 85", "Most lived to between 70 and 85",
                         "Most died before 70", "I don't know"]},
            {"key": "education", "label": "Highest education", "type": "select",
             "options": ["No formal schooling", "Primary school", "Secondary school",
                         "Bachelor's degree or diploma", "Postgraduate degree"]},
            {"key": "sleep_hours", "start": 7, "step": 0.5, "label": "Sleep on a typical night", "type": "number",
             "unit": "hours", "min": 0, "max": 16},
            {"key": "sleep_quality", "label": "How well do you sleep?", "type": "select",
             "options": ["Well, I wake up rested", "Fairly well", "Poorly, I often wake up tired",
                         "Very poorly, diagnosed sleep problem"]},
        ],
    },
    {
        "id": "heart",
        "title": "Heart disease risk",
        "fields": [
            {"key": "total_cholesterol", "start": 180, "step": 5, "label": "Total cholesterol", "type": "number",
             "unit": "mg/dL", "min": 50, "max": 500},
            {"key": "hdl", "start": 50, "label": "HDL cholesterol", "type": "number", "unit": "mg/dL", "min": 5, "max": 150},
            {"key": "ldl", "start": 100, "step": 5, "label": "LDL cholesterol", "type": "number", "unit": "mg/dL", "min": 10, "max": 400},
            {"key": "triglycerides", "start": 150, "step": 5, "label": "Triglycerides", "type": "number", "unit": "mg/dL",
             "min": 20, "max": 2000},
            {"key": "systolic_bp", "start": 120, "label": "Blood pressure, upper number", "type": "number",
             "unit": "mmHg", "min": 60, "max": 260},
            {"key": "diastolic_bp", "start": 80, "label": "Blood pressure, lower number", "type": "number",
             "unit": "mmHg", "min": 30, "max": 160},
            {"key": "resting_heart_rate", "start": 70, "label": "Resting heart rate", "type": "number",
             "unit": "beats per minute", "min": 25, "max": 200},
            {"key": "smoking", "label": "Smoking", "type": "select",
             "options": ["Never smoked", "Quit more than 5 years ago", "Quit within the last 5 years",
                         "Fewer than 10 a day", "10 to 20 a day", "More than 20 a day"]},
            {"key": "smokeless_tobacco", "label": "Chewing tobacco, gutkha or similar", "type": "select",
             "options": ["Never", "Occasionally", "Daily"]},
            {"key": "family_heart", "label": "Heart disease in close family", "type": "select",
             "options": ["None that I know of", "A parent or sibling after age 60",
                         "A parent or sibling before age 60"]},
            {"key": "waist", "start": 85, "label": "Waist", "type": "number", "unit": "cm", "min": 30, "max": 250,
             "help": "Measured at the navel."},
            {"key": "hip", "start": 95, "label": "Hips", "type": "number", "unit": "cm", "min": 30, "max": 250,
             "help": "Measured at the widest point."},
            {"key": "stress", "label": "How often do you feel stressed?", "type": "select", "options": FREQ},
            {"key": "exercise_minutes", "start": 150, "step": 10, "label": "Exercise per week", "type": "number", "unit": "minutes",
             "min": 0, "max": 3000, "help": "Anything that raises your breathing: brisk walking counts."},
            {"key": "exercise_type", "label": "Main type of exercise", "type": "select",
             "options": ["None", "Walking", "Running, cycling or swimming", "Strength training",
                         "Yoga or stretching", "Sports", "A mix of these"]},
        ],
    },
    {
        "id": "medical",
        "title": "Medical aspects",
        "fields": [
            {"key": "checkups", "label": "Routine check-ups", "type": "select",
             "options": ["Every year", "Every 2 to 3 years", "Only when unwell", "Never"]},
            {"key": "heart_condition", "label": "Heart and circulation", "type": "select",
             "options": ["No diagnosed condition", "High blood pressure, treated",
                         "High blood pressure, untreated", "Past heart attack or angina",
                         "Other heart condition"]},
            {"key": "lung_condition", "label": "Lungs", "type": "select",
             "options": ["No diagnosed condition", "Asthma", "COPD or chronic bronchitis",
                         "Past tuberculosis", "Other lung condition"]},
            {"key": "digestion", "label": "Digestion", "type": "select",
             "options": ["No problems", "Occasional problems", "Ongoing diagnosed condition"]},
            {"key": "diabetes", "label": "Diabetes", "type": "select",
             "options": ["No", "Prediabetes", "Type 2, well controlled", "Type 2, poorly controlled",
                         "Type 1"]},
            {"key": "medications", "label": "Regular medicines", "type": "text",
             "help": "Names only, for example metformin or a blood pressure tablet."},
            {"key": "other_conditions", "label": "Other diagnosed conditions", "type": "text"},
            {"key": "cervical_screening", "label": "Last cervical screening (Pap smear)", "type": "select",
             "show_if": FEMALE,
             "options": ["Within 3 years", "More than 3 years ago", "Never", "Not applicable"]},
            {"key": "breast_screening", "label": "Last breast check or mammogram", "type": "select",
             "show_if": FEMALE,
             "options": ["Within 2 years", "More than 2 years ago", "Never", "Not applicable"]},
            {"key": "contraceptive_pill", "label": "Contraceptive pill", "type": "select",
             "show_if": FEMALE,
             "options": ["Never used", "Used in the past", "Currently using"]},
        ],
    },
    {
        "id": "biomarkers",
        "title": "Blood test results",
        "intro": "Copy these from a recent lab report if you have one. These are the values most "
                 "closely linked to biological age.",
        "fields": [
            {"key": "fasting_glucose", "start": 95, "label": "Fasting glucose", "type": "number", "unit": "mg/dL",
             "min": 30, "max": 600},
            {"key": "hba1c", "start": 5.5, "step": 0.1, "label": "HbA1c", "type": "number", "unit": "%", "min": 3, "max": 20},
            {"key": "crp", "start": 1, "step": 0.1, "label": "C-reactive protein (CRP)", "type": "number", "unit": "mg/L",
             "min": 0, "max": 300},
            {"key": "creatinine", "start": 0.9, "step": 0.1, "label": "Creatinine", "type": "number", "unit": "mg/dL",
             "min": 0.1, "max": 20},
            {"key": "albumin", "start": 4.2, "step": 0.1, "label": "Albumin", "type": "number", "unit": "g/dL", "min": 1, "max": 7},
            {"key": "alkaline_phosphatase", "start": 80, "label": "Alkaline phosphatase", "type": "number",
             "unit": "U/L", "min": 10, "max": 2000},
            {"key": "white_cell_count", "start": 6.5, "step": 0.1, "label": "White blood cell count", "type": "number",
             "unit": "thousand per microlitre", "min": 0.5, "max": 100},
            {"key": "lymphocyte_percent", "start": 30, "label": "Lymphocytes", "type": "number", "unit": "%",
             "min": 1, "max": 90},
            {"key": "mcv", "start": 90, "label": "Mean cell volume (MCV)", "type": "number", "unit": "fL",
             "min": 50, "max": 130},
            {"key": "rdw", "start": 13, "step": 0.1, "label": "Red cell distribution width (RDW)", "type": "number", "unit": "%",
             "min": 8, "max": 30},
            {"key": "haemoglobin", "start": 14, "step": 0.1, "label": "Haemoglobin", "type": "number", "unit": "g/dL",
             "min": 3, "max": 25},
            {"key": "vitamin_d", "start": 30, "label": "Vitamin D", "type": "number", "unit": "ng/mL", "min": 1, "max": 200},
        ],
    },
    {
        "id": "nutrition",
        "title": "Nutrition",
        "fields": [
            {"key": "breakfast", "label": "Breakfast", "type": "select",
             "options": ["Every day", "Most days", "Rarely"]},
            {"key": "meals", "label": "Meal pattern", "type": "select",
             "options": ["Regular meals at regular times", "Regular meals, irregular times",
                         "Often skip meals", "Mostly snacking"]},
            {"key": "fruit_veg_servings", "start": 3, "label": "Fruit and vegetables per day", "type": "number",
             "unit": "servings", "min": 0, "max": 20, "help": "One serving is roughly a handful."},
            {"key": "fried_food", "label": "Fried or oily food", "type": "select",
             "options": ["Rarely", "Once or twice a week", "Most days", "Every meal"]},
            {"key": "refined_food", "label": "Sweets, white bread, packaged snacks, sugary drinks",
             "type": "select", "options": ["Rarely", "Once or twice a week", "Most days", "Several times a day"]},
            {"key": "alcohol_drinks", "start": 0, "label": "Alcohol per week", "type": "number", "unit": "drinks",
             "min": 0, "max": 150, "help": "One drink is a small glass of wine, a beer or a single peg."},
        ],
    },
    {
        "id": "psychological",
        "title": "Psychological aspects",
        "fields": [
            {"key": "happiness", "label": "Overall, how happy are you?", "type": "select",
             "options": ["Very happy", "Fairly happy", "Not very happy", "Unhappy"]},
            # The last two options must match CONCERNING_MOOD in detector_manual.py exactly.
            {"key": "depression", "label": "Your mood lately", "type": "select",
             "options": ["I rarely feel down", "I feel down sometimes but it passes",
                         "I often feel down or depressed",
                         "Sometimes I think that life is not worth the struggle",
                         "I have had thoughts about suicide"]},
            {"key": "anxiety", "label": "How often do you feel anxious or on edge?", "type": "select",
             "options": FREQ},
            {"key": "relaxation", "label": "Time set aside to relax or for hobbies", "type": "select",
             "options": ["Every day", "A few times a week", "Rarely", "Never"]},
            {"key": "relationship", "label": "Close relationship", "type": "select",
             "options": ["In a supportive relationship", "In a relationship with frequent conflict",
                         "Not in a relationship, and content", "Not in a relationship, and lonely"]},
            {"key": "work_satisfaction", "label": "Satisfaction with work or daily occupation",
             "type": "select", "options": ["Satisfied", "Neutral", "Dissatisfied", "Not working"]},
            {"key": "social_life", "label": "Time with friends and family", "type": "select",
             "options": ["Several times a week", "About once a week", "A few times a month",
                         "Rarely or never"]},
        ],
    },
    {
        "id": "security",
        "title": "Safety and risk",
        "fields": [
            {"key": "driving_km", "start": 5000, "step": 500, "label": "Distance driven or ridden per year", "type": "number",
             "unit": "km", "min": 0, "max": 300000},
            {"key": "seat_belt", "label": "Seat belt in a car", "type": "select",
             "options": ["Always", "Usually", "Rarely", "I don't travel by car"]},
            {"key": "helmet", "label": "Helmet on a two-wheeler", "type": "select",
             "options": ["Always", "Usually", "Rarely", "I don't ride two-wheelers"]},
            {"key": "risk_taking", "label": "Risky activities (speeding, dangerous sports, etc.)",
             "type": "select", "options": ["Never", "Occasionally", "Often"]},
        ],
    },
]

FIELDS = {f["key"]: f for section in QUESTIONNAIRE for f in section["fields"]}

MAX_TEXT = 500


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_answers(raw: dict) -> dict:
    """Drop blanks, trim text, turn number fields into numbers. Unknown keys are kept (trimmed)."""
    answers = {}
    for key, value in list(raw.items())[:150]:
        if value is None or str(value).strip() == "":
            continue
        key = str(key)[:60]
        field = FIELDS.get(key)
        if field and field["type"] == "number":
            number = _to_float(value)
            answers[key] = number if number is not None else str(value).strip()[:MAX_TEXT]
        else:
            answers[key] = str(value).strip()[:MAX_TEXT]
    return answers


def _derived(answers: dict) -> list[str]:
    """Ratios the model would otherwise have to work out itself (and often gets wrong)."""
    lines = []
    h, w = _to_float(answers.get("height")), _to_float(answers.get("weight"))
    if h and w and h > 0:
        lines.append(f"Body mass index (calculated): {w / (h / 100) ** 2:.1f}")
    waist, hip = _to_float(answers.get("waist")), _to_float(answers.get("hip"))
    if waist and hip and hip > 0:
        lines.append(f"Waist to hip ratio (calculated): {waist / hip:.2f}")
    return lines


def describe_answers(answers: dict) -> str:
    """Labelled, sectioned text for the model. Only answered fields appear."""
    blocks = []
    used = set()
    for section in QUESTIONNAIRE:
        lines = []
        for field in section["fields"]:
            if field["key"] in answers:
                used.add(field["key"])
                unit = f" ({field['unit']})" if field.get("unit") else ""
                value = answers[field["key"]]
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                lines.append(f"{field['label']}{unit}: {value}")
        if lines:
            blocks.append(f"[{section['title']}]\n" + "\n".join(lines))

    derived = _derived(answers)
    if derived:
        blocks.append("[Calculated]\n" + "\n".join(derived))

    extra = [f"{k}: {v}" for k, v in answers.items() if k not in used]
    if extra:
        blocks.append("[Other details]\n" + "\n".join(extra))

    return "\n\n".join(blocks)