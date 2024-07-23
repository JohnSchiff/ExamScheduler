from exam_scheduler import ExamScheduler
from utils import handle_course_code_value,filter_out_based_on_values 
import data_processing as dp
import pandas as pd

# משקל דינמי
# טבלה של קורסים עם הכי הרבה קוריסם חופפים וכמה מסלולים הוא נמצא

# בכל צד הוא בוחר את המשקל הדינמי הגבוה ביותר מבינהם אתזה עם מספר המסלולים הגבוה ביותר ומבינהם אתזה עם המשקל המקורי הקטן יותר

start_date = '2025-07-07'
end_moed_alef_date = '2025-08-08'
end_moed_bet_date = '2025-09-05'

limitiaons_file='limit_semester_b_tashpa.xlsx'


df_ifunim = dp.get_ifunim_dataframe_from_file('קובץ אפיונים.xlsx')
 
df_courses = dp.get_courses_dataframe_from_file('קובץ קורסים.xlsx')

# According to Orit 
# יש בקובץ הזה קורסים שאנחנו לא מתאמים להם בחינות והם לא מופיעים בקובץ אפיונים ששלחתי, לכן לא צריך לתאם להם מועדים. רק קורס שמופיע בקובץ אפיונים – צריך לתאם לו מועד.
# (אם יש קורס שמופיע באפיונים ולא מופיע בקובץ "כלכלה סמב תשפד" – סימן שיש בו עבודה ולכן לא צריך לתאם בחינה).
df = dp.merge_ifunim_and_coursim(df_ifunim, df_courses)

a = ExamScheduler(df, start_date=start_date, end_moed_alef_date=end_moed_alef_date,end_moed_bet_date=end_moed_bet_date, limitiaons_file=limitiaons_file)

a.schedule_exams()
# Validation
df = a.exam_schedule_table
for _, row in df.explode('code').iterrows():
    curernt_course = row['code']
    if pd.isna(curernt_course):
        continue
    current_date = row['date']
    crossed_courses = a.crossed_course_dict[curernt_course]
    date_range = pd.date_range(start=current_date - pd.Timedelta(days=3), end=current_date + pd.Timedelta(days=3))
    for date in date_range:
        courses_on_date = df[df['date'] == date]['code'].explode().tolist()
        # break
        for crossed_course in crossed_courses:
            if crossed_course in courses_on_date:
                raise ValueError(f'Conflict detected: Crossed course {crossed_course} on {date} conflicts with {curernt_course} on {current_date}')
        
a.exam_schedule_table.to_excel('test_exam_schedule.xlsx',index=False)
