import pandas as pd
import data_processing as dp
import math
from itertools import chain
from datetime import timedelta
from Logger import logger


class ExamScheduler:
    def __init__(self, df_ifunim, df_courses, limitations, start_date, end_date, gap=3, start_secondS=None):
        self.df_ifunim = df_ifunim
        self.df_courses = df_courses
        if 'num_of_students' in df_courses.columns:
            self.students_per_course_dict = dict(zip(df_courses['course_code'], df_courses['num_of_students']))
        else:
            self.students_per_course_dict = {code: 0 for code in df_courses['course_code']}
        self.df = dp.merge_ifunim_and_coursim(self.df_ifunim, self.df_courses)

        self.limitations = limitations
        self.no_friday_courses = self.limitations[self.limitations['no_friday'] == 1]['course'].values
        ## Dates ##
        self.start_date = start_date
        self.end_date = end_date
        self.gap = gap
        self.courses_per_program_dict = dp.get_courses_per_program_dict(df_ifunim)
        self.sort_courses_by_num_of_students()
        self.dynamic_dict = self.courses_per_program_dict.copy()
        self.crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(
            self.courses_per_program_dict)  # Example 66101: [66867, 66826, 66827...]
        # Generate dynamic dict
        self.sort_dynamic_dict()
        # when building the schedule we use courses_per_program_dict for deriving courses.
        self.all_courses = dp.get_all_courses_from_dict(self.courses_per_program_dict)

        # restrictions (replacing the blackList)
        self.restrictions_one_day = self.initialRestrictions(self.all_courses)
        self.restrictions_two_days = self.initialRestrictions(self.all_courses)
        self.restrictions_three_days = self.initialRestrictions(self.all_courses)

        self.code_dict = dict(zip(df_ifunim['course_code'], df_ifunim['course_name']))
        self.courses_to_place = list(df_ifunim['course_code'])

        # Build reverse lookup: course -> list of programs it belongs to
        self._course_to_programs = {}
        for program, courses in self.courses_per_program_dict.items():
            for course in courses:
                self._course_to_programs.setdefault(course, []).append(program)

        # Create exam table with dates
        self.exam_schedule_table = self.create_exam_schedule_table()
        if start_secondS is not None:
            self.exam_schedule_table = dp.filter_sunday_thursday(self.exam_schedule_table, start_secondS)
        self.Ndates = len(self.exam_schedule_table)
        self.scheduled_courses = []
        self.maxAday = 1  # helps to spread the courses over the period

        # Build a date->index lookup for fast access
        self._date_to_index = {}
        for idx, row in self.exam_schedule_table.iterrows():
            self._date_to_index[row['date']] = idx

    def strict_condition_3_days(self, row, course):
        current_date = row['date']
        course_out_of_limit_file = self.is_course_out_of_limit_file(current_date, course)
        cond_three_days_gap = current_date not in self.restrictions_three_days[course]
        not_too_many_exams = len(row['code']) < self.maxAday
        if course_out_of_limit_file and cond_three_days_gap and not_too_many_exams:
            return True
        return False

    def strict_condition_2_days(self, row, course):
        current_date = row['date']
        course_out_of_limit_file = self.is_course_out_of_limit_file(current_date, course)
        cond_two_days_gap = current_date not in self.restrictions_two_days[course]
        not_too_many_exams = len(row['code']) < self.maxAday
        if course_out_of_limit_file and cond_two_days_gap and not_too_many_exams:
            return True
        return False

    def less_strict_condition(self, row, course, program):
        current_date = row['date']
        course_out_of_limit_file = self.is_course_out_of_limit_file(current_date, course)
        crowded = self.count_courses_same_program_in_period(current_date, program, 1) >= 2
        any_exam_in_date = row['code']
        cond_one_day_gap = current_date not in self.restrictions_one_day[course]
        if course_out_of_limit_file and not crowded and not any_exam_in_date and cond_one_day_gap:
            return True
        return False

    def least_strict_condition(self, row, course, program):
        current_date = row['date']
        course_out_of_limit_file = self.is_course_out_of_limit_file(current_date, course)
        crowded = self.count_courses_same_program_in_period(current_date, program, 1) >= 2
        not_too_many_exams = len(row['code']) < self.maxAday
        same_day_course_exists = self.count_courses_same_program_in_period(current_date, program, 0) > 0
        crossed_same_day = bool(set(row['code']).intersection(self.crossed_course_dict.get(course, [])))
        if (course_out_of_limit_file and not crowded and not_too_many_exams
                and not same_day_course_exists and not crossed_same_day):
            return True
        return False

    def _score_date(self, index, row, course, pass_level):
        """Score a candidate date for a course. Higher is better.

        Considers:
        - Distance from crossed courses (more distance = better)
        - Number of exams already on this date (fewer = better)
        - Student load on this date (fewer students = better)
        - How centered the date is in the schedule (prefer middle dates to leave room)
        """
        current_date = row['date']
        score = 0.0

        # 1. Minimum distance to any crossed course's scheduled exam
        crossed = self.crossed_course_dict.get(course, [])
        if crossed:
            min_dist = float('inf')
            has_scheduled_crossed = False
            for crossed_course in crossed:
                if crossed_course in self.scheduled_courses:
                    has_scheduled_crossed = True
                    # Find the date of the crossed course
                    for _, srow in self.exam_schedule_table.iterrows():
                        if crossed_course in srow['code']:
                            dist = abs((current_date - srow['date']).days)
                            min_dist = min(min_dist, dist)
                            break
            if has_scheduled_crossed:
                score += min_dist * 10  # Heavily reward distance from conflicts

        # 2. Fewer exams on the same day is better
        exams_on_day = len(row['code'])
        score -= exams_on_day * 5

        # 3. Fewer students already on this day is better
        students_on_day = sum(self.students_per_course_dict.get(c, 0) for c in row['code'])
        score -= students_on_day * 0.01

        # 4. In early passes, prefer dates that leave room at edges
        total_dates = len(self.exam_schedule_table)
        if total_dates > 0:
            position = list(self.exam_schedule_table.index).index(index)
            center_ratio = 1.0 - abs(2.0 * position / total_dates - 1.0)
            score += center_ratio * 2

        return score

    def _find_best_date(self, course, condition_fn, condition_args, pass_level):
        """Find the best valid date for a course using scoring instead of first-fit.

        For pass levels 0-1 (strict conditions), evaluate all valid dates and pick the best.
        For pass levels 2-3 (relaxed conditions), still take first-fit to avoid
        placing difficult courses on suboptimal dates when options are very limited.
        """
        if pass_level >= 2:
            # Relaxed passes: first-fit (options are scarce, just place it)
            for index, row in self.exam_schedule_table.iterrows():
                if condition_fn(row, *condition_args):
                    return index, row
            return None, None

        # Strict passes: best-fit
        best_score = float('-inf')
        best_index = None
        best_row = None

        for index, row in self.exam_schedule_table.iterrows():
            if condition_fn(row, *condition_args):
                score = self._score_date(index, row, course, pass_level)
                if score > best_score:
                    best_score = score
                    best_index = index
                    best_row = row

        return best_index, best_row

    def schedule(self):
        """Schedule exams for all courses using a multi-pass greedy algorithm
        followed by a local search improvement phase."""
        programs = list(self.dynamic_dict.keys())
        for proN, program in enumerate(programs):
            if program in self.dynamic_dict and self.dynamic_dict[program] is not None:
                logger.add_remark(f"Program {proN} : {program}, Remained {len(self.dynamic_dict[program])}")

                for course in self.dynamic_dict[program]:
                    found = False

                    # Pass 1: 3-day gap, best-fit
                    index, row = self._find_best_date(
                        course, self.strict_condition_3_days, (course,), pass_level=0)
                    if index is not None:
                        self.put_exam_date(index, course, row['date'])
                        found = True

                    # Pass 2: 2-day gap, best-fit
                    if not found:
                        index, row = self._find_best_date(
                            course, self.strict_condition_2_days, (course,), pass_level=1)
                        if index is not None:
                            self.put_exam_date(index, course, row['date'])
                            found = True

                    # Pass 3: less strict, first-fit
                    if not found:
                        index, row = self._find_best_date(
                            course, self.less_strict_condition, (course, program), pass_level=2)
                        if index is not None:
                            self.put_exam_date(index, course, row['date'])
                            found = True

                    # Pass 4: least strict, first-fit
                    if not found:
                        index, row = self._find_best_date(
                            course, self.least_strict_condition, (course, program), pass_level=3)
                        if index is not None:
                            self.put_exam_date(index, course, row['date'])
                            found = True

                    if not found:
                        logger.add_remark(f"Could not schedule course {course}")

            if program in self.dynamic_dict and len(self.dynamic_dict[program]) > 0:
                msg = (f'Scheduling {program} is impossible. '
                       f'It contains {len(self.courses_per_program_dict[program])} courses, '
                       f'available dates: {len(self.exam_schedule_table)}')
                logger.add_remark(msg)

        if len(self.scheduled_courses) < len(self.courses_to_place):
            not_scheduled_courses = set(self.courses_to_place) - set(self.scheduled_courses)
            logger.add_remark(f'Missing {len(not_scheduled_courses)} courses: {list(not_scheduled_courses)}')

        # Local search improvement phase
        self._improve_schedule()

        try:
            self.validate_exam_table(self.exam_schedule_table)
        except ValueError as e:
            logger.add_remark(f'WARNING: schedule contains conflicts: {e}')

        self.programs_table = self.arrangePrograms()
        return self.exam_schedule_table

    def _improve_schedule(self, max_iterations=50):
        """Local search: try moving each course to a better date.

        Repeatedly scans all scheduled courses and attempts to move each one
        to a date that improves the overall schedule quality score.
        Stops when no improvement is found or max_iterations is reached.
        """
        for iteration in range(max_iterations):
            improved = False
            current_score = self.schedule_quality_score()

            for course in list(self.scheduled_courses):
                # Find current date of this course
                current_index = None
                current_date = None
                for idx, row in self.exam_schedule_table.iterrows():
                    if course in row['code']:
                        current_index = idx
                        current_date = row['date']
                        break

                if current_index is None:
                    continue

                # Try moving to every other valid date
                best_new_index = None
                best_new_score = current_score

                for candidate_idx, candidate_row in self.exam_schedule_table.iterrows():
                    if candidate_idx == current_index:
                        continue

                    candidate_date = candidate_row['date']

                    # Check basic validity: limitation file constraints
                    if not self.is_course_out_of_limit_file(candidate_date, course):
                        continue

                    # Check no crossed course on same day
                    crossed_same_day = bool(
                        set(candidate_row['code']).intersection(
                            self.crossed_course_dict.get(course, [])))
                    if crossed_same_day:
                        continue

                    # Check no same-program course on same day
                    programs_for_course = self._course_to_programs.get(course, [])
                    same_program_conflict = False
                    for prog in programs_for_course:
                        prog_courses = self.courses_per_program_dict.get(prog, [])
                        if any(c in candidate_row['code'] for c in prog_courses if c != course):
                            same_program_conflict = True
                            break
                    if same_program_conflict:
                        continue

                    # Tentatively move: remove from old, add to new
                    self.exam_schedule_table.at[current_index, 'code'].remove(course)
                    self.exam_schedule_table.at[candidate_idx, 'code'].append(course)

                    new_score = self.schedule_quality_score()

                    # Undo the move
                    self.exam_schedule_table.at[candidate_idx, 'code'].remove(course)
                    self.exam_schedule_table.at[current_index, 'code'].append(course)

                    if new_score > best_new_score:
                        best_new_score = new_score
                        best_new_index = candidate_idx

                # Apply the best move if found
                if best_new_index is not None:
                    self.exam_schedule_table.at[current_index, 'code'].remove(course)
                    old_desc = [d for d in self.exam_schedule_table.at[current_index, 'descriptions']
                                if str(course) in str(d)]
                    for d in old_desc:
                        self.exam_schedule_table.at[current_index, 'descriptions'].remove(d)

                    self.exam_schedule_table.at[best_new_index, 'code'].append(course)
                    self.exam_schedule_table.at[best_new_index, 'descriptions'].append(
                        f'{course} - {self.code_dict.get(course, "")}')

                    improved = True

            if not improved:
                logger.add_remark(f'Local search converged after {iteration + 1} iterations')
                break
        else:
            logger.add_remark(f'Local search stopped after {max_iterations} iterations')

    def schedule_quality_score(self):
        """Compute a numeric quality score for the current schedule. Higher is better.

        Components:
        - Gap score: sum of minimum distances between crossed courses (reward spacing)
        - Load balance: penalize days with many exams or many students
        - Program crowding: penalize same-program exams within 1 day of each other
        """
        score = 0.0

        # Build a course -> date lookup
        course_dates = {}
        for _, row in self.exam_schedule_table.iterrows():
            for course in row['code']:
                course_dates[course] = row['date']

        # 1. Gap score: reward distance between crossed courses
        counted_pairs = set()
        for course, crossed_list in self.crossed_course_dict.items():
            if course not in course_dates:
                continue
            for crossed in crossed_list:
                if crossed not in course_dates:
                    continue
                pair = (min(course, crossed), max(course, crossed))
                if pair in counted_pairs:
                    continue
                counted_pairs.add(pair)
                dist = abs((course_dates[course] - course_dates[crossed]).days)
                # Reward up to gap days, diminishing returns beyond
                score += min(dist, self.gap * 2)

        # 2. Load balance: penalize variance in exams per day
        exams_per_day = [len(row['code']) for _, row in self.exam_schedule_table.iterrows()
                         if row['code']]
        if exams_per_day:
            avg = sum(exams_per_day) / len(exams_per_day)
            variance = sum((x - avg) ** 2 for x in exams_per_day) / len(exams_per_day)
            score -= variance * 2

        # 3. Student load balance: penalize days with too many students
        for _, row in self.exam_schedule_table.iterrows():
            students = sum(self.students_per_course_dict.get(c, 0) for c in row['code'])
            if students > 0:
                # Penalize quadratically for high-load days
                score -= (students / 100) ** 2

        # 4. Program crowding: penalize same-program exams within 1 day
        for program, prog_courses in self.courses_per_program_dict.items():
            prog_dates = sorted([course_dates[c] for c in prog_courses if c in course_dates])
            for i in range(len(prog_dates) - 1):
                gap_days = (prog_dates[i + 1] - prog_dates[i]).days
                if gap_days <= 1:
                    score -= 10  # heavy penalty for back-to-back
                elif gap_days == 2:
                    score -= 3   # mild penalty for 2-day gap

        return score

    def put_exam_date(self, index, course, current_date):
        self.exam_schedule_table.at[index, 'code'].append(course)
        self.exam_schedule_table.at[index, 'descriptions'].append(
            f'{course} - {self.code_dict[course]}')
        self.scheduled_courses.append(course)
        self.remove_course_from_dynamic_dict(course)
        self.remove_empty_programs_from_dynamic_dict()
        self.update_restrictions(course, current_date)
        self.maxAday = self._compute_max_per_day()

    def _compute_max_per_day(self):
        """Compute max exams per day based on scheduled count and student capacity."""
        base = math.floor(len(self.scheduled_courses) / self.Ndates) + 2
        return base

    def is_course_out_of_limit_file(self, current_date, course):
        if course in self.no_friday_courses and current_date.weekday() == 4:
            return False
        if course not in self.limitations['course'].values:
            return True
        row_course = self.limitations.loc[self.limitations.course == course]
        start_limit_date = row_course['start'].iloc[0]
        end_limit_date   = row_course['end'].iloc[0]
        blocked_date     = row_course['blocked'].iloc[0]
        if not pd.isna(blocked_date) and current_date == pd.Timestamp(blocked_date):
            return False
        if not pd.isna(start_limit_date) and current_date < pd.Timestamp(start_limit_date):
            return False
        if not pd.isna(end_limit_date) and current_date > pd.Timestamp(end_limit_date):
            return False
        return True

    def _generate_dates_range(self):
        """Generate a range of dates from the start date to the end date."""
        dates_range = pd.date_range(start=self.start_date, end=self.end_date)
        return dates_range

    def sort_courses_list_by_max_crossed_courses(self, program: list):
        """Sort courses in a program by number of crossed courses (highest first)."""
        crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(self.dynamic_dict)
        temp_dict = {}
        for course in program:
            temp_dict[course] = len(crossed_course_dict.get(course, []))
        sorted_temp_dict = dict(sorted(temp_dict.items(), key=lambda item: item[1], reverse=True))
        return list(sorted_temp_dict.keys())

    def sort_courses_by_num_of_students(self):
        for program in self.courses_per_program_dict:
            courses_sorted_by_students = sorted(
                self.courses_per_program_dict[program],
                key=lambda x: self.students_per_course_dict.get(x, 0),
                reverse=True)
            self.courses_per_program_dict[program] = courses_sorted_by_students

    def sort_courses_inside_program(self):
        """Sort courses inside each program by number of crossed courses."""
        for program in self.dynamic_dict:
            sorted_courses = self.sort_courses_list_by_max_crossed_courses(self.dynamic_dict[program])
            self.dynamic_dict[program] = sorted_courses

    def sort_programs_by_num_of_courses(self):
        """Sort programs by number of courses (highest first)."""
        sorted_keys = sorted(self.dynamic_dict, key=lambda k: len(self.dynamic_dict[k]), reverse=True)
        self.dynamic_dict = {k: self.dynamic_dict[k] for k in sorted_keys}

    def sort_dynamic_dict(self):
        """Sort programs by size, then courses within each program by constraints."""
        self.sort_programs_by_num_of_courses()
        self.sort_courses_inside_program()

    def remove_course_from_dynamic_dict(self, course_to_remove):
        for path in self.dynamic_dict:
            self.dynamic_dict[path] = [c for c in self.dynamic_dict[path] if c != course_to_remove]

    def remove_empty_programs_from_dynamic_dict(self):
        for program in list(self.dynamic_dict.keys()):
            if not self.dynamic_dict[program]:
                del self.dynamic_dict[program]

    def create_exam_schedule_table(self):
        """Generate dataframe of possible dates for exams."""
        dates_range = self._generate_dates_range()
        exam_schedule_table = pd.DataFrame(data=dates_range, columns=['date'])
        exam_schedule_table = dp.filter_out_shabbat(exam_schedule_table)
        exam_schedule_table['code'] = [[] for _ in range(len(exam_schedule_table))]
        exam_schedule_table['descriptions'] = [[] for _ in range(len(exam_schedule_table))]

        if self.end_date is not None:
            self.df_second_exam = exam_schedule_table.loc[
                exam_schedule_table.date > pd.to_datetime(self.end_date)]

        return exam_schedule_table

    def update_restrictions(self, course: int, current_date):
        crossed_courses = self.crossed_course_dict[course]
        if not crossed_courses:
            return

        current_date_pd = pd.to_datetime(current_date)

        for crossed_course in crossed_courses:
            limit_days_period_one_day = pd.date_range(
                start=current_date_pd - pd.Timedelta(days=1),
                end=current_date_pd + pd.Timedelta(days=1))

            limit_days_period_two_days = pd.date_range(
                start=current_date_pd - pd.Timedelta(days=2),
                end=current_date_pd + pd.Timedelta(days=2))

            limit_days_period_three_days = pd.date_range(
                start=current_date_pd - pd.Timedelta(days=3),
                end=current_date_pd + pd.Timedelta(days=3))

            self.restrictions_one_day[crossed_course].update(limit_days_period_one_day)
            self.restrictions_two_days[crossed_course].update(limit_days_period_two_days)
            self.restrictions_three_days[crossed_course].update(limit_days_period_three_days)

    def validate_exam_table(self, df):
        for _, row in df.explode('code').iterrows():
            current_course = row['code']
            if pd.isna(current_course):
                continue
            current_date = row['date']
            crossed_courses = self.crossed_course_dict[current_course]
            date_range = pd.date_range(start=current_date - pd.Timedelta(days=self.gap),
                                       end=current_date + pd.Timedelta(days=self.gap))
            for check_date in date_range:
                courses_on_date = df[df['date'] == check_date]['code'].explode().tolist()
                for crossed_course in crossed_courses:
                    if crossed_course in courses_on_date:
                        raise ValueError(
                            f'Conflict detected: Crossed course {crossed_course} on {check_date} '
                            f'conflicts with {current_course} on {current_date} gap: {self.gap}')

        logger.add_remark(f'Validation passed: gap of {self.gap} days is OK')

    def prepare_results_to_export(self, df):
        df = df.copy()
        df.loc[:, 'name'] = df['code'].apply(lambda x: [self.code_dict[code] for code in x])
        df = df[['descriptions', 'code', 'name', 'date']]
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        result_table_dict = {
            'descriptions': 'הערות',
            'code': 'קוד קורס',
            'name': 'שם קורס',
            'date': 'תאריך',
        }
        df.columns = df.columns.map(result_table_dict)
        return df

    def initialRestrictions(self, allCourses):
        restrict = {}
        for course in allCourses:
            restrict[course] = set()
        return restrict

    def arrangePrograms(self):
        programs = list(self.courses_per_program_dict.keys())
        rows = []
        for _, row in self.exam_schedule_table.iterrows():
            date = row['date'].strftime('%Y-%m-%d')
            row_data = {'date': date}
            for course in row['code']:
                for program, program_courses in self.courses_per_program_dict.items():
                    if course in program_courses:
                        row_data[program] = course
            rows.append(row_data)
        return pd.DataFrame(rows, columns=['date'] + programs)

    def count_courses_same_program_in_period(self, date, program, n_days):
        if isinstance(date, str):
            date = pd.to_datetime(date)

        program_courses = self.courses_per_program_dict.get(program)
        start_date = date - timedelta(days=n_days)
        end_date = date + timedelta(days=n_days)

        mask_dates = ((self.exam_schedule_table['date'] >= start_date) &
                      (self.exam_schedule_table['date'] <= end_date))
        filtered_schedule = self.exam_schedule_table[mask_dates]
        courses_in_period = list(chain.from_iterable(filtered_schedule.code.values.tolist()))
        count = len(set(courses_in_period).intersection(program_courses))

        return count
