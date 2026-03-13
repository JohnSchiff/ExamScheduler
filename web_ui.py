import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

import data_processing as dp
from exam_scheduler import ExamScheduler

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="שיבוץ בחינות",
    page_icon="📅",
    layout="wide",
)

st.markdown("""
<style>
    html, body, [class*="css"] { direction: rtl; }
    h1, h2, h3, h4, p, label, div { direction: rtl; text-align: right; }
    .upload-label { font-size: 1rem; font-weight: 600; margin-bottom: 4px; }
    div[data-testid="stButton"] button { font-size: 1.1rem; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
DAY_HE = {
    'Sunday': 'ראשון', 'Monday': 'שני', 'Tuesday': 'שלישי',
    'Wednesday': 'רביעי', 'Thursday': 'חמישי', 'Friday': 'שישי',
}
SEMESTER_LABEL = {1: 'א', 2: 'ב'}


# ── Helpers ────────────────────────────────────────────────────────────────────
def load_config():
    with open('config.yaml') as f:
        return yaml.load(f, Loader=SafeLoader)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buf.getvalue()


def build_flat_df(scheduler: ExamScheduler) -> pd.DataFrame:
    rows = []
    for _, row in scheduler.exam_schedule_table.iterrows():
        if not row['code']:
            continue
        d = row['date']
        day_he = DAY_HE.get(d.strftime('%A'), '')
        for code, desc in zip(row['code'], row['descriptions']):
            name = desc.split(' - ', 1)[1] if ' - ' in str(desc) else str(desc)
            rows.append({
                'תאריך': d.strftime('%d/%m/%Y'),
                'יום': day_he,
                'קוד קורס': code,
                'שם קורס': name,
                'מספר סטודנטים': scheduler.students_per_course_dict.get(code, 0),
            })
    return pd.DataFrame(rows)


def _run_scheduler(df_ifunim, df_courses, limitations,
                   start_date, end_date, gap, second_semester_start):
    secondStart = str(second_semester_start) if second_semester_start else None
    scheduler = ExamScheduler(
        df_ifunim, df_courses, limitations,
        start_date=str(start_date), end_date=str(end_date),
        gap=gap, start_secondS=secondStart,
    )
    scheduler.schedule()
    programs_df = scheduler.arrangePrograms()
    flat_df = build_flat_df(scheduler)
    return scheduler, programs_df, flat_df


def run_schedule(courses_file, ifunim_file, limits_file, moed_a_file,
                 semester, start_date, end_date, gap, second_semester_start):
    df_ifunim = dp.get_ifunim_dataframe_from_file(ifunim_file, semester=semester)
    df_courses = dp.get_courses_dataframe_from_file(courses_file)
    limitations = dp.get_limitations(limits_file, moed_a_file)
    return _run_scheduler(df_ifunim, df_courses, limitations,
                          start_date, end_date, gap, second_semester_start)


def build_dfs_from_manual(manual_courses: pd.DataFrame, manual_limits: pd.DataFrame,
                           semester: int, moed_a_file):
    """Convert manual data-editor DataFrames into the shapes ExamScheduler expects."""
    sem_label = SEMESTER_LABEL[semester]

    df_ifunim = pd.DataFrame({
        'course_code': manual_courses['course_code'].astype(int),
        'course_name': manual_courses['course_name'].astype(str),
        'spec': manual_courses['programs'].str.split(',').apply(
            lambda x: [s.strip() for s in x if s.strip()]),
        'semester': sem_label,
    })

    students = manual_courses['num_of_students'].fillna(0).astype(int)
    if (students < 0).any():
        raise ValueError('מספר סטודנטים לא יכול להיות שלילי')

    df_courses = pd.DataFrame({
        'course_code': manual_courses['course_code'].astype(int),
        'num_of_students': students,
        'semester': sem_label,
    })

    if manual_limits.empty or manual_limits['course_code'].isna().all():
        limitations = pd.DataFrame(
            columns=['course', 'course_name', 'start', 'end', 'no_friday', 'blocked'])
    else:
        lim = manual_limits.dropna(subset=['course_code'])
        limitations = pd.DataFrame({
            'course': lim['course_code'].astype(int),
            'start': pd.to_datetime(lim['start'], errors='coerce'),
            'end': pd.to_datetime(lim['end'], errors='coerce'),
            'blocked': pd.to_datetime(lim['blocked'], errors='coerce'),
            'no_friday': lim['no_friday'].fillna(False).astype(int),
        })

    if moed_a_file is not None:
        limitations = dp.parseMoedA(limitations, moed_a_file)

    return df_ifunim, df_courses, limitations


# ── Authentication ─────────────────────────────────────────────────────────────
config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)
authenticator.login()

if st.session_state.get('authentication_status') is False:
    st.error('שם משתמש או סיסמה שגויים')
    st.stop()

if not st.session_state.get('authentication_status'):
    st.warning('נא להזין שם משתמש וסיסמה')
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
authenticator.logout('התנתק', 'sidebar')
st.sidebar.write(f'שלום, **{st.session_state["name"]}**')
st.sidebar.divider()
st.sidebar.markdown('### ⚙️ הגדרות לוח המבחנים')

c1, c2 = st.sidebar.columns(2)
semester = c1.radio('סמסטר', [1, 2], key='semester')
moed = c2.radio('מועד', ['א', 'ב'], key='moed')

st.sidebar.markdown('**טווח תאריכים**')
start_date = st.sidebar.date_input('תאריך התחלה', value=date.today(), key='start_date')
end_date = st.sidebar.date_input('תאריך סיום', value=date.today() + timedelta(days=28), key='end_date')
if end_date <= start_date:
    st.sidebar.error('תאריך הסיום חייב להיות אחרי תאריך ההתחלה')

gap = st.sidebar.slider(
    'פער מינימלי בין בחינות חופפות (ימים)',
    min_value=1, max_value=7, value=3, key='gap',
)

second_semester_start = None
if moed == 'ב':
    st.sidebar.markdown('**תחילת הסמסטר (לסינון תאריכים)**')
    second_semester_start = st.sidebar.date_input('תחילת הסמסטר', key='second_semester_start')

# ── Header ─────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 7])
with col_logo:
    st.image('BIU_LOGO.png', width=100)
with col_title:
    st.title('מערכת שיבוץ בחינות — אוניברסיטת בר אילן')

st.divider()

# ── Input mode selection ───────────────────────────────────────────────────────
input_mode = st.radio(
    'אופן הזנת הנתונים',
    ['📁 קבצי Excel', '✏️ הזנה ידנית'],
    horizontal=True,
    key='input_mode',
)
is_manual = input_mode == '✏️ הזנה ידנית'

st.divider()

# ── FILE UPLOAD MODE ───────────────────────────────────────────────────────────
courses_file = ifunim_file = limits_file = None
moed_a_file = None

if not is_manual:
    st.markdown('### 📂 העלאת קבצים')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('**קובץ קורסים** *(חובה)*')
        st.caption('קובץ Excel — קוד קורס, שם קורס, מספר סטודנטים')
        courses_file = st.file_uploader(
            'קובץ קורסים', type=['xlsx'], label_visibility='collapsed', key='courses_file')
        if courses_file:
            st.success('✓ הועלה בהצלחה')

    with col2:
        st.markdown('**קובץ אפיונים** *(חובה)*')
        st.caption('קובץ Excel — מיפוי קורסים למסלולי לימוד')
        ifunim_file = st.file_uploader(
            'קובץ אפיונים', type=['xlsx'], label_visibility='collapsed', key='ifunim_file')
        if ifunim_file:
            st.success('✓ הועלה בהצלחה')

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('**קובץ אילוצים** *(רשות)*')
        st.caption('תאריכים חסומים, הגבלות לפי קורס')
        limits_file = st.file_uploader(
            'קובץ אילוצים', type=['xlsx'], label_visibility='collapsed', key='limits_file')
        if limits_file:
            st.success('✓ הועלה בהצלחה')

    with col4:
        if moed == 'ב':
            st.markdown('**לוח מועד א׳** *(חובה למועד ב)*')
            st.caption('קובץ פלט ממועד א — לקביעת מרווח בין המועדים')
            moed_a_file = st.file_uploader(
                'לוח מועד א', type=['xlsx'], label_visibility='collapsed', key='moed_a_file')
            if moed_a_file:
                st.success('✓ הועלה בהצלחה')

# ── MANUAL INPUT MODE ──────────────────────────────────────────────────────────
manual_courses_df = None
manual_limits_df = None

if is_manual:
    st.markdown('### ✏️ הזנת קורסים ואילוצים')

    # ── Courses table ──────────────────────────────────────────────────────────
    st.markdown('#### 📚 קורסים *(חובה)*')
    st.caption(
        'הזן קוד קורס, שם קורס, מספר סטודנטים ומסלולים (מופרדים בפסיק, לדוגמה: `101,102,103`).'
    )

    _empty_courses = pd.DataFrame({
        'course_code': pd.array([], dtype='int64'),
        'course_name': pd.array([], dtype='object'),
        'num_of_students': pd.array([], dtype='int64'),
        'programs': pd.array([], dtype='object'),
    })

    manual_courses_df = st.data_editor(
        _empty_courses,
        num_rows='dynamic',
        use_container_width=True,
        key='manual_courses',
        column_config={
            'course_code': st.column_config.NumberColumn(
                'קוד קורס', required=True, min_value=1, step=1, format='%d'),
            'course_name': st.column_config.TextColumn('שם קורס', required=True),
            'num_of_students': st.column_config.NumberColumn(
                'מספר סטודנטים', min_value=0, default=0, step=1, format='%d'),
            'programs': st.column_config.TextColumn(
                'מסלולים (מופרדים בפסיק)', required=True,
                help='לדוגמה: 101,202,303'),
        },
    )

    st.divider()

    # ── Limitations table ──────────────────────────────────────────────────────
    st.markdown('#### 🚫 אילוצים *(רשות)*')
    st.caption(
        'ניתן להגדיר חלון תאריכים מותר (התחלה/סיום), תאריך חסום, ו/או איסור שישי לכל קורס.'
    )

    _empty_limits = pd.DataFrame({
        'course_code': pd.array([], dtype='Int64'),
        'start': pd.array([], dtype='object'),
        'end': pd.array([], dtype='object'),
        'blocked': pd.array([], dtype='object'),
        'no_friday': pd.array([], dtype='bool'),
    })

    manual_limits_df = st.data_editor(
        _empty_limits,
        num_rows='dynamic',
        use_container_width=True,
        key='manual_limits',
        column_config={
            'course_code': st.column_config.NumberColumn(
                'קוד קורס', min_value=1, step=1, format='%d'),
            'start': st.column_config.DateColumn(
                'תאריך התחלה מוקדם ביותר', format='DD/MM/YYYY'),
            'end': st.column_config.DateColumn(
                'תאריך סיום מאוחר ביותר', format='DD/MM/YYYY'),
            'blocked': st.column_config.DateColumn(
                'תאריך חסום', format='DD/MM/YYYY'),
            'no_friday': st.column_config.CheckboxColumn('ללא שישי', default=False),
        },
    )

    # Moed A file uploader also appears in manual mode for Moed B
    if moed == 'ב':
        st.divider()
        st.markdown('**לוח מועד א׳** *(חובה למועד ב)*')
        st.caption('קובץ פלט ממועד א — לקביעת מרווח אוטומטי של 25 יום')
        moed_a_file = st.file_uploader(
            'לוח מועד א', type=['xlsx'], label_visibility='collapsed', key='moed_a_file_manual')
        if moed_a_file:
            st.success('✓ הועלה בהצלחה')

st.divider()

# ── Validation ─────────────────────────────────────────────────────────────────
errors = []
if not is_manual:
    if not courses_file:
        errors.append('יש להעלות קובץ קורסים')
    if not ifunim_file:
        errors.append('יש להעלות קובץ אפיונים')
    if moed == 'ב' and not moed_a_file:
        errors.append('למועד ב יש להעלות את לוח מועד א׳')
else:
    if manual_courses_df is None or manual_courses_df.empty:
        errors.append('יש להזין לפחות קורס אחד')
    elif manual_courses_df['course_code'].isna().any() or manual_courses_df['programs'].isna().any():
        errors.append('יש למלא קוד קורס ומסלולים לכל השורות')
    if moed == 'ב' and not moed_a_file:
        errors.append('למועד ב יש להעלות את לוח מועד א׳')

if end_date <= start_date:
    errors.append('טווח התאריכים אינו תקין')

# ── Generate button ────────────────────────────────────────────────────────────
_, btn_col, _ = st.columns([1, 2, 1])
generate_clicked = btn_col.button(
    '🗓️  צור לוח מבחנים',
    disabled=bool(errors),
    use_container_width=True,
    type='primary',
)

if errors and (
    (not is_manual and (courses_file or ifunim_file))
    or (is_manual and manual_courses_df is not None and not manual_courses_df.empty)
):
    for e in errors:
        st.warning(e)

# ── Run scheduler ──────────────────────────────────────────────────────────────
if generate_clicked:
    with st.spinner('מחשב לוח מבחנים... אנא המתן'):
        try:
            if not is_manual:
                scheduler, programs_df, flat_df = run_schedule(
                    courses_file, ifunim_file, limits_file, moed_a_file,
                    semester, start_date, end_date, gap, second_semester_start,
                )
            else:
                df_ifunim, df_courses, limitations = build_dfs_from_manual(
                    manual_courses_df, manual_limits_df, semester, moed_a_file)
                scheduler, programs_df, flat_df = _run_scheduler(
                    df_ifunim, df_courses, limitations,
                    start_date, end_date, gap, second_semester_start,
                )
            st.session_state['result'] = {
                'scheduler': scheduler,
                'programs_df': programs_df,
                'flat_df': flat_df,
                'label': f'סמסטר {semester} מועד {"א" if moed == "א" else "ב"}',
            }
            st.success('לוח המבחנים נוצר בהצלחה!')
        except Exception as e:
            st.error(f'שגיאה ביצירת הלוח: {e}')
            st.session_state.pop('result', None)

# ── Results ────────────────────────────────────────────────────────────────────
if 'result' not in st.session_state:
    st.stop()

res = st.session_state['result']
scheduler: ExamScheduler = res['scheduler']
flat_df: pd.DataFrame = res['flat_df']
programs_df: pd.DataFrame = res['programs_df']
label: str = res['label']

unscheduled = set(scheduler.courses_to_place) - set(scheduler.scheduled_courses)

st.divider()
st.markdown(f'### 📊 תוצאות — {label}')

m1, m2, m3, m4 = st.columns(4)
m1.metric('קורסים שובצו', len(scheduler.scheduled_courses))
m2.metric('סה"כ קורסים', len(scheduler.courses_to_place))
m3.metric('ימי בחינה', flat_df['תאריך'].nunique() if not flat_df.empty else 0)
m4.metric('לא שובצו', len(unscheduled))

if unscheduled:
    with st.expander(f'⚠️ {len(unscheduled)} קורסים לא שובצו — לחץ לפרטים'):
        for code in sorted(unscheduled):
            name = scheduler.code_dict.get(code, '')
            st.write(f'• {code} — {name}')

st.divider()

tab1, tab2 = st.tabs(['📋 לוח לפי תאריך', '🗂️ לוח לפי מסלול'])

with tab1:
    st.dataframe(
        flat_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'מספר סטודנטים': st.column_config.NumberColumn(format='%d'),
        },
    )
    safe_label = label.replace(' ', '_')
    st.download_button(
        label='⬇️ הורד לוח בחינות (Excel)',
        data=to_excel_bytes(flat_df),
        file_name=f'exam_schedule_{safe_label}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )

with tab2:
    st.dataframe(programs_df, use_container_width=True, hide_index=True)
    st.download_button(
        label='⬇️ הורד לפי מסלולים (Excel)',
        data=to_excel_bytes(programs_df),
        file_name=f'programs_{safe_label}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
