import pandas as pd
from utils import handle_course_code_value, filter_out_based_on_values

# אפיונים
def get_ifunim_dataframe_from_file(file='כלכלה תשפד_רשימת מאפיינים לקורס.xlsx',semester=2):
    # Read Excel file headers is the second row (header=1)
    df = pd.read_excel(file, header=1)

    #  Shorten the column's names for convineince 
    df.rename(columns={'שם קורס':'שם','מס\' קורס':'קוד'},inplace=True)

    df = handle_course_code_value(df)

    # Filter out תרגיל וסמינריון 
    df = filter_out_based_on_values(df, col='אופן הוראה',values=['תרגיל','סמינריון'])

    # Drop duplicates by code
    df = df.drop_duplicates(subset='קוד')
    if semester==2:
        # Filter only Second semester
        df = df.loc[df['סמסטר'] =='ב']
    elif semester ==1:
        df = df.loc[df['סמסטר'] =='א']
        
    # Keep only relevant columns
    df = df[['אפיון','שם','קוד']].reset_index(drop=True)

    # Make list of instead of big string
    df['אפיון'] = df['אפיון'].str.split(',')

    # Convert to integer from float
    df['קוד'] = df['קוד'].astype(int)
    
    return df

# קובץ קורסים

def get_courses_dataframe_from_file(file='כלכלה סמב תשפד.xlsx'):
    # Read Excel file, columns in first row (headers=0)
    df = pd.read_excel(file, header=0)

    # Shorten the column's names for convineince 
    df.rename(columns={'קוד מלא':'קוד'},inplace=True)

    # Get code course without sub-course, i.e the dash sign
    df = handle_course_code_value(df)
    # Filter out תרגיל וסמינריון 
    df = filter_out_based_on_values(df, col='סוג מפגש',values=['תרגיל','סמינריון'])

    # Get total number os סטודנטים per course, maybe we will use it later
    df['סטודנטים'] = df.groupby('קוד')['לומדים'].transform('sum')

    # # Drop duplicates by code
    df.drop_duplicates(subset='קוד',inplace=True)

    # # Keep relevant columns 
    df = df [['קוד','סטודנטים']].reset_index(drop=True)
    
    return df

def merge_ifunim_and_coursim(df_ifunim, df_courses):
    df = pd.merge(df_ifunim,df_courses,on='קוד', how='left')

    # Replace NAN values with zero, and convert to integer
    df['סטודנטים'] = df['סטודנטים'].fillna(0).astype(int)

    return df

def get_courses_dict(df, key_str='קוד', path_col='אפיון'):
    # מילון מפתח קורסים
    courses_dict = {}
    # Iterate all rows 
    for index, row in df.iterrows():
        # Set key - the name of course 
        courses_dict[row[key_str]] = []
        for path in row[path_col]:
            courses_dict[row[key_str]].append(path)
            
    return courses_dict


def get_programs_dict(df):
    programs_dict = {}
    # Iterate all rows 
    for index, row in df.iterrows():
        # Set key - the name of program 
        for path in row['אפיון']:
            # Generate inital if not exists
            if path not in programs_dict:
                programs_dict[path] = []
            # If exists add course to program
            programs_dict[path].append(row['קוד'])
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
    before_specified_date = df[df['תאריך'] <= specified_date]
    after_specified_date = df[df['date'] > specified_date]
    # Filter the second part to include only Fridays
    only_sunday_thursday = after_specified_date[(after_specified_date['תאריך'].dt.day_name() == 'Sunday') | (after_specified_date['תאריך'].dt.day_name() == 'Thursday')]    
    # Concatenate the two parts back together
    filtered_df = pd.concat([before_specified_date, only_sunday_thursday], ignore_index=True)
    
    return filtered_df

def gen_crossed_courses_dict_from_prog_dict(program_dict):
    # Create a mapping from each course to all the courses that share a common course
    course_to_crossed_courses = {}

    # Iterate over each course list
    for key, course_list in program_dict.items():
        for course in course_list:
            if course not in course_to_crossed_courses:
                course_to_crossed_courses[course] = set()
            
            # Add all other courses in the list to the set of crossed courses
            course_to_crossed_courses[course].update(course_list)

    # Remove the course itself from its set of crossed courses
    for course, crossed_courses in course_to_crossed_courses.items():
        crossed_courses.discard(course)

    # Convert sets to lists for better readability
    course_to_crossed_courses = {course: list(crossed_courses) for course, crossed_courses in course_to_crossed_courses.items()}
    
    return course_to_crossed_courses