from exam_scheduler import ExamScheduler
from utils import handle_course_code_value,filter_out_based_on_values 
import data_processing as dp
import pandas as pd

# First courses to have exam in 
# first_courses = [66102,66214,66202]
# more_than_4_days_gap_courses = [66394,663921,661921,66282]

external_file='אילוצים.xlsx'

df_ifunim = dp.get_ifunim_dataframe_from_file()

df_courses = dp.get_courses_dataframe_from_file()

# According to Orit 
# יש בקובץ הזה קורסים שאנחנו לא מתאמים להם בחינות והם לא מופיעים בקובץ אפיונים ששלחתי, לכן לא צריך לתאם להם מועדים. רק קורס שמופיע בקובץ אפיונים – צריך לתאם לו מועד.
# (אם יש קורס שמופיע באפיונים ולא מופיע בקובץ "כלכלה סמב תשפד" – סימן שיש בו עבודה ולכן לא צריך לתאם בחינה).
df = dp.merge_ifunim_and_coursim(df_ifunim, df_courses)

a = ExamScheduler(df, external_file=external_file)

a.schedule_exams()

a.exam_schedule.to_excel('aaa.xlsx')