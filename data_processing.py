import pandas as pd
from itertools import chain
import ast
from datetime import timedelta

ifunim_dict = {
    'אפיון': 'spec',
    'חדר': 'room',
    'אופן הוראה': 'teaching',
    'שם קורס': 'course_name',
    'מס\' קורס': 'course_code',
    'סמסטר': 'semester',
    'מס\'': 'num'
}

courses_file_dict = {
    'סוג מפגש': 'teaching',
    'רשומים': 'students',
    'שם': 'course_name',
    'קוד מלא': 'course_code',
    'תקופה': 'semester'
}

period_dict = {
    "סמסטר א'": 'א',
    "סמסטר ב'": 'ב',
    "שנתי": 'ש',
    'סמסטר קיץ': 'ק'
}


def get_ifunim_dataframe_from_file(file, semester):
    # Read Excel file headers is the second row (header=1)
    df = pd.read_excel(file, header=1)
    #  Rename columns to English
    df.columns = df.columns.map(ifunim_dict)
    # This method changes the course from string to int and drops nan.
    df = handle_course_code_value(df.copy())
    # Filter out תרגיל וסמינריון
    df = filter_out_based_on_values(df, col='teaching', values=['תרגיל', 'סמינריון', 'סדנה'])
    # Drop duplicates by code and if same semester, some courses can be in both semsters so we add prtoection
    df = df.drop_duplicates(subset=['course_code', 'semester'])
    if semester == 2:
        # Filter only Second semester
        df = df.loc[df['semester'] == 'ב']
    elif semester == 1:
        df = df.loc[df['semester'] == 'א']
    # Keep only relevant columns
    df = df[['spec', 'course_name', 'course_code', 'semester']].reset_index(drop=True)
    # Make list of specs instead of big string
    df['spec'] = df['spec'].str.split(',')

    # Convert to integer from float
    df['course_code'] = df['course_code'].astype(int)

    return df


def filter_out_based_on_values(df: pd.DataFrame, col: int | str, values: list) -> pd.DataFrame:
    if not isinstance(values, list):
        values = [values]
    df = df.loc[~ df[col].isin(values)]
    return df


def filter_out_shabbat(df):
    return df[df['date'].dt.day_name() != 'Saturday']


def handle_course_code_value(df):
    """
    Convert code from string to integer
    """
    kod = 'course_code'
    if kod not in df.columns:
        return print(f'must have {kod} column')
    # Get code course without sub-course, i.e the dash sign
    df[kod] = df[kod].str.split('-').str[0].str.strip()
    # Convert to numneric
    df[kod] = pd.to_numeric(df[kod], errors='coerce', downcast='integer')
    # Drop rows with No code for course
    df = df.dropna(subset=kod)
    # Convert from Float to Int
    df[kod] = df[kod].astype('Int32')
    return df


def get_all_courses_from_dict(courses_per_program_dict):
    all_courses = set(chain.from_iterable(courses_per_program_dict.values()))
    return all_courses


def get_courses_dataframe_from_file(file=None):
    if not file:
        print('No File input')
        return
    # Read Excel file, columns in first row (headers=0)
    df = pd.read_excel(file)

    # Rename columns to English
    df.columns = df.columns.map(courses_file_dict)

    # Get code course without sub-course, i.e the dash sign
    df = handle_course_code_value(df)
    # Filter out תרגיל וסמינריון
    df = filter_out_based_on_values(df, col='teaching', values=['תרגיל', 'סמינריון'])

    df['semester'] = df['semester'].replace(period_dict)

    if 'students' in df.columns:
        # Get total number os סטודנטים per course, maybe we will use it later
        df['num_of_students'] = df.groupby('course_code')['students'].transform('sum')
        # Keep relevant columns
        df = df[['course_code', 'num_of_students', 'semester']].drop_duplicates(
            subset='course_code').reset_index(drop=True)
    else:
        # Keep relevant columns         # Drop duplicates by code
        df = df[['course_code', 'semester']].drop_duplicates(subset='course_code').reset_index(drop=True)

    return df


def get_courses_per_program_dict(df):
    programs_dict = {}
    # Iterate all rows
    for index, row in df.iterrows():
        # Set key - the name of program
        for path in row['spec']:
            # Generate inital if not exists
            if path not in programs_dict:
                programs_dict[path] = []
            # If exists add course to program
            programs_dict[path].append(row['course_code'])
    return programs_dict


def parse_limit_files(limit_file):
    limit_file_cols_dict = {
        'סוף': 'end',
        'התחלה': 'start',
        'שם קורס': 'course_name',
        'קוד קורס': 'course',
        'ללא שישי': 'no_friday',
        'חסום': 'blocked'
    }
    df = pd.read_excel(limit_file, header=0)
    if 'ללא שישי' not in df.columns:
        df['ללא שישי'] = ''
    df.columns = [col.strip() for col in df.columns]
    df.columns = df.columns.map(limit_file_cols_dict)
    df['end'] = pd.to_datetime(df['end'], dayfirst=True)
    df['start'] = pd.to_datetime(df['start'], dayfirst=True)
    df = df.dropna(subset=['course'])
    return df


def parseMoedA(df, moedAfile):
    dfMoedA = pd.read_excel(moedAfile, header=0)
    dfMoedA['date'] = pd.to_datetime(dfMoedA['date'])
    dfMoedA['code'] = dfMoedA['code'].apply(ast.literal_eval)
    for _, row in dfMoedA.iterrows():
        date = row['date']
        codes = row['code']
        for course in codes:
            # Check if the course already exists in the result DataFrame
            if course in df['course'].values:
                # Update the date for the course
                df.loc[df['course'] == course, 'start'] = date + timedelta(days=25)
            else:
                # Add a new row for the course
                new_row = pd.DataFrame({'course': [course], 'start': [date + timedelta(days=25)]})
                df = pd.concat([df, new_row], ignore_index=True)
    return df


def get_limitations(fileName=None, moedAfile=None):
    if fileName is None:
        df = pd.DataFrame(columns=['course', 'course_name', 'start', 'end', 'no_friday', 'blocked'])
    else:
        df = parse_limit_files(fileName)
    if moedAfile is not None:  # moed2
        df = parseMoedA(df, moedAfile)
    return df


def filter_sunday_thursday(df, specified_date):
    specified_date = pd.to_datetime(specified_date)
    before_specified_date = df[df['date'] <= specified_date]
    after_specified_date = df[df['date'] > specified_date]
    # Filter the second part to include only Fridays
    only_sunday_thursday = after_specified_date[(after_specified_date['date'].dt.day_name() == 'Sunday') | (
        after_specified_date['date'].dt.day_name() == 'Thursday')]
    # Concatenate the two parts back together
    filtered_df = pd.concat([before_specified_date, only_sunday_thursday], ignore_index=True)

    return filtered_df


def gen_crossed_courses_dict_from_prog_dict(courses_per_program_dict: dict) -> dict:
    # Create a mapping from each course to all the courses that share a common course
    course_to_crossed_courses = {}

    # Iterate over each course list
    for program, courses_list in courses_per_program_dict.items():
        for course in courses_list:
            if course not in course_to_crossed_courses:
                course_to_crossed_courses[course] = set()

            # Add all other courses in the list to the set of crossed courses
            # Because an entry is a set, the items are unique.
            course_to_crossed_courses[course].update(courses_list)

    # Remove the course itself from its set of crossed courses
    for course, crossed_courses in course_to_crossed_courses.items():
        crossed_courses.discard(course)

    # Convert sets to lists for better readability
    course_to_crossed_courses = {course: list(crossed_courses)
                                 for course, crossed_courses in course_to_crossed_courses.items()}

    return course_to_crossed_courses
