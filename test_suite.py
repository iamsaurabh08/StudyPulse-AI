import os
import sys
import json
import sqlite3
from datetime import date, timedelta

# Fix Windows console encoding for Unicode/emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app
from backend.database import DB_PATH, init_db, get_db_connection

def run_tests():
    print("=" * 60)
    print("🧪 RUNNING COMPREHENSIVE AUTOMATED TEST SUITE")
    print("=" * 60)

    client = app.test_client()
    passed = 0
    total = 0

    def assert_test(condition, test_name):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"✅ PASS: {test_name}")
        else:
            print(f"❌ FAIL: {test_name}")
            raise AssertionError(f"Test failed: {test_name}")

    # 1. System Status Endpoint
    res = client.get('/api/status')
    assert_test(res.status_code == 200, "GET /api/status returns HTTP 200")
    data = res.get_json()
    assert_test(data.get('status') == 'operational', "System status is operational")
    assert_test('planner_mode' in data, "Planner mode reported correctly")

    # 2. Static Frontend Serving
    res = client.get('/')
    assert_test(res.status_code == 200, "GET / serves index.html")
    assert_test(b'StudyPulse AI' in res.data, "index.html contains StudyPulse AI title")

    res = client.get('/css/style.css')
    assert_test(res.status_code == 200, "GET /css/style.css returns stylesheet")

    res = client.get('/js/app.js')
    assert_test(res.status_code == 200, "GET /js/app.js returns app JavaScript")

    res = client.get('/js/api.js')
    assert_test(res.status_code == 200, "GET /js/api.js returns API client JavaScript")

    # 3. Student Profile Endpoints
    res = client.get('/api/profile')
    assert_test(res.status_code == 200, "GET /api/profile returns HTTP 200")
    prof = res.get_json()
    assert_test(bool(prof.get('name')), "Default profile has a valid name")
    assert_test(isinstance(prof.get('subjects'), list), "Profile subjects is a list")

    # Update Profile
    update_payload = {
        "name": "Jane Doe",
        "email": "jane.doe@university.edu",
        "institution": "Department of Computer Science",
        "target_exam": "Final Semester Exams",
        "daily_study_hours": 5.0,
        "preferred_study_time": "Morning",
        "subjects": ["Operating Systems", "Computer Networks", "Artificial Intelligence"]
    }
    res = client.post('/api/profile', data=json.dumps(update_payload), content_type='application/json')
    assert_test(res.status_code == 200, "POST /api/profile updates profile")
    updated_prof = client.get('/api/profile').get_json()
    assert_test(updated_prof['name'] == 'Jane Doe', "Profile name persisted as 'Jane Doe'")
    assert_test(updated_prof['daily_study_hours'] == 5.0, "Daily study hours persisted as 5.0")
    assert_test(len(updated_prof['subjects']) == 3, "Subjects updated to 3 items")

    # 4. Task Management (CRUD)
    # GET initial tasks
    res = client.get('/api/tasks')
    assert_test(res.status_code == 200, "GET /api/tasks returns HTTP 200")
    initial_tasks = res.get_json()
    initial_count = len(initial_tasks)
    assert_test(initial_count >= 1, "Initial seeded tasks exist")

    # CREATE Task
    new_task = {
        "title": "Master Heuristic Search & A* Algorithm",
        "subject": "Artificial Intelligence",
        "priority": "Urgent",
        "deadline": (date.today() + timedelta(days=2)).isoformat(),
        "duration_minutes": 90,
        "notes": "Chapter 4 uninformed vs informed search"
    }
    res = client.post('/api/tasks', data=json.dumps(new_task), content_type='application/json')
    assert_test(res.status_code == 201, "POST /api/tasks returns HTTP 201 Created")
    created = res.get_json()['task']
    task_id = created['id']
    assert_test(created['title'] == new_task['title'], "Created task has correct title")
    assert_test(created['priority'] == 'Urgent', "Created task priority is 'Urgent'")
    assert_test(created['completed'] == 0, "Created task is pending (0)")

    # Form Validation test (empty title should fail)
    res = client.post('/api/tasks', data=json.dumps({"title": "", "subject": "Math"}), content_type='application/json')
    assert_test(res.status_code == 400, "POST /api/tasks with empty title returns 400 Bad Request")

    # GET Single Task
    res = client.get(f'/api/tasks/{task_id}')
    assert_test(res.status_code == 200, f"GET /api/tasks/{task_id} retrieves task")
    assert_test(res.get_json()['id'] == task_id, "Retrieved task ID matches")

    # UPDATE Task
    update_data = {
        "title": "Master Heuristic Search & A* Algorithm (Revised)",
        "priority": "High",
        "duration_minutes": 120
    }
    res = client.put(f'/api/tasks/{task_id}', data=json.dumps(update_data), content_type='application/json')
    assert_test(res.status_code == 200, f"PUT /api/tasks/{task_id} updates task")
    updated_task = client.get(f'/api/tasks/{task_id}').get_json()
    assert_test(updated_task['title'] == update_data['title'], "Updated task title matches")
    assert_test(updated_task['duration_minutes'] == 120, "Updated task duration matches 120")

    # TOGGLE Task
    res = client.patch(f'/api/tasks/{task_id}/toggle')
    assert_test(res.status_code == 200, f"PATCH /api/tasks/{task_id}/toggle returns 200")
    assert_test(res.get_json()['task']['completed'] == 1, "Task completed status toggled to 1")

    # Filter tasks by status=completed
    res = client.get('/api/tasks?status=completed')
    completed_list = res.get_json()
    assert_test(any(t['id'] == task_id for t in completed_list), "Toggled task appears in status=completed filter")

    # 5. Progress Tracker & Analytics Calculations
    res = client.get('/api/analytics/progress')
    assert_test(res.status_code == 200, "GET /api/analytics/progress returns HTTP 200")
    analytics = res.get_json()
    assert_test('total_tasks' in analytics, "Analytics has 'total_tasks'")
    assert_test('completed_tasks' in analytics, "Analytics has 'completed_tasks'")
    assert_test('completion_rate' in analytics, "Analytics has 'completion_rate'")
    assert_test('subject_breakdown' in analytics, "Analytics has 'subject_breakdown'")
    assert_test(analytics['total_tasks'] == initial_count + 1, "Analytics total tasks count is accurate")
    expected_rate = round((analytics['completed_tasks'] / analytics['total_tasks']) * 100, 1)
    assert_test(analytics['completion_rate'] == expected_rate, f"Completion rate calculation is mathematically accurate ({analytics['completion_rate']}%)")

    # 6. AI & Rule-Based Study Planner
    # Test 6a: Past Exam Date Rejection (ISO format YYYY-MM-DD)
    past_date_payload = {
        "subjects": [
            {
                "name": "Database Systems",
                "difficulty": 4,
                "exam_date": "2026-10-15", # in past relative to 2026-10-23
                "topics": "SQL Joins"
            }
        ],
        "daily_hours": 4.0,
        "days_count": 7,
        "start_date": "2026-10-23"
    }
    res_past = client.post('/api/planner/generate', data=json.dumps(past_date_payload), content_type='application/json')
    assert_test(res_past.status_code == 400, "POST /api/planner/generate with past exam date returns HTTP 400")
    assert_test(res_past.is_json, "Past exam date error returns valid JSON")
    assert_test("in the past" in res_past.get_json().get("error", "").lower(), "Error explicitly explains exam date is in the past")

    # Test 6b: Past Exam Date Rejection (DD-MM-YYYY format)
    past_dd_payload = {
        "subjects": [{"name": "Math", "difficulty": 3, "exam_date": "15-10-2026"}],
        "daily_hours": 4.0,
        "days_count": 7,
        "start_date": "23-10-2026"
    }
    res_past_dd = client.post('/api/planner/generate', data=json.dumps(past_dd_payload), content_type='application/json')
    assert_test(res_past_dd.status_code == 400, "POST /api/planner/generate with DD-MM-YYYY past date returns HTTP 400")
    assert_test("in the past" in res_past_dd.get_json().get("error", "").lower(), "DD-MM-YYYY error explicitly explains past date")

    # Test 6c: Flexible Date Formatting with Valid Upcoming Dates (DD-MM-YYYY)
    flexible_payload = {
        "subjects": [{"name": "Discrete Math", "difficulty": 4, "exam_date": "30-10-2026"}],
        "daily_hours": 4.0,
        "days_count": 5,
        "start_date": "23-10-2026"
    }
    res_flex = client.post('/api/planner/generate', data=json.dumps(flexible_payload), content_type='application/json')
    assert_test(res_flex.status_code == 200, "POST /api/planner/generate parses DD-MM-YYYY successfully (HTTP 200)")
    assert_test(len(res_flex.get_json().get('daily_schedule', [])) == 5, "Generated 5 days from DD-MM-YYYY inputs")

    # Test 6d: Validation of Empty Subject List
    res_empty_sub = client.post('/api/planner/generate', data=json.dumps({"subjects": []}), content_type='application/json')
    assert_test(res_empty_sub.status_code == 400, "Empty subjects list returns HTTP 400")
    assert_test(res_empty_sub.is_json, "Empty subjects returns valid JSON")

    # Test 6e: Validation of Missing Subject Name
    res_no_name = client.post('/api/planner/generate', data=json.dumps({"subjects": [{"name": "   ", "difficulty": 3}]}), content_type='application/json')
    assert_test(res_no_name.status_code == 400, "Blank subject name returns HTTP 400")

    # Test 6f: Validation of Invalid Study Hours
    res_bad_hours = client.post('/api/planner/generate', data=json.dumps({"subjects": [{"name": "Math"}], "daily_hours": 25.0}), content_type='application/json')
    assert_test(res_bad_hours.status_code == 400, "Daily hours > 16 returns HTTP 400")

    # Test 6g: Validation of Invalid Days Count
    res_bad_days = client.post('/api/planner/generate', data=json.dumps({"subjects": [{"name": "Math"}], "days_count": 0}), content_type='application/json')
    assert_test(res_bad_days.status_code == 400, "Days count < 1 returns HTTP 400")

    # Test 6h: Empty Request Body (Checks that 400 is JSON, not HTML)
    res_empty_body = client.post('/api/planner/generate', data="", content_type='application/json')
    assert_test(res_empty_body.status_code == 400, "Empty request body returns HTTP 400")
    assert_test(res_empty_body.is_json, "Empty request body returns valid JSON")

    # Test 6i: OPTIONS Preflight Handling
    res_options = client.open('/api/planner/generate', method='OPTIONS')
    assert_test(res_options.status_code == 200, "OPTIONS /api/planner/generate returns HTTP 200")

    # Test 6j: Trailing Slash Handling (strict_slashes=False prevents 405 on trailing slash)
    res_trailing = client.post('/api/planner/generate/', data=json.dumps(flexible_payload), content_type='application/json')
    assert_test(res_trailing.status_code == 200, "POST /api/planner/generate/ (with trailing slash) returns HTTP 200")

    res_options_trailing = client.open('/api/planner/generate/', method='OPTIONS')
    assert_test(res_options_trailing.status_code == 200, "OPTIONS /api/planner/generate/ returns HTTP 200")

    # Test 6k: CORS Headers on Cross-Origin Preflight
    res_cors = client.open('/api/planner/generate', method='OPTIONS', headers={'Origin': 'http://localhost:5500'})
    assert_test(res_cors.headers.get('Access-Control-Allow-Origin') == '*', "CORS header Access-Control-Allow-Origin is '*'")

    # Test 6l: Structured JSON on Method Not Allowed (405)
    res_405 = client.open('/api/planner/generate', method='DELETE')
    assert_test(res_405.status_code == 405, "DELETE /api/planner/generate returns HTTP 405")
    assert_test(res_405.is_json, "405 error returns valid structured JSON")
    assert_test("Method Not Allowed" in res_405.get_json().get("error", ""), "405 response contains descriptive error message")

    # Test 6m: API 404 does not hit static route with 405
    res_api_404 = client.post('/api/nonexistent_endpoint')
    assert_test(res_api_404.status_code == 404, "POST to unknown API endpoint returns HTTP 404 (not 405)")
    assert_test(res_api_404.is_json, "Unknown API endpoint returns valid JSON")

    # Test 6n: Standard Rule-Based Schedule Generation (Without API key)
    planner_payload = {
        "subjects": [
            {
                "name": "Operating Systems",
                "difficulty": 5,
                "exam_date": (date.today() + timedelta(days=3)).isoformat(),
                "topics": "Page replacement, Virtual Memory, Semaphore deadlocks"
            },
            {
                "name": "Computer Networks",
                "difficulty": 2,
                "exam_date": (date.today() + timedelta(days=25)).isoformat(),
                "topics": "IP Addressing, Routing protocols"
            }
        ],
        "daily_hours": 4.5,
        "days_count": 7,
        "force_rule_based": False # Tests automatic fallback when no API key
    }
    res = client.post('/api/planner/generate', data=json.dumps(planner_payload), content_type='application/json')
    assert_test(res.status_code == 200, "POST /api/planner/generate returns HTTP 200")
    plan = res.get_json()
    assert_test(plan.get('success') is True, "Plan generation reported success")
    assert_test(plan.get('generated_by') == 'Rule-Based Heuristic Algorithm', "Reported 'Rule-Based Heuristic Algorithm'")
    assert_test(len(plan.get('daily_schedule', [])) == 7, "Generated exactly 7 days of daily schedule")

    # Verify that difficult subject with near exam gets MORE time than easy subject with far exam
    weights = {w['name']: w['target_hours_per_day'] for w in plan.get('subject_weights', [])}
    assert_test(weights['Operating Systems'] > weights['Computer Networks'],
                f"Operating Systems ({weights['Operating Systems']}h/d) received more time than Computer Networks ({weights['Computer Networks']}h/d)")

    # GET Active Planner
    res = client.get('/api/planner/active')
    assert_test(res.status_code == 200, "GET /api/planner/active returns HTTP 200")
    active_plan = res.get_json()
    assert_test(bool(active_plan.get('schedule_data')), "Active plan contains schedule_data in SQLite")

    # 7. Focus Music & Quotes
    res = client.post('/api/music-suggest', data=json.dumps({"mood": "focused", "language": "english", "ptype": "lofi"}), content_type='application/json')
    assert_test(res.status_code == 200, "POST /api/music-suggest returns HTTP 200")
    music = res.get_json()
    assert_test('youtube_url' in music, "Music response includes youtube_url")
    assert_test('spotify_embed' in music, "Music response includes spotify_embed")

    res = client.get('/api/quote')
    assert_test(res.status_code == 200, "GET /api/quote returns HTTP 200")
    assert_test(len(res.get_json().get('quote', '')) > 5, "Quote string is valid")

    # 8. AI Assistant with Rule-Based Fallback
    res = client.post('/api/assistant', data=json.dumps({"prompt": "How do I study for my upcoming exams?"}), content_type='application/json')
    assert_test(res.status_code == 200, "POST /api/assistant returns HTTP 200")
    assist_data = res.get_json()
    assert_test(bool(assist_data.get('text')), "Assistant returns helpful guidance response")

    # 9. DELETE Task
    res = client.delete(f'/api/tasks/{task_id}')
    assert_test(res.status_code == 200, f"DELETE /api/tasks/{task_id} returns HTTP 200")
    res_after = client.get(f'/api/tasks/{task_id}')
    assert_test(res_after.status_code == 404, "Deleted task is no longer found (HTTP 404)")

    # 10. Database Persistence Verification (Across Connection Restarts)
    test_task = {
        "title": "Persistence Check Task",
        "subject": "Testing",
        "priority": "Medium",
        "deadline": date.today().isoformat(),
        "duration_minutes": 45
    }
    res_create = client.post('/api/tasks', data=json.dumps(test_task), content_type='application/json')
    persist_id = res_create.get_json()['task']['id']

    # Open fresh direct SQLite connection to verify disk persistence
    raw_conn = sqlite3.connect(DB_PATH)
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT title, subject FROM tasks WHERE id = ?", (persist_id,))
    row = raw_cursor.fetchone()
    raw_conn.close()
    assert_test(row is not None and row[0] == test_task['title'], "Task directly verified on disk in SQLite database file")

    # Cleanup persistence test task
    client.delete(f'/api/tasks/{persist_id}')

    print("=" * 60)
    print(f"🎉 ALL TESTS PASSED! {passed}/{total} assertions successful.")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
