import sys
import time
start_time = time.time()
from Logger import logger
from exam_scheduler import ExamScheduler
import pandas as pd
import data_processing as dp
from openpyxl import load_workbook

# Parameters ##################################################
start_semester1_moed1='2025-02-02'
end_semester1_moed1='2025-02-28'
start_semester1_moed2='2025-03-02'
end_semester1_moed2='2025-04-03'
start_semester2_moed1='2025-07-07'
end_semester2_moed1='2025-08-08'
start_semester2_moed2='2025-08-10'
end_semester2_moed2='2025-09-04'
second_semester_Start_Date='2025-03-16'
############################# IMPORTANT
semester=1
moed=1
logger.add_remark("Semester:"+str(semester)+", Moed:"+str(moed))
######################################                             
gap=3
############################ Files
charecteristics='characteristics.xlsx'
limitationsFile='קובץ אילוצים.xlsx'
coursesFile = 'קובץ קורסים.xlsx'
semester1moed1tableFile='exam_schedule_semester1_moed1.xlsx'
semester2moed1tableFile='exam_schedule_semester2_moed1.xlsx'
###########################################################################
### Initialazing Data
moed1F=None
secondStart=None

if semester==1 and moed==1: 
    start_date = start_semester1_moed1
    end_date = end_semester1_moed1
    sm='_semester1_moed1'
if semester==1 and moed==2:
    start_date = start_semester1_moed2
    end_date = end_semester1_moed2
    sm='_semester1_moed2'
    moed1F=semester1moed1tableFile
    secondStart=second_semester_Start_Date
if semester==2 and moed==1: 
    start_date = start_semester2_moed1
    end_date = end_semester2_moed1
    sm='_semester2_moed1'
if semester==2 and moed==2: 
    start_date = start_semester2_moed2
    end_date = end_semester2_moed2
    sm='_semester2_moed2'
    moed1F=semester2moed1tableFile
#######################################################33

# reading Data
df_ifunim = dp.get_ifunim_dataframe_from_file(charecteristics,semester)
df_courses = dp.get_courses_dataframe_from_file(coursesFile)
limitations=dp.get_limitations(limitationsFile,moed1F)
exam_scheduler = ExamScheduler(df_ifunim, df_courses, limitations, start_date, end_date,gap,secondStart)
exam_scheduler.schedule()
exams_per_programs=exam_scheduler.arrangePrograms()

# Validation Tests
courses_per_program_df = dp.get_courses_per_program_df(df_ifunim)
dp.saveDfToExcelFile(df_ifunim,'df_ifunim'+sm+'.xlsx')
dp.saveDfToExcelFile(courses_per_program_df,'programs'+sm+'.xlsx')
dp.saveDfToExcelFile(exam_scheduler.exam_schedule_table,'exam_schedule'+sm+'.xlsx')
dp.saveDfToExcelFile(exams_per_programs,'TablePerPrograms'+sm+'.xlsx')


end_time=time.time()
logger.add_remark("Running time:"+str(start_time-end_time))
logger.print_log()


