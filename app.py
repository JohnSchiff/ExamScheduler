import io
import base64
import os
from functools import wraps

import bcrypt
import pandas as pd
import yaml
from flask import (Flask, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)

import data_processing as dp
from exam_scheduler import ExamScheduler

app = Flask(__name__)

DAY_HE = {
    'Sunday': 'ראשון', 'Monday': 'שני', 'Tuesday': 'שלישי',
    'Wednesday': 'רביעי', 'Thursday': 'חמישי', 'Friday': 'שישי',
}


def load_config():
    with open('config.yaml') as f:
        return yaml.safe_load(f)


app.secret_key = load_config().get('cookie', {}).get('key', 'biu-exam-secret')


# ── Auth helpers ───────────────────────────────────────────────────────────────
def check_credentials(username, password):
    config = load_config()
    users = config.get('credentials', {}).get('usernames', {})
    if username not in users:
        return False, None
    stored = users[username]['password'].encode('utf-8')
    if bcrypt.checkpw(password.encode('utf-8'), stored):
        return True, users[username]['name']
    return False, None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('scheduler') if session.get('logged_in') else url_for('login_page'))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ok, name = check_credentials(username, password)
        if ok:
            session['logged_in'] = True
            session['username'] = username
            session['name'] = name
            return redirect(url_for('scheduler'))
        error = 'שם משתמש או סיסמה שגויים'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/scheduler')
@login_required
def scheduler():
    return render_template('index.html', name=session.get('name', ''))


# ── Schedule generation ────────────────────────────────────────────────────────
def df_to_b64(df: pd.DataFrame) -> str:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return base64.b64encode(buf.getvalue()).decode()


def file_or_none(key):
    f = request.files.get(key)
    return f if f and f.filename else None


@app.route('/generate_manual', methods=['POST'])
@login_required
def generate_manual():
    try:
        data = request.get_json(force=True)
        courses_raw = data.get('courses', [])
        limits_raw  = data.get('limits', [])
        semester    = int(data.get('semester', 1))
        moed        = data.get('moed', 'א')
        start_date  = data['start_date']
        end_date    = data['end_date']
        gap         = int(data.get('gap', 3))
        second_start = data.get('second_semester_start') or None

        if not courses_raw:
            return jsonify({'error': 'יש להזין לפחות קורס אחד'}), 400

        for c in courses_raw:
            students = int(c.get('students') or 0)
            if students < 0:
                return jsonify({'error': f'מספר סטודנטים לא יכול להיות שלילי (קורס {c.get("code")})'}), 400

        sem_label = {1: 'א', 2: 'ב'}[semester]

        df_ifunim = pd.DataFrame({
            'course_code': [int(c['code']) for c in courses_raw],
            'course_name': [c['name'] for c in courses_raw],
            'spec': [
                [s.strip() for s in c['programs'].split(',') if s.strip()]
                for c in courses_raw
            ],
            'semester': sem_label,
        })

        df_courses = pd.DataFrame({
            'course_code':    [int(c['code']) for c in courses_raw],
            'num_of_students': [int(c.get('students') or 0) for c in courses_raw],
            'semester': sem_label,
        })

        if limits_raw:
            limitations = pd.DataFrame({
                'course':    [int(l['code']) for l in limits_raw],
                'start':     [pd.to_datetime(l['start'])   if l.get('start')   else pd.NaT for l in limits_raw],
                'end':       [pd.to_datetime(l['end'])     if l.get('end')     else pd.NaT for l in limits_raw],
                'blocked':   [pd.to_datetime(l['blocked']) if l.get('blocked') else pd.NaT for l in limits_raw],
                'no_friday': [1 if l.get('no_friday') else 0 for l in limits_raw],
            })
        else:
            limitations = pd.DataFrame(
                columns=['course', 'course_name', 'start', 'end', 'no_friday', 'blocked'])

        sched = ExamScheduler(
            df_ifunim, df_courses, limitations,
            start_date=start_date, end_date=end_date,
            gap=gap, start_secondS=second_start,
        )
        sched.schedule()
        programs_df = sched.arrangePrograms()

        rows = []
        for _, row in sched.exam_schedule_table.iterrows():
            if not row['code']:
                continue
            d = row['date']
            day_he = DAY_HE.get(d.strftime('%A'), '')
            for code, desc in zip(row['code'], row['descriptions']):
                name = desc.split(' - ', 1)[1] if ' - ' in str(desc) else str(desc)
                rows.append({
                    'date': d.strftime('%d/%m/%Y'), 'day': day_he,
                    'code': int(code), 'name': name,
                    'students': int(sched.students_per_course_dict.get(code, 0)),
                })

        unscheduled_codes = set(sched.courses_to_place) - set(sched.scheduled_courses)
        unscheduled = [
            {'code': int(c), 'name': sched.code_dict.get(c, '')}
            for c in sorted(unscheduled_codes)
        ]

        flat_df = pd.DataFrame([{
            'תאריך': r['date'], 'יום': r['day'], 'קוד קורס': r['code'],
            'שם קורס': r['name'], 'מספר סטודנטים': r['students'],
        } for r in rows])

        programs_df.columns = [str(c) for c in programs_df.columns]
        label = f'סמסטר {semester} מועד {"א" if moed == "א" else "ב"}'
        return jsonify({
            'rows': rows,
            'programs': programs_df.fillna('').to_dict(orient='records'),
            'program_columns': list(programs_df.columns),
            'stats': {
                'scheduled':   len(sched.scheduled_courses),
                'total':       len(sched.courses_to_place),
                'exam_days':   len(set(r['date'] for r in rows)),
                'unscheduled': len(unscheduled_codes),
            },
            'unscheduled':    unscheduled,
            'excel_flat':     df_to_b64(flat_df),
            'excel_programs': df_to_b64(programs_df),
            'label':          label,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/generate', methods=['POST'])
@login_required
def generate():
    try:
        courses_file = file_or_none('courses_file')
        ifunim_file  = file_or_none('ifunim_file')
        limits_file  = file_or_none('limits_file')
        moed_a_file  = file_or_none('moed_a_file')

        if not courses_file:
            return jsonify({'error': 'חסר קובץ קורסים'}), 400
        if not ifunim_file:
            return jsonify({'error': 'חסר קובץ אפיונים'}), 400

        semester   = int(request.form.get('semester', 1))
        moed       = request.form.get('moed', 'א')
        start_date = request.form.get('start_date')
        end_date   = request.form.get('end_date')
        gap        = int(request.form.get('gap', 3))
        second_start = request.form.get('second_semester_start') or None

        df_ifunim  = dp.get_ifunim_dataframe_from_file(ifunim_file, semester=semester)
        df_courses = dp.get_courses_dataframe_from_file(courses_file)
        limitations = dp.get_limitations(limits_file, moed_a_file)

        sched = ExamScheduler(
            df_ifunim, df_courses, limitations,
            start_date=start_date, end_date=end_date,
            gap=gap, start_secondS=second_start,
        )
        sched.schedule()
        programs_df = sched.arrangePrograms()

        # Build flat list (one row per exam)
        rows = []
        for _, row in sched.exam_schedule_table.iterrows():
            if not row['code']:
                continue
            d = row['date']
            day_he = DAY_HE.get(d.strftime('%A'), '')
            for code, desc in zip(row['code'], row['descriptions']):
                name = desc.split(' - ', 1)[1] if ' - ' in str(desc) else str(desc)
                rows.append({
                    'date':     d.strftime('%d/%m/%Y'),
                    'day':      day_he,
                    'code':     int(code),
                    'name':     name,
                    'students': int(sched.students_per_course_dict.get(code, 0)),
                })

        unscheduled_codes = set(sched.courses_to_place) - set(sched.scheduled_courses)
        unscheduled = [
            {'code': int(c), 'name': sched.code_dict.get(c, '')}
            for c in sorted(unscheduled_codes)
        ]

        # Excel exports
        flat_df = pd.DataFrame([{
            'תאריך': r['date'], 'יום': r['day'], 'קוד קורס': r['code'],
            'שם קורס': r['name'], 'מספר סטודנטים': r['students'],
        } for r in rows])

        programs_df.columns = [str(c) for c in programs_df.columns]
        programs_records = programs_df.fillna('').to_dict(orient='records')

        label = f'סמסטר {semester} מועד {"א" if moed == "א" else "ב"}'
        return jsonify({
            'rows':            rows,
            'programs':        programs_records,
            'program_columns': list(programs_df.columns),
            'stats': {
                'scheduled':  len(sched.scheduled_courses),
                'total':      len(sched.courses_to_place),
                'exam_days':  len(set(r['date'] for r in rows)),
                'unscheduled': len(unscheduled_codes),
            },
            'unscheduled':    unscheduled,
            'excel_flat':     df_to_b64(flat_df),
            'excel_programs': df_to_b64(programs_df),
            'label':          label,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8080)
