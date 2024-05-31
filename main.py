from exam_scheduler import ExamScheduler
from utils import handle_course_code_value,filter_out_based_on_values 
from data_processing import *
import pandas as pd

# First courses to have exam in 
# first_courses = [66102,66214,66202]
# more_than_4_days_gap_courses = [66394,663921,661921,66282]

# Define the start and end dates
start_date = '2024-06-30'
end_date = '2024-09-12'

# List of dates to exclude based on word file (holidays, fast ...etc)
dates_to_exclude = ['2024-07-04','2024-07-05','2024-07-23',
                    '2024-07-24','2024-08-06','2024-08-06',
                    '2024-08-07','2024-08-08','2024-08-09',
                    '2024-08-13','2024-08-14','2024-08-25',
                    '2024-08-26','2024-08-27','2024-08-28',
                    '2024-08-29','2024-08-30','2024-09-02',
                    '2024-09-03','2024-09-10','2024-09-11',
                    '2024-09-12']

external_file='אילוצים.xlsx'

df = get_ifunim_dataframe()

df1 = get_courses_dataframe()

# According to Orit 
# יש בקובץ הזה קורסים שאנחנו לא מתאמים להם בחינות והם לא מופיעים בקובץ אפיונים ששלחתי, לכן לא צריך לתאם להם מועדים. רק קורס שמופיע בקובץ אפיונים – צריך לתאם לו מועד.
# (אם יש קורס שמופיע באפיונים ולא מופיע בקובץ "כלכלה סמב תשפד" – סימן שיש בו עבודה ולכן לא צריך לתאם בחינה).
df2 = pd.merge(df,df1,on='קוד', how='left')

# Replace NAN values with zero, and convert to integer
df2['students'] = df2['students'].fillna(0).astype(int)

courses_dict = get_courses_dict(df2)

code_dict = dict(zip(df2['קוד'], df2['שם']))
 
programs_dict = get_programs_dict(df2)

a = ExamScheduler(start_date, end_date, dates_to_exclude, courses_dict, programs_dict, code_dict, external_file= external_file)

df_exams = a.schedule_exams()

df_exams.to_excel('aaa.xlsx')