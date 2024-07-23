import pandas as pd
from datetime import timedelta
import data_processing as dp



class ExamScheduler:
    def __init__(self, data_from_files, start_date,
                 end_moed_alef_date,end_moed_bet_date=None,semester=2,
                 limitiaons_file=None, start_of_semester2_date=None, moed_c=False,gap=4):

        ## Dates ##
        self.start_date = start_date
        self.end_moed_alef_date = end_moed_alef_date 
        self.end_moed_bet_date = end_moed_bet_date 
        self.start_of_semester2_date = start_of_semester2_date
        self.days_gap_between_moed_b = 28
        self.semester = semester
        self.moed_c = moed_c
        # Data files
        self.data_from_files = data_from_files
        self.limitiaons_file = limitiaons_file
        
        self.courses_dict =  dp.get_courses_dict(data_from_files)
        self.programs_dict = dp.get_programs_dict(data_from_files)
        self.crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(self.programs_dict)
        self.code_dict = dict(zip(data_from_files['course_code'], data_from_files['course_name']))
        self.courses_to_place = list(data_from_files['course_code'])
        self.scheduled_courses = []
        # Gen exam tables
        self.blocked_dates_dict  = dp.get_dict_of_blocked_dates_for_course_from_limitiaons_file(self.limitiaons_file)
        
        self.dates_to_exclude = dp.get_unavailable_dates_from_limit_file(self.limitiaons_file)
        self.exam_schedule_table = self.create_exam_schedule_table()
        self.moed_a_scheduled = []
        self.moed_b_scheduled = []
        self.gap = gap
    def create_exam_schedule_table(self):
        """  
        Generate dataframe of possible dates for exams.
        """
        # Convert the date range to a list
        if self.end_moed_bet_date is not None:
            dates_range = pd.date_range(start=self.start_date, end=self.end_moed_bet_date)
        else:
            dates_range = pd.date_range(start=self.start_date, end=self.end_moed_alef_date)
        # Show it as a DataFrame with column 'date'    
        exam_schedule_table = pd.DataFrame(data=dates_range, columns=['date'])
        # Filter out Shabbat days
        exam_schedule_table = exam_schedule_table[exam_schedule_table['date'].dt.day_name() != 'Saturday']
        if self.moed_c:
            exam_schedule_table = exam_schedule_table[(exam_schedule_table['date'].dt.day_name() == 'Sunday') | (exam_schedule_table['date'].dt.day_name() == 'Thursday')]
        # Filter out excluded dates
        if self.dates_to_exclude:
            exam_schedule_table = exam_schedule_table[~exam_schedule_table['date'].isin(self.dates_to_exclude)].reset_index(drop=True)
        if self.semester == 1:
            exam_schedule_table = dp.filter_sunday_thursday(exam_schedule_table, self.start_of_semester2_date)
        # Add column of exam with empty list  
        exam_schedule_table['code'] = [[] for _ in range(len(exam_schedule_table))]
        # Add column of Comments with empty list  
        exam_schedule_table['descriptions'] = [[] for _ in range(len(exam_schedule_table))]
        
        self.df_first_exam = exam_schedule_table.loc[exam_schedule_table.date<= pd.to_datetime(self.end_moed_alef_date)]
        if self.end_moed_bet_date is not None:
            self.df_second_exam =exam_schedule_table.loc[exam_schedule_table.date> pd.to_datetime(self.end_moed_alef_date)]
        # Fix format
        # exam_schedule_table['date'] = exam_schedule_table['date'].dt.strftime('%Y-%m-%d')
        return exam_schedule_table   
        
    def get_course(self, current_date: str)-> str | None:
        """
        Choose a course from the list of courses to place and check if it fits well with the given date.
        If no course fits, return None.

        Args:
            current_date (str): The date to check against the blocked dates for each course.

        Returns:
            str or None: The chosen course that fits the date, or None if no suitable course is found.
        """
        for course in self.courses_to_place:
            # Check if the course is not in the blocked dates dictionary or if the current date is not blocked for the course
            if course not in self.blocked_dates_dict or current_date not in self.blocked_dates_dict[course]:
                return course
        return None



    def update_blacklist(self, course:int, current_date: str, moed_b=False):
        """   
        This function update blacklist  
        """
        # Remove scheuled course from blacklist 
        crossed_courses = self.crossed_course_dict[course]
        # When there was no new crossed courses to add to blacklist
        if not crossed_courses:
            return
        # Iterate over the crossed courses
        for crossed_course in crossed_courses:
            # Check if it's not already in blacklist
            current_date = pd.to_datetime(current_date)
            # Add expiration date of 4 days
            limit_days_period = pd.date_range(start=current_date - pd.Timedelta(days=self.gap), end=current_date + pd.Timedelta(days=self.gap))
            if moed_b:
                if course in self.blocked_dates_dict:
                    del self.blocked_dates_dict[course]
                    print(f'remove {course} from blacklist')
                limit_days_before= pd.date_range(start=current_date - pd.Timedelta(days=self.gap), end=current_date + pd.Timedelta(days=self.gap))
                # limit_days_before = pd.date_range(end=current_date, periods=4)
                limit_days_period = limit_days_period.union(limit_days_before)
            if crossed_course not in self.blocked_dates_dict:
                self.blocked_dates_dict[crossed_course] = limit_days_period
            else:
                self.blocked_dates_dict[crossed_course] = self.blocked_dates_dict[crossed_course].union(limit_days_period)
        return 

    def is_moed_b_possible(self, current_date: str, course_to_schedule: int):
        current_date = pd.to_datetime(current_date)
        max_attempts = 7  # Maximum number of attempts to find an available date
        attempt = 0
        available_dates = pd.to_datetime(self.exam_schedule_table['date']).values  # Convert available dates to datetime format
        while attempt < max_attempts:
            potential_date = current_date + pd.DateOffset(days=28+ attempt)   # Calculate 4 weeks (approximately) after current_date
            if potential_date in available_dates:
                if potential_date <= pd.to_datetime(self.end_moed_bet_date):
                    # print(f"Scheduled Moed B to course {course_to_schedule} on {potential_date} == {28+ attempt}. ")
                    return potential_date
                else:
                    print(f"Problem scheduling course {course_to_schedule} on {potential_date}: Exceeds maximum date {self.end_moed_bet_date}.")
                    return False

            attempt += 1
        
        print(f"Could not find a suitable date within {max_attempts} attempts.")
        return False
    
    def check_if_date_possible(self, course:str,potential_date):
        if course not in self.blocked_dates_dict:
            return True
        if potential_date not in self.blocked_dates_dict[course]:
            return True
        return False
    
    
    
    def schedule_moed_a(self, course, current_date):
        """Schedule Moed A for the course."""
        # if course not in self.moed_a_scheduled:
        index_moed_a = self.get_index_of_date(current_date)
        self.exam_schedule_table.at[index_moed_a, 'code'].append(course)
        self.exam_schedule_table.at[index_moed_a, 'descriptions'].append(f'{course} מועד א')
        self.moed_a_scheduled.append(course)
        self.update_blacklist(course, current_date)
                     
    def get_moed_a_date(self, course:int):
        date_moed_a = self.df_first_exam[self.df_first_exam['code'].apply(lambda x: course in x)]['date'].iloc[0]
        return date_moed_a
        
        
                
    def schedule_moed_b(self, course, current_date):
        """Schedule Moed B for the course."""
        date_moed_a = self.get_moed_a_date(course)
        for index, row in self.df_second_exam.iterrows():
            date = row['date']
            if (date - date_moed_a).days >=28:
                if course not in self.blocked_dates_dict or date not in self.blocked_dates_dict[course]:
                    print(f'Moed B  is {date} course is {course}')
                    index_moed_b = self.get_index_of_date(date)
                    self.exam_schedule_table.at[index_moed_b,'code'].append(course)
                    self.exam_schedule_table.at[index_moed_b,'descriptions'].append(f'{course}  מועד ב')
                    self.update_blacklist(course, date) 
                    self.courses_to_place.remove(course)
                    self.moed_b_scheduled.append(course)
                    break     
            
            
                          
    def schedule_exams(self ,max_iterations=10,just_moed_a=False):
        """_summary_
        This function schedualing the exams based on lazy algorithm
        :param int max_iterations: _description_, defaults to 2
        
        """
        iterations = 0
        while self.courses_to_place and iterations <max_iterations:   
            print(f' itrartion :{iterations} Lenght coures : {len(self.courses_to_place)}' )
            # iterate over all possible dates
            for index ,row in self.df_first_exam.iterrows():
                if not self.courses_to_place:
                    break
                # Get the curernt date 
                current_date = row['date']
                # Get  course ,In case no course avaliable, skip to next date
                course = self.get_course(current_date)
                if not course:
                    continue
                if course not in self.moed_a_scheduled:
                    self.schedule_moed_a(course, current_date)
                if course not in self.moed_b_scheduled and not just_moed_a:
                    self.schedule_moed_b(course,current_date)
                        
            iterations +=1
                    
                            
        # print(f'Warning: Maximum iterations reached. {self.courses_to_place} not be scheduled.')
        # Add column of names of courses
        self.exam_schedule_table['name'] = self.exam_schedule_table['code'].apply(lambda x: [self.code_dict[code] for code in x])
        self.exam_schedule_table = self.exam_schedule_table[['descriptions','code','name','date']]
        
        self.validate_exam_table()


    def get_index_of_date(self,date):
        index = self.exam_schedule_table.loc[self.exam_schedule_table['date']==date].index.values
        int_index = int(index)
        return int_index
    
    def validate_exam_table(self):
        for _, row in self.exam_schedule_table.explode('code').iterrows():
            curernt_course = row['code']
            if pd.isna(curernt_course):
                continue
            current_date = row['date']
            crossed_courses = self.crossed_course_dict[curernt_course]
            date_range = pd.date_range(start=current_date - pd.Timedelta(days=self.gap), end=current_date + pd.Timedelta(days=self.gap))
            for date in date_range:
                courses_on_date = self.exam_schedule_table[self.exam_schedule_table['date'] == date]['code'].explode().tolist()
                # break
                for crossed_course in crossed_courses:
                    if crossed_course in courses_on_date:
                        raise ValueError(f'Conflict detected: Crossed course {crossed_course} on {date} conflicts with {curernt_course} on {current_date} gap: {self.gap}')
                
        print(f'gap of {self.gap} days is OK')