# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

University exam scheduling system for Bar-Ilan University. It reads course data from Hebrew Excel files, applies scheduling constraints, and produces an optimized exam timetable that avoids conflicts between overlapping programs. There is both a CLI entry point (`main.py`) and a Streamlit web UI (`web_ui.py`).

## Commands

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the Streamlit web UI (primary interface):
```bash
streamlit run web_ui.py
```

Run CLI scheduling (edit parameters at top of file first):
```bash
python main.py
```

Run tests:
```bash
python -m pytest test_exam_scheduler.py
python -m unittest test_exam_scheduler.py
```

## Architecture

### Core modules

- **`exam_scheduler.py`** — `ExamScheduler` class. The scheduling algorithm works in passes with decreasing strictness:
  1. 3-day gap between overlapping-program courses
  2. 2-day gap fallback
  3. Less-strict (no crowding but no hard gap)
  4. Least-strict (minimal constraints)

  Key internal data structures: `courses_per_program_dict` (program → course list), `crossed_course_dict` (course → all courses sharing any program), `restrictions_*_days` (per-course date blacklists at 1/2/3-day granularity), `exam_schedule_table` (DataFrame with date, code list, descriptions list).

- **`data_processing.py`** — All file I/O and DataFrame transformations. Reads Hebrew-column Excel files and normalizes them to English column names. Key functions: `get_ifunim_dataframe_from_file`, `get_courses_dataframe_from_file`, `get_limitations`, `gen_crossed_courses_dict_from_prog_dict`.

- **`web_ui.py`** — Streamlit app (`ExamSchedulerApp`). Login via `streamlit_authenticator` using `config.yaml`. Accepts three file uploads (courses, characteristics/ifunim, constraints/limitations), date range, moed (A/B), and semester inputs.

- **`main.py`** — CLI script. Parameters (semester, moed, date ranges, file names) are hardcoded at the top of the file. Outputs four Excel files: `df_ifunim`, `programs`, `exam_schedule`, `TablePerPrograms`.

### Input files (Hebrew Excel)

| Variable name | Hebrew filename | Contents |
|---|---|---|
| `charecteristics` / ifunim | `מאפיינים למערכת בחינות.xlsx` | Course–program mapping (spec column = comma-separated program codes) |
| `coursesFile` | `מספר סטודנטים בקורס.xlsx` | Number of students per course |
| `limitationsFile` | `קובץ אילוצים סמסטר ב.xlsx` | Date constraints per course (start/end window, blocked date, no-Friday flag) |

### Moed B handling

For Moed B, the Moed A schedule file is passed to `get_limitations()` via `parseMoedA()`, which adds a 25-day offset from each Moed A exam date as the earliest allowed Moed B date for that course.

### Authentication

`config.yaml` holds bcrypt-hashed credentials for `streamlit_authenticator`. To add users, hash passwords with `stauth.Hasher(['plaintext']).generate()` and add entries manually.

### Other files

- **`Logger.py`** — Simple in-memory logger with `add_remark` / `save_to_file` / `print_log`. A module-level `logger` singleton is exported and used across the codebase.
- **`test_schedule.py`** — Older integration test script; requires a pre-generated `test_exam_schedule.xlsx`. Less maintained than `test_exam_scheduler.py`.
- **`read_from_xl_file.py`** — One-off scratch script, not used in production.
- **`app.py`** — Unrelated Flask prototype, not used in production.
