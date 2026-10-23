import os
import sqlite3
import json
from datetime import datetime, date

DB_PATH = os.getenv('DATABASE_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'study_planner.db')

# Ensure database directory exists (supports persistent volume mounts like /data/study_planner.db)
_db_dir = os.path.dirname(os.path.abspath(DB_PATH))
if _db_dir and not os.path.exists(_db_dir):
    os.makedirs(_db_dir, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Profile Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            institution TEXT DEFAULT '',
            target_exam TEXT DEFAULT '',
            daily_study_hours REAL NOT NULL DEFAULT 4.0,
            preferred_study_time TEXT NOT NULL DEFAULT 'Evening',
            subjects TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tasks Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium',
            deadline TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            completed INTEGER NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL
        )
    ''')

    # Study Schedules Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_name TEXT NOT NULL,
            generated_by TEXT NOT NULL,
            parameters TEXT NOT NULL,
            schedule_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # Seed initial Profile if empty
    cursor.execute('SELECT COUNT(*) FROM profile WHERE id = 1')
    if cursor.fetchone()[0] == 0:
        default_subjects = ["Mathematics", "Data Structures", "Operating Systems", "Computer Networks", "Database Systems"]
        cursor.execute('''
            INSERT INTO profile (id, name, email, institution, target_exam, daily_study_hours, preferred_study_time, subjects)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Alex Morgan",
            "alex.morgan@university.edu",
            "Faculty of Computer Science & Engineering",
            "Semester Final Exams 2026",
            4.0,
            "Evening",
            json.dumps(default_subjects)
        ))

    # Seed sample Tasks if empty
    cursor.execute('SELECT COUNT(*) FROM tasks')
    if cursor.fetchone()[0] == 0:
        today_str = date.today().isoformat()
        sample_tasks = [
            ("Solve Dynamic Programming & Trees Assignment", "Data Structures", "Urgent", today_str, 90, 0, "Focus on recursion memoization"),
            ("Revise Virtual Memory & Page Replacement", "Operating Systems", "High", today_str, 60, 0, "Understand LRU and FIFO algorithms"),
            ("Complete SQL Joins & Normalization Worksheet", "Database Systems", "Medium", today_str, 45, 1, "Submitted to portal"),
            ("Practice Eigenvalues & Matrix Transformations", "Mathematics", "Medium", today_str, 60, 0, "Chapter 3 practice questions"),
            ("Study OSI 7-Layer Model & TCP Handshake", "Computer Networks", "Low", today_str, 30, 0, "Create summary diagram")
        ]
        for task in sample_tasks:
            cursor.execute('''
                INSERT INTO tasks (title, subject, priority, deadline, duration_minutes, completed, notes, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task[0], task[1], task[2], task[3], task[4], task[5], task[6], datetime.now().isoformat() if task[5] == 1 else None))

    conn.commit()
    conn.close()

# ----------------------------------------------------
# Profile Operations
# ----------------------------------------------------
def get_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM profile WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d['subjects'] = json.loads(d['subjects'])
    except Exception:
        d['subjects'] = []
    return d

def update_profile(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    subjects_json = json.dumps(data.get('subjects', [])) if isinstance(data.get('subjects'), list) else data.get('subjects', '[]')
    
    cursor.execute('''
        UPDATE profile
        SET name = ?,
            email = ?,
            institution = ?,
            target_exam = ?,
            daily_study_hours = ?,
            preferred_study_time = ?,
            subjects = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (
        data.get('name', 'Student').strip(),
        data.get('email', '').strip(),
        data.get('institution', '').strip(),
        data.get('target_exam', '').strip(),
        float(data.get('daily_study_hours', 4.0)),
        data.get('preferred_study_time', 'Evening').strip(),
        subjects_json
    ))
    conn.commit()
    conn.close()
    return get_profile()

# ----------------------------------------------------
# Task Operations (CRUD)
# ----------------------------------------------------
def get_tasks(filter_status=None, subject=None, search=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM tasks WHERE 1=1'
    params = []

    if filter_status == 'completed':
        query += ' AND completed = 1'
    elif filter_status == 'pending':
        query += ' AND completed = 0'

    if subject and subject.strip() and subject.strip().lower() != 'all':
        query += ' AND LOWER(subject) = LOWER(?)'
        params.append(subject.strip())

    if search and search.strip():
        query += ' AND (LOWER(title) LIKE LOWER(?) OR LOWER(notes) LIKE LOWER(?))'
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])

    query += ' ORDER BY completed ASC, CASE priority WHEN "Urgent" THEN 1 WHEN "High" THEN 2 WHEN "Medium" THEN 3 ELSE 4 END, deadline ASC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_task_by_id(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_task(data):
    title = (data.get('title') or '').strip()
    subject = (data.get('subject') or '').strip()
    if not title:
        raise ValueError("Task title is required.")
    if not subject:
        raise ValueError("Subject is required.")

    priority = data.get('priority', 'Medium')
    if priority not in ['Low', 'Medium', 'High', 'Urgent']:
        priority = 'Medium'

    deadline = (data.get('deadline') or '').strip()
    if not deadline:
        deadline = date.today().isoformat()

    duration = int(data.get('duration_minutes', 60))
    if duration <= 0:
        duration = 60

    notes = (data.get('notes') or '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (title, subject, priority, deadline, duration_minutes, completed, notes)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    ''', (title, subject, priority, deadline, duration, notes))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_task_by_id(task_id)

def update_task(task_id, data):
    existing = get_task_by_id(task_id)
    if not existing:
        return None

    title = data.get('title', existing['title']).strip()
    subject = data.get('subject', existing['subject']).strip()
    priority = data.get('priority', existing['priority'])
    deadline = data.get('deadline', existing['deadline']).strip()
    duration = int(data.get('duration_minutes', existing['duration_minutes']))
    notes = data.get('notes', existing['notes']).strip()
    completed = int(data.get('completed', existing['completed']))
    
    completed_at = existing['completed_at']
    if completed == 1 and not completed_at:
        completed_at = datetime.now().isoformat()
    elif completed == 0:
        completed_at = None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET title = ?,
            subject = ?,
            priority = ?,
            deadline = ?,
            duration_minutes = ?,
            completed = ?,
            notes = ?,
            completed_at = ?
        WHERE id = ?
    ''', (title, subject, priority, deadline, duration, completed, notes, completed_at, task_id))
    conn.commit()
    conn.close()
    return get_task_by_id(task_id)

def toggle_task_completed(task_id):
    existing = get_task_by_id(task_id)
    if not existing:
        return None

    new_status = 0 if existing['completed'] == 1 else 1
    completed_at = datetime.now().isoformat() if new_status == 1 else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET completed = ?, completed_at = ?
        WHERE id = ?
    ''', (new_status, completed_at, task_id))
    conn.commit()
    conn.close()
    return get_task_by_id(task_id)

def delete_task(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

# ----------------------------------------------------
# Study Schedule Operations
# ----------------------------------------------------
def save_study_schedule(plan_name, generated_by, parameters, schedule_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Mark old schedules as non-active
    cursor.execute('UPDATE study_schedules SET is_active = 0')
    
    cursor.execute('''
        INSERT INTO study_schedules (plan_name, generated_by, parameters, schedule_data, is_active)
        VALUES (?, ?, ?, ?, 1)
    ''', (
        plan_name,
        generated_by,
        json.dumps(parameters) if not isinstance(parameters, str) else parameters,
        json.dumps(schedule_data) if not isinstance(schedule_data, str) else schedule_data
    ))
    schedule_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_schedule_by_id(schedule_id)

def get_schedule_by_id(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM study_schedules WHERE id = ?', (schedule_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d['parameters'] = json.loads(d['parameters'])
    except Exception:
        pass
    try:
        d['schedule_data'] = json.loads(d['schedule_data'])
    except Exception:
        pass
    return d

def get_active_study_schedule():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM study_schedules WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d['parameters'] = json.loads(d['parameters'])
    except Exception:
        pass
    try:
        d['schedule_data'] = json.loads(d['schedule_data'])
    except Exception:
        pass
    return d

def get_schedule_history(limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, plan_name, generated_by, created_at, is_active FROM study_schedules ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------------------------------------------
# Analytics & Progress Calculations
# ----------------------------------------------------
def get_analytics_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks')
    tasks = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t['completed'] == 1)
    pending_tasks = total_tasks - completed_tasks
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    today_str = date.today().isoformat()
    today_tasks = 0
    upcoming_tasks = 0
    overdue_tasks = 0
    total_study_minutes = 0
    completed_study_minutes = 0

    subject_map = {}
    priority_map = {"Low": 0, "Medium": 0, "High": 0, "Urgent": 0}

    for t in tasks:
        # Priority count
        p = t.get('priority', 'Medium')
        priority_map[p] = priority_map.get(p, 0) + 1

        # Minutes
        dur = t.get('duration_minutes', 60)
        total_study_minutes += dur
        if t['completed'] == 1:
            completed_study_minutes += dur

        # Deadlines
        dl = t.get('deadline', '')
        if t['completed'] == 0:
            if dl < today_str:
                overdue_tasks += 1
            elif dl == today_str:
                today_tasks += 1
            else:
                upcoming_tasks += 1

        # Subject aggregation
        subj = t.get('subject', 'General')
        if subj not in subject_map:
            subject_map[subj] = {"subject": subj, "total": 0, "completed": 0, "pending": 0, "total_minutes": 0}
        subject_map[subj]["total"] += 1
        subject_map[subj]["total_minutes"] += dur
        if t['completed'] == 1:
            subject_map[subj]["completed"] += 1
        else:
            subject_map[subj]["pending"] += 1

    subject_breakdown = []
    for subj, stats in subject_map.items():
        rate = round((stats["completed"] / stats["total"] * 100), 1) if stats["total"] > 0 else 0.0
        subject_breakdown.append({
            "subject": subj,
            "total": stats["total"],
            "completed": stats["completed"],
            "pending": stats["pending"],
            "completion_rate": rate,
            "total_minutes": stats["total_minutes"]
        })

    subject_breakdown.sort(key=lambda x: x["total"], reverse=True)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "completion_rate": completion_rate,
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "overdue_tasks": overdue_tasks,
        "total_study_hours": round(total_study_minutes / 60.0, 1),
        "completed_study_hours": round(completed_study_minutes / 60.0, 1),
        "priority_distribution": priority_map,
        "subject_breakdown": subject_breakdown
    }
