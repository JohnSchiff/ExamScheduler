import pandas as pd

ifunim_dict = {
'אפיון':'spec',
'חדר': 'room',
'אופן הוראה': 'teaching',
'שם קורס':'course_name',
'מס\' קורס':'course_code',
'סמסטר': 'semester',
'מס\'' : 'num'
            }

courses_file_dict = {
'סוג מפגש':'teaching',
'לומדים': 'students',
'שם': 'course_name',
'קוד מלא': 'course_code',
'תקופה': 'semester'
            }

period_dict = {
    "סמסטר א'": 'א',
    "סמסטר ב'":'ב',
    "שנתי" : 'ש',
    'סמסטר קיץ':'ק'
} 

def filter_out_based_on_values(df: pd.DataFrame, col: int|str, values: list) -> pd.DataFrame:
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
    # Ensure DataFrame is a copy to avoid issues with views
    df = df.copy()
    # Get code course without sub-course, i.e the dash sign
    df[kod] = df[kod].str.split('-').str[0].str.strip()
    # Convert to numneric
    df[kod] = pd.to_numeric(df[kod], errors='coerce', downcast='integer')
    # Drop rows with No code for course
    df = df.dropna(subset=kod)
    # Convert from Float to Int
    df[kod] = df[kod].astype('Int32')
    return df

# אפיונים
def get_ifunim_dataframe_from_file(file='כלכלה תשפד_רשימת מאפיינים לקורס.xlsx', semester=2):
    if not file:
        print('No File input')
        return
    # Read Excel file headers is the second row (header=1)
    df = pd.read_excel(file, header=1)

    #  Rename columns to English 
    df.columns = df.columns.map(ifunim_dict)

    df = handle_course_code_value(df)

    # Filter out תרגיל וסמינריון 
    df = filter_out_based_on_values(df, col='teaching',values=['תרגיל','סמינריון'])

    # Drop duplicates by code and if same semester, some courses can be in both semsters so we add prtoection
    df = df.drop_duplicates(subset=['course_code','semester'])
    
    if semester==2:
        # Filter only Second semester
        df = df.loc[df['semester'] =='ב']
    elif semester ==1:
        df = df.loc[df['semester'] =='א']
        
    # Keep only relevant columns
    df = df[['spec','course_name','course_code','semester']].reset_index(drop=True)

    # Make list of instead of big string
    df['spec'] = df['spec'].str.split(',')

    # Convert to integer from float
    df['course_code'] = df['course_code'].astype(int)
    
    return df

# קובץ קורסים

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
    df = filter_out_based_on_values(df, col='teaching',values=['תרגיל','סמינריון'])
    
    df['semester'] = df['semester'].replace(period_dict)

    if 'students' in df.columns:
        # Get total number os סטודנטים per course, maybe we will use it later
        df['num_of_students'] = df.groupby('course_code')['students'].transform('sum')
        # Keep relevant columns 
        df = df [['course_code','num_of_students','semester']].drop_duplicates(subset='course_code').reset_index(drop=True)    
    else:
        # Keep relevant columns         # Drop duplicates by code
        df = df [['course_code','semester']].drop_duplicates(subset='course_code').reset_index(drop=True)
    
    return df
    
def merge_ifunim_and_coursim(df_ifunim, df_courses):
    if len(df_courses) < len(df_ifunim):
        df = pd.merge(df_courses, df_ifunim, on=['course_code','semester'], how='left')
    else:
        df = pd.merge(df_ifunim, df_courses, on=['course_code','semester'], how='left')
    if 'num_of_students' in df.columns:
    # Replace NAN values with zero, and convert to integer
        df['num_of_students'] = df['num_of_students'].fillna(0).astype(int)
    return df


def get_programs_per_course_dict(df, key_str='course_code', path_col='spec'):
    # מילון מפתח קורסים
    courses_dict = {}
    # Iterate all rows 
    for index, row in df.iterrows():
        # Set key - the name of course 
        courses_dict[row[key_str]] = []
        for path in row[path_col]:
            courses_dict[row[key_str]].append(path)
    return courses_dict


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


def gen_list_of_dates_in_range(df)-> list:
    days_to_exclude = []
    for i, row in df.iterrows():
        start_date = row['start']
        end_date = row['end']
        days_to_exclude.extend(pd.date_range(start=start_date, end=end_date).tolist())
    return days_to_exclude


def parse_limit_files(limit_file):
    limit_file_cols_dict = {
    'סוף': 'end',
    'התחלה': 'start',
    'שם קורס': 'course_name',
    'קוד קורס': 'course'
                }
    df = pd.read_excel(limit_file, header=0)
    df.columns = [col.strip() for col in df.columns]
    df.columns = df.columns.map(limit_file_cols_dict)
    df['end'] = pd.to_datetime(df['end'],dayfirst=True)
    df['start'] = pd.to_datetime(df['start'],dayfirst=True)
    return df


def get_unavailable_dates_from_limit_file(limit_file=None):
    if limit_file is None:
        return 
    df = parse_limit_files(limit_file)
    all_courses = df.loc[df['course']=='*']
    days_to_exclude = gen_list_of_dates_in_range(all_courses)
    return days_to_exclude

    
def get_dict_of_blocked_dates_for_course_from_limitiaons_file(limit_file=None) -> dict:
    if limit_file is None:
        return {}
    df = parse_limit_files(limit_file)
    limit_dict = {}
    for i, row in df.iterrows():
        course = row['course']
        start = row['start']
        end = row['end']
    if not isinstance(course, str):
        limit_dict[course] = pd.date_range(start=start, end=end)
    return limit_dict 


def filter_sunday_thursday(df, specified_date):
    specified_date = pd.to_datetime(specified_date)
    before_specified_date = df[df['date'] <= specified_date]
    after_specified_date = df[df['date'] > specified_date]
    # Filter the second part to include only Fridays
    only_sunday_thursday = after_specified_date[(after_specified_date['date'].dt.day_name() == 'Sunday') | (after_specified_date['date'].dt.day_name() == 'Thursday')]    
    # Concatenate the two parts back together
    filtered_df = pd.concat([before_specified_date, only_sunday_thursday], ignore_index=True)
    
    return filtered_df


def gen_crossed_courses_dict_from_prog_dict(courses_per_program_dict:dict)-> dict:
    """_summary_

    :param _type_ courses_per_program_dict: _description_
    :return _type_: _description_
    """
    # Create a mapping from each course to all the courses that share a common course
    course_to_crossed_courses = {}

    # Iterate over each course list
    for program, courses_list in courses_per_program_dict.items():
        for course in courses_list:
            if course not in course_to_crossed_courses:
                course_to_crossed_courses[course] = set()
            
            # Add all other courses in the list to the set of crossed courses
            course_to_crossed_courses[course].update(courses_list)

    # Remove the course itself from its set of crossed courses
    for course, crossed_courses in course_to_crossed_courses.items():
        crossed_courses.discard(course)

    # Convert sets to lists for better readability
    course_to_crossed_courses = {course: list(crossed_courses) for course, crossed_courses in course_to_crossed_courses.items()}
    
    return course_to_crossed_courses


