import os
import sys
import json
import random

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, redirect
import requests
from flask_cors import CORS

from backend.database import (
    init_db,
    DB_PATH,
    get_profile,
    update_profile,
    get_tasks,
    get_task_by_id,
    create_task,
    update_task,
    toggle_task_completed,
    delete_task,
    save_study_schedule,
    get_active_study_schedule,
    get_schedule_history,
    get_analytics_summary
)
from backend.planner import generate_study_schedule, generate_rule_based_schedule

# Load environment variables from parent or current directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:free")

# Configure frontend directory robustly
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from werkzeug.routing import PathConverter

class NonApiPathConverter(PathConverter):
    regex = r'(?!api/).+'

app = Flask(__name__, static_folder=None)
app.url_map.converters['non_api_path'] = NonApiPathConverter

# Enable CORS for all origins and headers
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"]
)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    return response

# Initialize SQLite database and seed defaults if empty
init_db()

# ----------------------------------------------------
#  ROOT & STATUS API
# ----------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/api/status', methods=['GET', 'OPTIONS'], strict_slashes=False)
def system_status():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    has_key = bool(OPENROUTER_API_KEY and OPENROUTER_API_KEY.strip())
    return jsonify({
        "status": "operational",
        "api_key_configured": has_key,
        "ai_model": OPENROUTER_MODEL,
        "planner_mode": "Hybrid (AI with Automatic Rule-Based Fallback)" if has_key else "Rule-Based Heuristic Engine",
        "database": "SQLite (Local Persistent Storage)"
    })


# ----------------------------------------------------
#  STUDENT PROFILE API
# ----------------------------------------------------
@app.route('/api/profile', methods=['GET', 'POST', 'PUT', 'OPTIONS'], strict_slashes=False)
def profile_endpoint():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        profile = get_profile()
        return jsonify(profile or {})

    # POST or PUT updates profile
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Profile data is required."}), 400

        updated = update_profile(data)
        return jsonify({"message": "Profile updated successfully", "profile": updated})
    except Exception as e:
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500


# ----------------------------------------------------
#  TASK MANAGEMENT API (CRUD)
# ----------------------------------------------------
@app.route('/api/tasks', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def tasks_collection():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        status = request.args.get('status') # 'pending', 'completed', or None
        subject = request.args.get('subject')
        search = request.args.get('search')
        tasks = get_tasks(filter_status=status, subject=subject, search=search)
        return jsonify(tasks)

    # POST: Create Task
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Task data required."}), 400

        task = create_task(data)
        return jsonify({"message": "Task created successfully", "task": task}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create task: {str(e)}"}), 500


@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'], strict_slashes=False)
def task_single(task_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if request.method == 'GET':
        task = get_task_by_id(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task)

    elif request.method == 'PUT':
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Update data required."}), 400
            updated = update_task(task_id, data)
            if not updated:
                return jsonify({"error": "Task not found"}), 404
            return jsonify({"message": "Task updated successfully", "task": updated})
        except Exception as e:
            return jsonify({"error": f"Failed to update task: {str(e)}"}), 500

    elif request.method == 'DELETE':
        success = delete_task(task_id)
        if not success:
            return jsonify({"error": "Task not found"}), 404
        return jsonify({"message": "Task deleted successfully", "id": task_id})


@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST', 'PATCH', 'PUT', 'OPTIONS'], strict_slashes=False)
def task_toggle(task_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    updated = toggle_task_completed(task_id)
    if not updated:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({
        "message": f"Task marked as {'completed' if updated['completed'] else 'pending'}",
        "task": updated
    })


# ----------------------------------------------------
#  PROGRESS & ANALYTICS API
# ----------------------------------------------------
@app.route('/api/analytics/progress', methods=['GET', 'OPTIONS'], strict_slashes=False)
def analytics_progress():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        summary = get_analytics_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": f"Failed to calculate progress analytics: {str(e)}"}), 500


# ----------------------------------------------------
#  AI & RULE-BASED STUDY PLANNER API
# ----------------------------------------------------
@app.route('/api/planner/generate', methods=['POST', 'OPTIONS'], strict_slashes=False)
def planner_generate():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.get_json(silent=True) or {}
        subjects = data.get('subjects', [])
        daily_hours = data.get('daily_hours', 4.0)
        days_count = data.get('days_count', 7)
        start_date = data.get('start_date')
        force_rule_based = bool(data.get('force_rule_based', False))
        plan_name = (data.get('plan_name') or f"Study Plan - {datetime.now().strftime('%b %d, %Y')}").strip()

        if not subjects or not isinstance(subjects, list) or len(subjects) == 0:
            return jsonify({"error": "Please provide at least one subject to generate a study timetable."}), 400

        result = generate_study_schedule(
            subjects=subjects,
            daily_hours=daily_hours,
            days_count=days_count,
            start_date_str=start_date,
            force_rule_based=force_rule_based
        )

        if not result.get("success"):
            return jsonify({"error": result.get("error", "Failed to generate schedule")}), 400

        # Persist schedule to SQLite
        saved = save_study_schedule(
            plan_name=plan_name,
            generated_by=result.get("generated_by", "Rule-Based"),
            parameters={
                "subjects": subjects,
                "daily_hours": daily_hours,
                "days_count": days_count,
                "start_date": start_date
            },
            schedule_data=result
        )

        if saved:
            result["id"] = saved.get("id")
            result["saved_at"] = saved.get("created_at")

        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to generate study timetable: {str(e)}"}), 500


@app.route('/api/planner/active', methods=['GET', 'OPTIONS'], strict_slashes=False)
def planner_active():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        active = get_active_study_schedule()
        if not active:
            # If no active schedule in DB, generate default rule-based schedule from profile subjects
            prof = get_profile()
            subjects = [{"name": s, "difficulty": 3, "exam_date": (date.today() + timedelta(days=14)).isoformat()} for s in (prof.get('subjects') or ['Mathematics', 'Computer Science'])]
            result = generate_rule_based_schedule(subjects, daily_hours=prof.get('daily_study_hours', 4.0), days_count=7)
            saved = save_study_schedule(
                plan_name="Default Semester Study Plan",
                generated_by="Rule-Based Heuristic Algorithm",
                parameters={"subjects": subjects, "daily_hours": 4.0, "days_count": 7},
                schedule_data=result
            )
            return jsonify(saved)
        return jsonify(active)
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve active schedule: {str(e)}"}), 500


@app.route('/api/planner/history', methods=['GET', 'OPTIONS'], strict_slashes=False)
def planner_history():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        history = get_schedule_history()
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": f"Failed to load schedule history: {str(e)}"}), 500


# ----------------------------------------------------
#  ORIGINAL FEATURE: AI ASSISTANT API (Preserved & Enhanced)
# ----------------------------------------------------
@app.route('/api/assistant', methods=['POST', 'OPTIONS'], strict_slashes=False)
def assistant():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get('prompt', '').strip()
        length_hint = float(data.get('length_hint', 1.0))

        if not prompt:
            return jsonify({"error": "Prompt required"}), 400

        # If no API key configured, provide a helpful intelligent rule-based study coach response
        if not OPENROUTER_API_KEY or not OPENROUTER_API_KEY.strip():
            study_tips = [
                "Tip: Break difficult topics into 25-minute Pomodoro sessions with 5-minute active recall breaks.",
                "Tip: Explain concepts aloud without looking at your notes using the Feynman Technique.",
                "Tip: Solve past exam questions under timed conditions to eliminate exam anxiety.",
                "Tip: Prioritize subjects with exams in the next 5 days before tackling long-term revisions."
            ]
            advice = (
                f"I am running in offline Study Coach mode (no OPENROUTER_API_KEY configured). "
                f"Here is academic guidance regarding your query '{prompt}':\n\n"
                f"1. Break your learning objectives into bite-sized milestones.\n"
                f"2. Use Active Recall and spaced repetition rather than passive reading.\n"
                f"3. {random.choice(study_tips)}\n\n"
                f"To enable generative AI responses, add OPENROUTER_API_KEY to your .env file."
            )
            return jsonify({
                "text": advice,
                "model_used": "Local Academic Coach (Rule-Based Fallback)",
                "is_fallback": True
            })

        base_tokens = 500
        if length_hint <= 0.5:
            max_tokens = int(base_tokens * 0.5)
        elif length_hint >= 1.5:
            max_tokens = int(base_tokens * 2)
        else:
            max_tokens = base_tokens

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("SITE_URL", "https://studypulse-ai.app"),
            "X-Title": "Study Planner AI"
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful, encouraging, and concise study assistant for university students."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 429:
            return jsonify({
                "error": "API rate limit exceeded.",
                "retry_after": response.headers.get('Retry-After', '60')
            }), 429

        response.raise_for_status()

        result = response.json()
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "No response received")

        return jsonify({"text": text, "model_used": OPENROUTER_MODEL, "is_fallback": False})

    except requests.RequestException as e:
        return jsonify({"error": f"AI Assistant API request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


# ----------------------------------------------------
#  ORIGINAL FEATURE: MUSIC API WITH SPOTIFY + YOUTUBE (Preserved)
# ----------------------------------------------------
@app.route('/api/music-suggest', methods=['POST', 'OPTIONS'], strict_slashes=False)
def music_suggest():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        data = request.get_json(silent=True) or {}
        mood = data.get('mood', 'calm').lower()
        language = data.get('language', 'english').lower()
        ptype = data.get('ptype', 'lofi').lower()

        playlists = {
            "focused": {
                "english": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/jfKfPfyJRdk?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX8Uebhn9wzrS",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX8Uebhn9wzrS"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/y6120QOlsfU?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX4UtSsGT1Sbe",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX4UtSsGT1Sbe"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/5yx6BWlEVcY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DWZd79rJ6a7lp",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DWZd79rJ6a7lp"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/36YnV9STBqc?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX4o1oenSJRJd",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX4o1oenSJRJd"
                    }
                },
                "tamil": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/MGQ5m0QdCjE?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/1E1j2PbaSW1byDCxtaiGlg",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/1E1j2PbaSW1byDCxtaiGlg"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/r00ikilDxW4?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DXaVmfUr97Uve",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DXaVmfUr97Uve"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/HpEi0lrpLDo?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/4zzmGEbnAkLZRiVO9b9eGO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/4zzmGEbnAkLZRiVO9b9eGO"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/1q8gp2AB6VY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/43a73ssTnlw00K8ljXDEfO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/43a73ssTnlw00K8ljXDEfO"
                    }
                }
            },
            "calm": {
                "english": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/5yx6BWlEVcY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/1DWuFSxuyo6xjLsanCwGTC",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/1DWuFSxuyo6xjLsanCwGTC"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/EkHTsc9PU2A?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX3rxVfibe1L0",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX3rxVfibe1L0"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/1ZYbU82GVz4?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DWXmlLSKkfdAk",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DWXmlLSKkfdAk"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/2OEL4P1Rz04?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX6VdMW310YC7",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX6VdMW310YC7"
                    }
                },
                "tamil": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/MGQ5m0QdCjE?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/1E1j2PbaSW1byDCxtaiGlg",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/1E1j2PbaSW1byDCxtaiGlg"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/r00ikilDxW4?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DXaVmfUr97Uve",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DXaVmfUr97Uve"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/HpEi0lrpLDo?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/4zzmGEbnAkLZRiVO9b9eGO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/4zzmGEbnAkLZRiVO9b9eGO"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/1q8gp2AB6VY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/43a73ssTnlw00K8ljXDEfO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/43a73ssTnlw00K8ljXDEfO"
                    }
                }
            },
            "energetic": {
                "english": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/hi4pzKvuEQM?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX76Wlfdnj7AP",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX76Wlfdnj7AP"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/kXYiU_JCYtU?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DXcWBRiUaG3o5",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DXcWBRiUaG3o5"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/NgcBaJhGHbE?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX70RN3TfWWJh",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX70RN3TfWWJh"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/9E6b3swbnWg?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX2pSTOxoPbx9",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX2pSTOxoPbx9"
                    }
                },
                "tamil": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/MGQ5m0QdCjE?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/1E1j2PbaSW1byDCxtaiGlg",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/1E1j2PbaSW1byDCxtaiGlg"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/r00ikilDxW4?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DXaVmfUr97Uve",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DXaVmfUr97Uve"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/HpEi0lrpLDo?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/4zzmGEbnAkLZRiVO9b9eGO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/4zzmGEbnAkLZRiVO9b9eGO"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/1q8gp2AB6VY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/43a73ssTnlw00K8ljXDEfO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/43a73ssTnlw00K8ljXDEfO"
                    }
                }
            },
            "melancholy": {
                "english": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/1ZYbU82GVz4?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX7gIoKXt0gmx",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX7gIoKXt0gmx"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/hLQl3WQQoQ0?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX7qK8ma5wgG1",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX7qK8ma5wgG1"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/d-diB65scQU?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DWSqBruwoIXkA",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DWSqBruwoIXkA"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/oHBx7y8kRPY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DX2pNb5XG6XQH",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DX2pNb5XG6XQH"
                    }
                },
                "tamil": {
                    "lofi": {
                        "youtube": "https://www.youtube.com/embed/MGQ5m0QdCjE?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/1E1j2PbaSW1byDCxtaiGlg",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/1E1j2PbaSW1byDCxtaiGlg"
                    },
                    "pop": {
                        "youtube": "https://www.youtube.com/embed/r00ikilDxW4?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/37i9dQZF1DXaVmfUr97Uve",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/37i9dQZF1DXaVmfUr97Uve"
                    },
                    "melody": {
                        "youtube": "https://www.youtube.com/embed/HpEi0lrpLDo?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/4zzmGEbnAkLZRiVO9b9eGO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/4zzmGEbnAkLZRiVO9b9eGO"
                    },
                    "beats": {
                        "youtube": "https://www.youtube.com/embed/1q8gp2AB6VY?autoplay=1",
                        "spotify": "https://open.spotify.com/playlist/43a73ssTnlw00K8ljXDEfO",
                        "spotify_embed": "https://open.spotify.com/embed/playlist/43a73ssTnlw00K8ljXDEfO"
                    }
                }
            }
        }

        playlist = playlists.get(mood, {}).get(language, {}).get(ptype)
        if not playlist:
            # Fallback to focused english lofi
            playlist = playlists["focused"]["english"]["lofi"]

        return jsonify({
            "playlist_name": f"{language.capitalize()} • {ptype.capitalize()} • {mood.capitalize()}",
            "youtube_url": playlist["youtube"],
            "spotify_url": playlist["spotify"],
            "spotify_embed": playlist["spotify_embed"],
            "description": f"{mood.capitalize()} mood • {language.capitalize()} {ptype} playlist"
        })

    except Exception as e:
        return jsonify({"error": f"Error: {e}"}), 500


# ----------------------------------------------------
#  ORIGINAL FEATURE: MOTIVATIONAL QUOTE API (Preserved)
# ----------------------------------------------------
@app.route('/api/quote', methods=['GET', 'OPTIONS'], strict_slashes=False)
def get_quote():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    quotes = [
        "Success is the sum of small efforts repeated day in and day out. – Robert Collier",
        "Don't watch the clock; do what it does. Keep going. – Sam Levenson",
        "The expert in anything was once a beginner. – Helen Hayes",
        "Education is the most powerful weapon which you can use to change the world. – Nelson Mandela",
        "Focus on progress, not perfection. Every study session counts.",
        "Small daily disciplines compound into massive academic achievement.",
        "கல்வி கற்றால் நேர்மை வரும். – திருவள்ளுவர்",
        "அறிவே ஆற்றல். – ஏ. பி. ஜே. அப்துல் கலாம்"
    ]
    return jsonify({"quote": random.choice(quotes)})


@app.route('/spotify/<path:path>', methods=['GET', 'OPTIONS'], strict_slashes=False)
def spotify_proxy(path):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    return redirect(f"https://open.spotify.com/{path}")


# ----------------------------------------------------
#  FRONTEND STATIC CATCH-ALL (Excludes /api/ routes)
# ----------------------------------------------------
@app.route('/<non_api_path:path>', methods=['GET'])
def static_files(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')


# ----------------------------------------------------
#  ERROR HANDLERS (Always return valid JSON)
# ----------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.errorhandler(400)
def bad_request(error):
    msg = getattr(error, 'description', str(error))
    return jsonify({"error": msg, "status_code": 400}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found", "status_code": 404}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "HTTP 405 Method Not Allowed: Please ensure you are sending the correct HTTP method (e.g. POST with JSON body).",
        "status_code": 405
    }), 405

@app.errorhandler(500)
def internal_error(error):
    msg = getattr(error, 'description', "Internal server error")
    return jsonify({"error": msg, "status_code": 500}), 500

@app.errorhandler(Exception)
def handle_unexpected_exception(error):
    return jsonify({"error": f"An unexpected server error occurred: {str(error)}", "status_code": 500}), 500


# ----------------------------------------------------
#  SERVER ENTRYPOINT
# ----------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    print("=" * 60)
    print("🚀 StudyPulse AI Backend")
    print(f"📡 OpenRouter Key: {'Configured ✅' if OPENROUTER_API_KEY else 'Offline Rule-Based Fallback Active ⚙️'}")
    print(f"🤖 AI Model: {OPENROUTER_MODEL}")
    print(f"💾 Persistent Storage: SQLite ({DB_PATH})")
    print(f"📁 Serving Frontend: {FRONTEND_DIR}")
    print(f"🌐 Application URL: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"⚙️ Mode: {'Debug' if debug else 'Production (Standard)'}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
