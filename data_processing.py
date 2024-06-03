import pandas as pd
from utils import handle_course_code_value, filter_out_based_on_values

# אפיונים
def get_ifunim_dataframe_from_file(file='כלכלה תשפד_רשימת מאפיינים לקורס.xlsx'):
    # Read Excel file headers is the second row (header=1)
    df = pd.read_excel(file, header=1)

    #  Shorten the column's names for convineince 
    df.rename(columns={'שם קורס':'שם','מס\' קורס':'קוד'},inplace=True)

    df = handle_course_code_value(df)

    # Filter out תרגיל וסמינריון 
    df = filter_out_based_on_values(df, col='אופן הוראה',values=['תרגיל','סמינריון'])

    # Drop duplicates by code
    df = df.drop_duplicates(subset='קוד')

    # Filter only Second semester
    df = df.loc[df['סמסטר'] =='ב']

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

    # Get total number os students per course, maybe we will use it later
    df['students'] = df.groupby('קוד')['לומדים'].transform('sum')

    # # Drop duplicates by code
    df.drop_duplicates(subset='קוד',inplace=True)

    # # Keep relevant columns 
    df = df [['קוד','students']].reset_index(drop=True)
    
    return df

def merge_ifunim_and_coursim(df_ifunim, df_courses):
    df = pd.merge(df_ifunim,df_courses,on='קוד', how='left')

    # Replace NAN values with zero, and convert to integer
    df['students'] = df['students'].fillna(0).astype(int)

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


def get_limitations_from_another_file(file:str):
    df = pd.read_excel(file)
    new_cols = {col: col.strip() for col in df.columns}
    df.rename(columns=new_cols, inplace=True)
    df.rename(columns={'קוד קורס':'קוד'},inplace=True)
    limit_dict = {}
    for i, row in df.iterrows():
        course = row['קוד']
        start = row['התחלה']
        end = row['סוף']
        limit_dict[course] = pd.date_range(start=start, end=end)
    return limit_dict
    