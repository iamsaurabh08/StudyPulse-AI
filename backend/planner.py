import os
import json
import math
import requests
from datetime import datetime, date, timedelta

STUDY_TECHNIQUES = [
    "Feynman Technique (Explain concepts simply to test understanding)",
    "Active Recall & Closed-Book Flashcards",
    "Pomodoro 50/10 (50 mins focused study, 10 mins break)",
    "Past Exam Paper Problem Solving & Time Trials",
    "Blurting Method (Write down everything from memory, then fill gaps)",
    "Mind Mapping & Formula Sheet Synthesis"
]

def parse_flexible_date(date_val):
    """
    Parses date strings in various formats (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, etc.)
    Returns a datetime.date object or raises ValueError if invalid.
    """
    if not date_val:
        return None
    if isinstance(date_val, (date, datetime)):
        return date_val if isinstance(date_val, date) else date_val.date()
    
    s = str(date_val).strip()
    if not s:
        return None

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%d %b %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: '{s}'. Expected YYYY-MM-DD or DD-MM-YYYY.")


def validate_planner_inputs(subjects, daily_hours=4.0, days_count=7, start_date_str=None):
    """
    Validates all inputs for study planner:
    - Subject names, difficulties (1-5), exam dates
    - Checks that exam dates are NOT before start_date
    - Validates daily hours (0.5 to 16.0) and schedule duration (1 to 60 days)
    Returns sanitized parameters: (valid_subjects, valid_daily_hours, valid_days_count, valid_start_date)
    """
    if not subjects or not isinstance(subjects, list) or len(subjects) == 0:
        raise ValueError("Please provide at least one subject to generate a study timetable.")

    # 1. Start Date Validation
    today = date.today()
    if start_date_str:
        try:
            start_date = parse_flexible_date(start_date_str)
        except ValueError as e:
            raise ValueError(f"Invalid schedule start date: {str(e)}")
    else:
        start_date = today

    # 2. Daily Hours Validation
    try:
        daily_hours = float(daily_hours)
        if daily_hours < 0.5 or daily_hours > 16.0:
            raise ValueError()
    except Exception:
        raise ValueError("Daily study availability must be a number between 0.5 and 16.0 hours.")

    # 3. Days Count Validation
    try:
        days_count = int(days_count)
        if days_count < 1 or days_count > 60:
            raise ValueError()
    except Exception:
        raise ValueError("Schedule duration must be an integer between 1 and 60 days.")

    # 4. Subjects Validation
    valid_subjects = []
    for idx, subj in enumerate(subjects):
        if not isinstance(subj, dict):
            raise ValueError(f"Subject #{idx + 1} is invalid.")

        name = (subj.get("name") or "").strip()
        if not name:
            raise ValueError(f"Subject #{idx + 1} is missing a name. Please enter a valid subject name.")

        # Difficulty: 1 to 5
        try:
            diff = int(subj.get("difficulty", 3))
            if diff < 1 or diff > 5:
                diff = max(1, min(5, diff))
        except Exception:
            raise ValueError(f"Difficulty for '{name}' must be an integer between 1 (Very Easy) and 5 (Very Hard).")

        # Exam Date Validation
        exam_date_str = subj.get("exam_date")
        exam_date = None
        if exam_date_str and str(exam_date_str).strip():
            try:
                exam_date = parse_flexible_date(exam_date_str)
            except ValueError as e:
                raise ValueError(f"Invalid exam date for '{name}': {str(e)}")

            # Check if exam date is in the past relative to schedule start date
            if exam_date < start_date:
                days_past = (start_date - exam_date).days
                raise ValueError(
                    f"Exam date for '{name}' ({exam_date.strftime('%d-%m-%Y')}) cannot be in the past relative to the schedule start date ({start_date.strftime('%d-%m-%Y')}). "
                    f"It is already {days_past} day{'s' if days_past != 1 else ''} in the past. Please select an exam date on or after {start_date.strftime('%d-%m-%Y')}."
                )

        raw_topics = subj.get("topics", "")
        if isinstance(raw_topics, list):
            topics_list = [t.strip() for t in raw_topics if t.strip()]
        elif isinstance(raw_topics, str) and raw_topics.strip():
            topics_list = [t.strip() for t in raw_topics.replace("\n", ",").split(",") if t.strip()]
        else:
            topics_list = [f"{name} Core Concepts & Key Formulas"]

        valid_subjects.append({
            "name": name,
            "difficulty": diff,
            "exam_date": exam_date.isoformat() if exam_date else None,
            "exam_date_obj": exam_date,
            "topics": topics_list
        })

    return valid_subjects, daily_hours, days_count, start_date


def generate_rule_based_schedule(subjects, daily_hours=4.0, days_count=7, start_date_str=None):
    """
    Deterministically computes a weighted study timetable based on:
    1. Subject difficulty (1-5 scale)
    2. Exam proximity (urgency weight)
    3. Daily available hours
    """
    valid_subjects, daily_hours, days_count, start_date = validate_planner_inputs(
        subjects=subjects,
        daily_hours=daily_hours,
        days_count=days_count,
        start_date_str=start_date_str
    )

    weighted_subjects = []
    total_weight = 0.0

    for subj in valid_subjects:
        name = subj["name"]
        difficulty = subj["difficulty"]
        ex_date = subj["exam_date_obj"]

        if ex_date:
            delta = (ex_date - start_date).days
            days_to_exam = max(0, delta)
        else:
            days_to_exam = 30 # Default if no specific exam date

        # Urgency multiplier based on days remaining
        if days_to_exam == 0:
            urgency_score = 5.0
            urgency_label = "Exam Today! (Immediate Final Revision)"
        elif days_to_exam <= 2:
            urgency_score = 4.5
            urgency_label = "Imminent Exam (< 48 hrs)"
        elif days_to_exam <= 5:
            urgency_score = 3.5
            urgency_label = "High Urgency (Under 5 days)"
        elif days_to_exam <= 10:
            urgency_score = 2.5
            urgency_label = "Medium Urgency (Under 10 days)"
        elif days_to_exam <= 20:
            urgency_score = 1.8
            urgency_label = "Moderate (10-20 days)"
        else:
            urgency_score = 1.2
            urgency_label = "Long-Term Preparation (> 20 days)"

        # Combined weight: Difficulty (1.5x) + Urgency (2.0x)
        subj_weight = (difficulty * 1.5) + (urgency_score * 2.0)
        total_weight += subj_weight

        weighted_subjects.append({
            "name": name,
            "difficulty": difficulty,
            "days_to_exam": days_to_exam,
            "urgency_score": urgency_score,
            "urgency_label": urgency_label,
            "weight": subj_weight,
            "topics": subj["topics"]
        })

    # Compute daily time allocation per subject
    for s in weighted_subjects:
        ratio = s["weight"] / total_weight if total_weight > 0 else (1.0 / len(weighted_subjects))
        allocated = max(0.5, round(ratio * daily_hours, 1))
        s["allocated_hours_per_day"] = allocated

    # Sort descending by priority weight
    weighted_subjects.sort(key=lambda x: x["weight"], reverse=True)

    # Generate day-by-day timetable
    daily_schedule = []
    technique_idx = 0

    for day_offset in range(days_count):
        current_day_date = start_date + timedelta(days=day_offset)
        day_name = current_day_date.strftime("%A")
        date_formatted = current_day_date.strftime("%b %d, %Y")

        day_slots = []
        rotation_offset = day_offset % len(weighted_subjects)
        ordered_for_day = weighted_subjects[rotation_offset:] + weighted_subjects[:rotation_offset]

        slot_hours_pool = daily_hours
        slot_number = 1

        for subj in ordered_for_day:
            if slot_hours_pool <= 0.2:
                break

            target_slot_hours = min(subj["allocated_hours_per_day"], slot_hours_pool)
            target_slot_hours = max(0.5, round(target_slot_hours, 1))
            slot_hours_pool -= target_slot_hours

            topics = subj["topics"]
            topic_for_slot = topics[(day_offset + slot_number - 1) % len(topics)]

            remaining_to_exam = subj["days_to_exam"] - day_offset
            if remaining_to_exam <= 1:
                phase = "Final Mock Exams & High-Yield Formula Review"
            elif remaining_to_exam <= 4:
                phase = "Intensive Practice Questions & Weakness Elimination"
            else:
                phase = "Concept Deep-Dive & Structured Problem Solving"

            tech = STUDY_TECHNIQUES[technique_idx % len(STUDY_TECHNIQUES)]
            technique_idx += 1

            day_slots.append({
                "session_number": slot_number,
                "subject": subj["name"],
                "duration_hours": target_slot_hours,
                "duration_minutes": int(target_slot_hours * 60),
                "topic": topic_for_slot,
                "phase": phase,
                "difficulty": subj["difficulty"],
                "urgency_label": subj["urgency_label"],
                "technique": tech,
                "break_after_minutes": 15 if target_slot_hours >= 1.5 else 10
            })
            slot_number += 1

        daily_schedule.append({
            "day_number": day_offset + 1,
            "day_name": day_name,
            "date": date_formatted,
            "iso_date": current_day_date.isoformat(),
            "total_hours": round(sum(slot["duration_hours"] for slot in day_slots), 1),
            "sessions": day_slots
        })

    top_subject = weighted_subjects[0]["name"]
    top_reason = f"highest priority ({weighted_subjects[0]['difficulty']}/5 difficulty, {weighted_subjects[0]['days_to_exam']} days to exam)"
    summary = (
        f"Calculated a {days_count}-day schedule balancing {daily_hours} hours/day across {len(valid_subjects)} subjects. "
        f"Allocated the largest focus blocks to {top_subject} due to {top_reason}. "
        f"Each session incorporates active learning techniques and structured breaks to maximize retention."
    )

    return {
        "success": True,
        "generated_by": "Rule-Based Heuristic Algorithm",
        "model_used": "Deterministic Priority & Urgency Balancer",
        "is_ai": False,
        "summary": summary,
        "total_days": days_count,
        "daily_study_hours": daily_hours,
        "subject_weights": [
            {
                "name": s["name"],
                "difficulty": s["difficulty"],
                "days_to_exam": s["days_to_exam"],
                "urgency_label": s["urgency_label"],
                "weight_score": round(s["weight"], 2),
                "target_hours_per_day": s["allocated_hours_per_day"]
            }
            for s in weighted_subjects
        ],
        "daily_schedule": daily_schedule
    }


def generate_study_schedule(subjects, daily_hours=4.0, days_count=7, start_date_str=None, force_rule_based=False):
    """
    Master generator function:
    1. Validates all inputs (subject difficulty, exam dates vs start date, hours, duration).
    2. If force_rule_based is True or OPENROUTER_API_KEY is not configured, uses the Rule-Based engine.
    3. If OPENROUTER_API_KEY is present, attempts AI generation via OpenRouter.
    4. On any AI failure (timeout, network error, 429 rate limit, parsing error),
       automatically falls back to the Rule-Based engine with clear indicators.
    """
    valid_subjects, daily_hours, days_count, start_date = validate_planner_inputs(
        subjects=subjects,
        daily_hours=daily_hours,
        days_count=days_count,
        start_date_str=start_date_str
    )

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:free")

    # If no API key or explicitly requested rule-based, run heuristic engine directly
    if force_rule_based or not api_key or not api_key.strip():
        result = generate_rule_based_schedule(valid_subjects, daily_hours, days_count, start_date.isoformat())
        result["ai_status"] = "Rule-based engine active (No OPENROUTER_API_KEY detected in environment)."
        return result

    # Attempt AI generation via OpenRouter
    prompt_payload = {
        "subjects": valid_subjects,
        "daily_hours": daily_hours,
        "days_count": days_count,
        "start_date": start_date.isoformat()
    }

    system_prompt = (
        "You are an expert academic counselor. Generate an optimal study timetable in raw JSON only. "
        "Allocate more hours to subjects with higher difficulty and nearer exam dates. "
        "Do NOT include markdown formatting or code blocks."
    )

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("SITE_URL", "https://studypulse-ai.app"),
        "X-Title": "AI Study Planner"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate study schedule: {json.dumps(prompt_payload)}"}
        ],
        "temperature": 0.4,
        "max_tokens": 3000
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        
        if response.status_code == 200:
            res_json = response.json()
            raw_content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            clean_text = raw_content.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            parsed = json.loads(clean_text)
            parsed["success"] = True
            parsed["generated_by"] = "AI-Generated Schedule"
            parsed["model_used"] = model
            parsed["is_ai"] = True
            parsed["ai_status"] = f"Successfully generated using OpenRouter AI ({model})."
            return parsed
        else:
            fallback = generate_rule_based_schedule(valid_subjects, daily_hours, days_count, start_date.isoformat())
            fallback["ai_status"] = f"OpenRouter API returned HTTP {response.status_code}. Automatically fell back to Rule-Based Heuristic engine."
            fallback["fallback_triggered"] = True
            return fallback

    except Exception as e:
        # Graceful fallback on connection/timeout/parsing error
        fallback = generate_rule_based_schedule(valid_subjects, daily_hours, days_count, start_date.isoformat())
        fallback["ai_status"] = f"AI request failed ({str(e)}). Automatically fell back to Rule-Based Heuristic engine."
        fallback["fallback_triggered"] = True
        return fallback
