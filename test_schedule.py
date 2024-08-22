import unittest
import pandas as pd
from exam_scheduler import ExamScheduler
import data_processing as dp

class TestExamSchedule(unittest.TestCase):
    def setUp(self):
        # Load the generated exam schedule
        self.df = pd.read_excel('test_exam_schedule.xlsx')
        print('Hello')
    def test_no_blocked_courses(self):
        # Assuming 'Blocked Courses' is a list of blocked course codes
        blocked_courses = ["C002"]  # Replace with actual blocked courses
        for course in blocked_courses:
            self.assertNotIn(course, self.df['Course Code'].values, f"Blocked course {course} found in the schedule")

    # def test_dates_format(self):
    #     # Ensure dates are in the correct format (YYYY-MM-DD)
    #     for date in self.df['Date']:
    #         self.assertTrue(isinstance(date, pd.Timestamp), f"Date {date} is not in the correct format")

    # def test_gap_between_exams(self):
    #     # Ensure there is the required gap between exams
    #     self.df['Date'] = pd.to_datetime(self.df['Date'])
    #     self.df = self.df.sort_values(by='Date')
    #     date_diff = self.df['Date'].diff().dt.days
    #     self.assertTrue((date_diff[1:] >= 4).all(), "Less than 4 days gap between some exams")

if __name__ == "__main__":
    external_file='קובץ אילוצים.xlsx'

    df_ifunim = dp.get_ifunim_dataframe_from_file('קובץ אפיונים.xlsx')
    
    df_courses = dp.get_courses_dataframe_from_file('קובץ קורסים.xlsx')

    # According to Orit 
    # יש בקובץ הזה קורסים שאנחנו לא מתאמים להם בחינות והם לא מופיעים בקובץ אפיונים ששלחתי, לכן לא צריך לתאם להם מועדים. רק קורס שמופיע בקובץ אפיונים – צריך לתאם לו מועד.
    # (אם יש קורס שמופיע באפיונים ולא מופיע בקובץ "כלכלה סמב תשפד" – סימן שיש בו עבודה ולכן לא צריך לתאם בחינה).
    df = dp.merge_ifunim_and_coursim(df_ifunim, df_courses)

    a = ExamScheduler(df, external_file=external_file)

    a.schedule_exams()

    a.exam_schedule.to_excel('test_exam_schedule.xlsx')
    unittest.main()
