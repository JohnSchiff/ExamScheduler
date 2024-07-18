from exam_scheduler import ExamScheduler
from utils import handle_course_code_value,filter_out_based_on_values 
import data_processing as dp
import pandas as pd


start_date = '2025-07-07'
end_moed_alef_date = '2025-08-08'
end_moed_bet_date = '2025-09-04'

limitiaons_file='limit_semester_b_tashpa.xlsx'


df_ifunim = dp.get_ifunim_dataframe_from_file('קובץ אפיונים.xlsx')
 
df_courses = dp.get_courses_dataframe_from_file('קובץ קורסים.xlsx')

# According to Orit 
# יש בקובץ הזה קורסים שאנחנו לא מתאמים להם בחינות והם לא מופיעים בקובץ אפיונים ששלחתי, לכן לא צריך לתאם להם מועדים. רק קורס שמופיע בקובץ אפיונים – צריך לתאם לו מועד.
# (אם יש קורס שמופיע באפיונים ולא מופיע בקובץ "כלכלה סמב תשפד" – סימן שיש בו עבודה ולכן לא צריך לתאם בחינה).
df = dp.merge_ifunim_and_coursim(df_ifunim, df_courses)

a = ExamScheduler(df[0:5], start_date=start_date, end_moed_alef_date=end_moed_alef_date,end_moed_bet_date=end_moed_bet_date, limitiaons_file=limitiaons_file)

a.schedule_exams()

a.exam_schedule_table.to_excel('test_exam_schedule.xlsx')
