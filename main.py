from exam_scheduler import ExamScheduler
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

df = dp.merge_ifunim_and_coursim(df_ifunim, df_courses)

a = ExamScheduler(df, start_date=start_date, end_moed_alef_date=end_moed_alef_date,end_moed_bet_date=end_moed_bet_date, limitiaons_file=limitiaons_file)

a.schedule_exams()


# Validation
# a.exam_schedule_table.to_excel('test_exam_schedule.xlsx',index=False)
