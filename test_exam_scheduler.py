import unittest
import pandas as pd
from datetime import datetime, timedelta
from exam_scheduler import ExamScheduler

class TestExamScheduler(unittest.TestCase):
    
    def setUp(self):
        # Set up the initial conditions for each test
        self.scheduler = ExamScheduler(data_from_files={}, gap=3)
        self.scheduler.crossed_course_dict = {
            66101: [66867, 66826],
            66867: [66101],
            66826: [66101]
        }
        self.df = pd.DataFrame({
            'date': [datetime(2024, 8, 1), datetime(2024, 8, 5), datetime(2024, 8, 10)],
            'code': [[66101], [66867], [66826]]
        })
    
    def test_no_conflicts(self):
        # Test case where there are no conflicts
        try:
            self.scheduler.validate_exam_table(self.df)
        except ValueError:
            self.fail("validate_exam_table() raised ValueError unexpectedly!")
    
    def test_with_conflicts(self):
        # Test case where there are conflicts
        self.df = pd.DataFrame({
            'date': [datetime(2024, 8, 1), datetime(2024, 8, 3), datetime(2024, 8, 10)],
            'code': [[66101], [66867], [66826]]
        })
        with self.assertRaises(ValueError):
            self.scheduler.validate_exam_table(self.df)
    
    def test_with_nan(self):
        # Test case with NaN values in the code column
        self.df = pd.DataFrame({
            'date': [datetime(2024, 8, 1), datetime(2024, 8, 3), datetime(2024, 8, 10)],
            'code': [[66101], [None], [66826]]
        })
        try:
            self.scheduler.validate_exam_table(self.df)
        except ValueError:
            self.fail("validate_exam_table() raised ValueError unexpectedly with NaN values!")
    
if __name__ == '__main__':
    unittest.main()
