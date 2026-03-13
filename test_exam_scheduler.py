import unittest
import pandas as pd
from datetime import datetime, timedelta
from exam_scheduler import ExamScheduler

class TestExamScheduler(unittest.TestCase):

    def setUp(self):
        # Minimal synthetic DataFrames matching the real constructor signature
        df_ifunim = pd.DataFrame({
            'course_code': [66101, 66867, 66826],
            'course_name': ['Course A', 'Course B', 'Course C'],
            'spec': [['P1'], ['P1'], ['P1']],
            'semester': [1, 1, 1],
        })
        df_courses = pd.DataFrame({
            'course_code': [66101, 66867, 66826],
            'semester': [1, 1, 1],
        })
        limitations = pd.DataFrame({
            'course': pd.Series([], dtype=int),
            'no_friday': pd.Series([], dtype=int),
            'start': pd.Series([], dtype=object),
            'end': pd.Series([], dtype=object),
            'blocked': pd.Series([], dtype=object),
        })
        self.scheduler = ExamScheduler(
            df_ifunim=df_ifunim,
            df_courses=df_courses,
            limitations=limitations,
            start_date='2024-08-01',
            end_date='2024-08-31',
            gap=3,
        )
        # Override crossed_course_dict for deterministic test cases
        self.scheduler.crossed_course_dict = {
            66101: [66867, 66826],
            66867: [66101],
            66826: [66101],
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


class TestScheduleQualityScore(unittest.TestCase):
    """Tests for the schedule quality scoring function."""

    def _make_scheduler(self, specs=None):
        """Helper to create a scheduler with configurable program structure."""
        if specs is None:
            specs = [['P1'], ['P1'], ['P1', 'P2'], ['P2']]
        codes = [10001 + i for i in range(len(specs))]
        names = [f'Course {chr(65+i)}' for i in range(len(specs))]

        df_ifunim = pd.DataFrame({
            'course_code': codes,
            'course_name': names,
            'spec': specs,
            'semester': [1] * len(codes),
        })
        df_courses = pd.DataFrame({
            'course_code': codes,
            'num_of_students': [100, 50, 200, 30],
            'semester': [1] * len(codes),
        })
        limitations = pd.DataFrame({
            'course': pd.Series([], dtype=int),
            'no_friday': pd.Series([], dtype=int),
            'start': pd.Series([], dtype=object),
            'end': pd.Series([], dtype=object),
            'blocked': pd.Series([], dtype=object),
        })
        return ExamScheduler(
            df_ifunim=df_ifunim,
            df_courses=df_courses,
            limitations=limitations,
            start_date='2024-08-01',
            end_date='2024-08-31',
            gap=3,
        )

    def test_quality_score_returns_float(self):
        scheduler = self._make_scheduler()
        score = scheduler.schedule_quality_score()
        self.assertIsInstance(score, float)

    def test_spaced_schedule_scores_higher_than_cramped(self):
        """A schedule with well-spaced exams should score higher than one
        where crossed courses are crammed together."""
        scheduler = self._make_scheduler()
        table = scheduler.exam_schedule_table

        # Spaced: put courses on well-separated dates
        indices = list(table.index)
        table.at[indices[0], 'code'] = [10001]
        table.at[indices[5], 'code'] = [10002]
        table.at[indices[10], 'code'] = [10003]
        table.at[indices[15], 'code'] = [10004]
        scheduler.scheduled_courses = [10001, 10002, 10003, 10004]
        spaced_score = scheduler.schedule_quality_score()

        # Reset
        for idx in indices:
            table.at[idx, 'code'] = []

        # Cramped: put all courses on consecutive days
        table.at[indices[0], 'code'] = [10001]
        table.at[indices[1], 'code'] = [10002]
        table.at[indices[2], 'code'] = [10003]
        table.at[indices[3], 'code'] = [10004]
        cramped_score = scheduler.schedule_quality_score()

        self.assertGreater(spaced_score, cramped_score)

    def test_schedule_produces_valid_result(self):
        """Full schedule run should produce a result with all courses placed."""
        scheduler = self._make_scheduler()
        scheduler.schedule()
        self.assertEqual(len(scheduler.scheduled_courses),
                         len(scheduler.courses_to_place))

    def test_local_search_does_not_break_schedule(self):
        """After local search, the schedule should still be valid."""
        scheduler = self._make_scheduler()
        scheduler.schedule()
        # validate_exam_table raises ValueError on conflict
        try:
            scheduler.validate_exam_table(scheduler.exam_schedule_table)
        except ValueError:
            self.fail("Schedule has conflicts after local search improvement")


class TestBestFitSelection(unittest.TestCase):
    """Tests for best-fit date selection."""

    def test_score_date_returns_float(self):
        df_ifunim = pd.DataFrame({
            'course_code': [101, 102],
            'course_name': ['A', 'B'],
            'spec': [['P1'], ['P1']],
            'semester': [1, 1],
        })
        df_courses = pd.DataFrame({
            'course_code': [101, 102],
            'num_of_students': [100, 50],
            'semester': [1, 1],
        })
        limitations = pd.DataFrame({
            'course': pd.Series([], dtype=int),
            'no_friday': pd.Series([], dtype=int),
            'start': pd.Series([], dtype=object),
            'end': pd.Series([], dtype=object),
            'blocked': pd.Series([], dtype=object),
        })
        scheduler = ExamScheduler(
            df_ifunim=df_ifunim,
            df_courses=df_courses,
            limitations=limitations,
            start_date='2024-08-01',
            end_date='2024-08-14',
            gap=3,
        )
        idx = scheduler.exam_schedule_table.index[0]
        row = scheduler.exam_schedule_table.iloc[0]
        score = scheduler._score_date(idx, row, 101, pass_level=0)
        self.assertIsInstance(score, float)


if __name__ == '__main__':
    unittest.main()
