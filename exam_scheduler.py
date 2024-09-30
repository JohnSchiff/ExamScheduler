import pandas as pd
import data_processing as dp
import math
from Logger import logger
from itertools import chain
from datetime import timedelta


class ExamScheduler:
    def __init__(self, df_ifunim, df_courses, limitations, start_date, end_date, gap=3, start_secondS=None):
        self.df_ifunim = df_ifunim
        self.df_courses = df_courses
        self.students_per_course_dict = dict(zip(df_courses['course_code'], df_courses['num_of_students']))
        self.df = dp.merge_ifunim_and_coursim(self.df_ifunim, self.df_courses)

        self.limitations = limitations
        self.no_friday_courses = self.limitations[self.limitations['no_friday']==1]['course'].values
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
        # when building the schedle we use courses_per_program_dict for deriving courses.
        self.all_courses = dp.get_all_courses_from_dict(self.courses_per_program_dict)

        # restrictions (replacing the blackList)
        self.restrictions_one_day = self.initialRestrictions(self.all_courses)
        self.restrictions_two_days = self.initialRestrictions(self.all_courses)
        self.restrictions_three_days = self.initialRestrictions(self.all_courses)

        self.code_dict = dict(zip(df_ifunim['course_code'], df_ifunim['course_name']))
        self.courses_to_place = list(df_ifunim['course_code'])

        # Create exam table with dates
        self.exam_schedule_table = self.create_exam_schedule_table()
        if start_secondS is not None:
            self.exam_schedule_table = dp.filter_sunday_thursday(self.exam_schedule_table, start_secondS)
        self.Ndates = len(self.exam_schedule_table)
        self.scheduled_courses = []
        self.maxAday = 1  # helps to spread the courses over the period

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
        if course_out_of_limit_file and not crowded and not any_exam_in_date:
            return True
        return False

    def least_strict_condition(self, row, course, program):
        current_date = row['date']
        course_out_of_limit_file = self.is_course_out_of_limit_file(current_date, course)
        crowded = self.count_courses_same_program_in_period(current_date, program, 1) >= 2
        not_too_many_exams = len(row['code']) < self.maxAday
        same_day_course_exists = self.count_courses_same_program_in_period(current_date, program, 0) > 0
        if course_out_of_limit_file and not crowded and not_too_many_exams and not same_day_course_exists:
            return True
        return False

    def schedule(self):
        """Schedule Moed A for the course."""
        programs = list(self.dynamic_dict.keys())
        # עבור כל מסלול במסלולים לפי הסדר
        for proN, program in enumerate(programs):
            if program in self.dynamic_dict and self.dynamic_dict[program] is not None:
                print(f"Program {proN} : {program}, Remained {len(self.dynamic_dict[program])}")

                for course in self.dynamic_dict[program]:
                    found = False
                    # print("looking for schedule: "+str(course))
                    for index, row in self.exam_schedule_table.iterrows():
                        if self.strict_condition_3_days(row, course):
                            self.put_exam_date(index, course, row['date'])
                            found = True
                            break

                    if not found:
                        for index, row in self.exam_schedule_table.iterrows():
                            if self.strict_condition_2_days(row, course):
                                self.put_exam_date(index, course, row['date'])
                                found = True
                                break

                    if not found:
                        for index, row in self.exam_schedule_table.iterrows():
                            if self.less_strict_condition(row, course, program):
                                self.put_exam_date(index, course, row['date'])
                                found = True
                                break

                    if not found:
                        for index, row in self.exam_schedule_table.iterrows():
                            if self.least_strict_condition(row, course, program):
                                self.put_exam_date(index, course, row['date'])
                                found = True
                                break

                    if not found:
                        print("Even brutality doesnt help for course "+str(course))

            if program in self.dynamic_dict and len(self.dynamic_dict[program]) > 0:
                msg = f'Scheduling {program} is impossible.\n It contains {len(self.courses_per_program_dict[program])} courses,available dates:{len(self.exam_schedule_table)}'
                print(msg)
                logger.add_remark(msg)

        if len(self.scheduled_courses) < len(self.courses_to_place):
            not_scheduled_courses = set(self.courses_to_place) - set(self.scheduled_courses)
            print(f'missing {len(not_scheduled_courses)} courses {list(not_scheduled_courses)}')
        # self.validate_exam_table(self.df_first_exam)
        self.prepare_results_to_export(self.exam_schedule_table)
        # self.df_first_exam
        self.arrangePrograms()
        return self.exam_schedule_table

    def put_exam_date(self, index, course, current_date):
        # print("List of "+str(current_date)+": "+str(row['code']))
        # print("Scheduling "+str(course)+" at "+str(current_date)+".")
        #  שבץ בטבלה של לוח המבחנים בעמודת "code"
        self.exam_schedule_table.at[index, 'code'].append(course)
        num_of_students_in_course = self.students_per_course_dict.get(course, 0)
        # תוסיף הערה בטבלת לוח המבחנים תחת עמודת "descriptions"
        self.exam_schedule_table.at[index, 'descriptions'].append(f'{course} - {num_of_students_in_course}')
        # הוסף קורס לרשימת קורסים ששובצו
        self.scheduled_courses.append(course)
        # מחק קורס מהמילון הדינמי
        self.remove_course_from_dynamic_dict(course)
        # תמחק מסלולים ריקים (אם יש)
        self.remove_empty_programs_from_dynamic_dict()
        # סדר את הרשימה שוב לפי המסלול הכי ארוך ובתוך כל מסלול לפי הקורס עם הכי הרבה קורסים חופפים
        # I dont think it is needed to resort every time.
        # self.sort_dynamic_dict()
        # עדכן את הרשימה השחורה
        self.update_restrictions(course, current_date)
        self.maxAday = math.floor(len(self.scheduled_courses)/self.Ndates)+2

    def is_course_out_of_limit_file(self, current_date, course):
        if course in self.no_friday_courses and current_date.weekday()==4:
            return False
        if course not in self.limitations['course'].values:
            return True
        row_course = self.limitations.loc[self.limitations.course == course]
        start_limit_date = row_course['start'].iloc[0]
        end_limit_date = row_course['end'].iloc[0]
        blocked_date = row_course['blocked'].iloc[0]
        limited_dates = pd.date_range(start=start_limit_date, end=end_limit_date)
        if current_date not in limited_dates and current_date != blocked_date:
            return True
        return False

    def _generate_dates_range(self):
        """
        Generate a range of dates from the start date to the end date.
        The end date is determined by the end_date if it exists,
        otherwise by the end_date.
        """
        end_date = self.end_date if self.end_date else self.end_date
        dates_range = pd.date_range(start=self.start_date, end=end_date)
        return dates_range

    def sort_courses_list_by_max_crossed_courses(self, program: list):
        """
        Sort the courses in a program based on the number of crossed courses.
        Courses with the highest number of crossed courses are listed first.

        :param program: List of courses in the program.
        :return: List of courses sorted by the number of crossed courses in descending order.
        """
        temp_dict = {}

        # Generate a dictionary of crossed courses from the dynamic_dict
        crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(self.dynamic_dict)

        # Count the number of crossed courses for each course in the program
        for course in program:
            temp_dict[course] = len(crossed_course_dict[course])

        # Sort the courses by the number of crossed courses (highest first)
        sorted_temp_dict = dict(sorted(temp_dict.items(), key=lambda item: item[1], reverse=True))
        sorted_courses_list = list(sorted_temp_dict.keys())

        return sorted_courses_list

    def sort_courses_by_num_of_students(self):
        """_summary_

        :param _type_ prog: _description_
        :return _type_: _description_
        """
        for program in self.courses_per_program_dict:
            courses_sorted_by_stuendts = sorted(self.courses_per_program_dict[program], key=lambda x: self.students_per_course_dict.get(x, 0), reverse=True)
            self.courses_per_program_dict[program] = courses_sorted_by_stuendts


    def sort_courses_inside_program(self):
        """
        Sort the courses inside each program in the dynamic_dict.
        The sorting is done based on the number of crossed courses.
        """
        for program in self.dynamic_dict:
            # Get the sorted list of courses for the current program
            sorted_courses = self.sort_courses_list_by_max_crossed_courses(self.dynamic_dict[program])
            # Update the program's course list with the sorted courses
            self.dynamic_dict[program] = sorted_courses

    def sort_programs_by_num_of_courses(self):
        """
        Sort the programs in dynamic_dict by the number of courses they have.
        Programs with the highest number of courses come first.
        """
        # Sort the programs by the number of courses (highest first)
        sorted_keys = sorted(self.dynamic_dict, key=lambda k: len(self.dynamic_dict[k]), reverse=False)
        # Create a new dictionary with the programs sorted by their number of courses
        dict_sorted_keys = {k: self.dynamic_dict[k] for k in sorted_keys}
        # Update dynamic_dict to the new sorted dictionary
        self.dynamic_dict = dict_sorted_keys

    def sort_dynamic_dict(self):
        """
        Perform a full sort of the dynamic_dict.
        First, programs are sorted by the number of courses.
        Then, courses inside each program are sorted by the number of crossed courses.
        """
        self.sort_programs_by_num_of_courses()
        # sort by number of students
        self.sort_courses_inside_program()

    def remove_course_from_dynamic_dict(self, course_to_remove):
        """
        Remove a specific course from all programs in dynamic_dict.

        :param course_to_remove: The course to be removed from the programs.
        """
        for path in self.dynamic_dict:
            # Remove the course from the list of courses in each program
            self.dynamic_dict[path] = [course for course in self.dynamic_dict[path] if course != course_to_remove]

    def remove_empty_programs_from_dynamic_dict(self):
        """
        Remove programs from dynamic_dict that have no courses left.
        """
        for program in list(self.dynamic_dict.keys()):
            if not self.dynamic_dict[program]:
                # Delete the program if its list of courses is empty
                del self.dynamic_dict[program]

    def create_exam_schedule_table(self):
        """
        Generate dataframe of possible dates for exams.
        """
        # Convert the date range to a list
        dates_range = self._generate_dates_range()
        # Show it as a DataFrame with column 'date'
        exam_schedule_table = pd.DataFrame(data=dates_range, columns=['date'])
        # Filter out Shabbat days
        exam_schedule_table = dp.filter_out_shabbat(exam_schedule_table)
        # Filter out excluded dates
        # Add column of exam with empty list
        exam_schedule_table['code'] = [[] for _ in range(len(exam_schedule_table))]
        # Add column of Comments with empty list
        exam_schedule_table['descriptions'] = [[] for _ in range(len(exam_schedule_table))]

        # dataframe for Moed A until (include) end of moed A
        # self.df_first_exam = exam_schedule_table.loc[exam_schedule_table.date<= pd.to_datetime(self.end_date)]
        if self.end_date is not None:
            # dataframe for Moed B starts day after end of moed A
            self.df_second_exam = exam_schedule_table.loc[exam_schedule_table.date > pd.to_datetime(self.end_date)]

        return exam_schedule_table

    def update_restrictions(self, course: int, current_date: str):
        crossed_courses = self.crossed_course_dict[course]
        # When there was no new crossed courses to add to blacklist
        if not crossed_courses:
            return
        # Iterate over the crossed courses
        for crossed_course in crossed_courses:
            # Check if it's not already in blacklist
            current_date_pd = pd.to_datetime(current_date)

            limit_days_period_one_day = pd.date_range(start=current_date_pd-pd.Timedelta(days=1),
                                                      end = current_date + pd.Timedelta(days=1))

            limit_days_period_two_days = pd.date_range(start=current_date_pd-pd.Timedelta(days=2),
                                                       end = current_date + pd.Timedelta(days=2))

            limit_days_period_three_days = pd.date_range(start=current_date_pd-pd.Timedelta(days=3),
                                                         end = current_date + pd.Timedelta(days=3))
            self.restrictions_one_day[crossed_course].update(limit_days_period_one_day)
            self.restrictions_two_days[crossed_course].update(limit_days_period_two_days)
            self.restrictions_three_days[crossed_course].update(limit_days_period_three_days)

        return

    def validate_exam_table(self, df):
        for _, row in df.explode('code').iterrows():
            curernt_course = row['code']
            if pd.isna(curernt_course):
                continue
            current_date = row['date']
            crossed_courses = self.crossed_course_dict[curernt_course]
            date_range = pd.date_range(start=current_date - pd.Timedelta(days=self.gap),
                                       end=current_date + pd.Timedelta(days=self.gap))
            for date in date_range:
                courses_on_date = df[df['date'] == date]['code'].explode().tolist()
                # break
                for crossed_course in crossed_courses:
                    if crossed_course in courses_on_date:
                        raise ValueError(
                            f'Conflict detected: Crossed course {crossed_course} on {date} conflicts with {curernt_course} on {current_date} gap: {self.gap}')

        print(f'gap of {self.gap} days is OK')

    def prepare_results_to_export(self, df):
        df = df.copy()
        df.loc[:, 'name'] = df['code'].apply(lambda x: [self.code_dict[code] for code in x])
        df = df[['descriptions', 'code', 'name', 'date']]
        # Change date timestamp to string
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        # Dict for Hebrew column
        result_table_dict = {
            'descriptions': 'הערות',
            'code': 'קוד קורס',
            'name': 'שם קורס',
            'date': 'תאריך',
        }

        # Rename columns to Hebrew
        df.columns = df.columns.map(result_table_dict)

        return df

    def initialRestrictions(self, allCourses):
        # Initializing the restircitons of all courses. Each course appears anyway.
        restrict = {}
        for course in allCourses:
            restrict[course] = set()
        return restrict

    def arrangePrograms(self):
        # Get the list of programs
        programs = list(self.courses_per_program_dict.keys())
        # Initialize the new DataFrame with 'date' and program columns
        columns = ['date'] + programs
        new_df = pd.DataFrame(columns=columns)
        # Iterate through each row in exam_schedule_table
        for _, row in self.exam_schedule_table.iterrows():
            date = row['date'].strftime('%Y-%m-%d')
            courses = row['code']
            # Create a dictionary to store courses for each program for the current date
            row_data = {'date': date}
            for course in courses:
                for program, program_courses in self.courses_per_program_dict.items():
                    if course in program_courses:
                        row_data[program] = course
            # # Convert lists to strings to avoid having lists in the DataFrame cells
            new_df = pd.concat([new_df, pd.DataFrame([row_data])], ignore_index=True)
        return new_df

    def count_courses_same_program_in_period(self, date, program, n_days):
        # Convert D to a datetime object if it's not already
        if isinstance(date, str):
            date = pd.to_datetime(date)

        # Get the list of courses for the given program P
        program_courses = self.courses_per_program_dict.get(program)

        # Calculate the start date of the period (k days before D)
        start_date = date - timedelta(days=n_days)
        end_date = date + timedelta(days=n_days)

        # Filter the schedule table to include only the dates in the specified period
        mask_dates = (self.exam_schedule_table['date'] >= start_date) & (self.exam_schedule_table['date'] <= end_date)
        filtered_schedule = self.exam_schedule_table[mask_dates]
        courses_in_period = list(chain.from_iterable(filtered_schedule.code.values.tolist()))
        count = len(set(courses_in_period).intersection(program_courses))

        return count
