from exam_scheduler import ExamScheduler
import data_processing as dp
import pandas as pd



start_date = '2025-07-07'
end_moed_alef_date = '2025-08-08'
end_moed_bet_date = '2025-09-05'

limitiaons_file='limit_semester_b_tashpa.xlsx'


df_ifunim = dp.get_ifunim_dataframe_from_file('קובץ אפיונים.xlsx')
 

exam_scheduler = ExamScheduler(df_ifunim, start_date=start_date, end_moed_alef_date=end_moed_alef_date,end_moed_bet_date=end_moed_bet_date)

exam_scheduler.schedule_moed_a()

# Validation
exam_scheduler.df_first_exam.to_excel('test_exam_schedule.xlsx',index=False)
