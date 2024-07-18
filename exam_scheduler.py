import pandas as pd
from datetime import timedelta
import data_processing as dp



class ExamScheduler:
    def __init__(self, data_from_files, start_date, end_moed_alef_date,end_moed_bet_date,semester=2, limitiaons_file=None, start_of_semester2_date=None):

        ## Dates ##
        self.start_date = start_date
        self.end_moed_alef_date = end_moed_alef_date 
        self.end_moed_bet_date = end_moed_bet_date 
        self.start_of_semester2_date = start_of_semester2_date
        self.days_gap_between_moed_b = 28
        self.semester = semester
        # Data files
        self.data_from_files = data_from_files
        self.limitiaons_file = limitiaons_file
        
        self.courses_dict =  dp.get_courses_dict(data_from_files)
        self.programs_dict = dp.get_programs_dict(data_from_files)
        self.crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(self.programs_dict)
        self.code_dict = dict(zip(data_from_files['קוד'], data_from_files['שם']))
        self.courses_to_place = list(data_from_files['קוד'])
        self.scheduled_courses = []
        # Gen exam tables
        self.blocked_dates_dict  = dp.get_dict_of_blocked_dates_for_course_from_limitiaons_file(self.limitiaons_file)
        
        self.dates_to_exclude = dp.get_unavailable_dates_from_limit_file(self.limitiaons_file)
        self.exam_schedule_table = self.create_exam_schedule_table()
        
    def create_exam_schedule_table(self):
        """  
        Generate dataframe of possible dates for exams.
        """
        # Convert the date range to a list
        dates_range = pd.date_range(start=self.start_date, end=self.end_moed_bet_date)
        # Show it as a DataFrame with column 'date'    
        exam_schedule_table = pd.DataFrame(data=dates_range, columns=['תאריך'])
        # Filter out Shabbat days
        exam_schedule_table = exam_schedule_table[exam_schedule_table['תאריך'].dt.day_name() != 'Saturday']
        # Filter out excluded dates
        if self.dates_to_exclude:
            exam_schedule_table = exam_schedule_table[~exam_schedule_table['תאריך'].isin(self.dates_to_exclude)].reset_index(drop=True)
        if self.semester == 1:
            exam_schedule_table = dp.filter_sunday_thursday(exam_schedule_table, self.start_of_semester2_date)
        # Add column of exam with empty list  
        exam_schedule_table['קוד קורס'] = [[] for _ in range(len(exam_schedule_table))]
        # Add column of Comments with empty list  
        exam_schedule_table['הערות'] = [[] for _ in range(len(exam_schedule_table))]
        # Fix format
        exam_schedule_table['תאריך'] = exam_schedule_table['תאריך'].dt.strftime('%Y-%m-%d')
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



    def handle_blacklist(self, course:int, current_date: str, gap:int):
        """   
        This function update blacklist  
        """
        # Remove scheuled course from blacklist 
        crossed_courses = self.crossed_course_dict[course]
        # When there was no new crossed courses to add to blacklist
        if not crossed_courses:
            return
        if course in self.blocked_dates_dict:
            del self.blocked_dates_dict[course]
        # Iterate over the crossed courses
        for crossed_course in crossed_courses:
            # Check if it's not already in blacklist
            current_date = pd.to_datetime(current_date)
            # Add expiration date of 4 days
            limit_days_period = pd.date_range(start=current_date,end=current_date+timedelta(days=gap))
            if crossed_course not in self.blocked_dates_dict:
                self.blocked_dates_dict[crossed_course] = limit_days_period
            else:
                self.blocked_dates_dict[crossed_course] = self.blocked_dates_dict[crossed_course].union(limit_days_period)
        return

    def is_moed_b_possible(self, current_date: str, course_to_schedule: int):
        current_date = pd.to_datetime(current_date)
        max_attempts = 7  # Maximum number of attempts to find an available date
        attempt = 0
        available_dates = pd.to_datetime(self.exam_schedule_table['תאריך']).values  # Convert available dates to datetime format
        while attempt < max_attempts:
            potential_date = current_date + pd.DateOffset(days=28+ attempt)   # Calculate 4 weeks (approximately) after current_date
            if potential_date in available_dates:
                if potential_date <= pd.to_datetime(self.end_moed_bet_date):
                    print(f"Scheduled Moed B to course {course_to_schedule} on {potential_date} == {28+ attempt}. ")
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
            
            
    def schedule_exams(self ,max_iterations=2):
        """_summary_
        This function schedualing the exams based on lazy algorithm
        :param int max_iterations: _description_, defaults to 2
        
        """
        iteration_count = 0
        while self.courses_to_place and iteration_count < max_iterations:                
            print(f'iteration_count is {iteration_count}')
            iteration_count +=1
            # iterate over all possible dates
            for index ,row in self.exam_schedule_table.iterrows():
                exams_scheduled = 0
                if not self.courses_to_place:
                    break
                # Get the date 
                current_date = row['תאריך']
                # Get random course 
                # In case no course avaliable, skip to next date
                while exams_scheduled <4 :
                    course = self.get_course(current_date)
                    if not course:
                        break
                    # When course was found - remove it from courses list
                    # Schedule the course in the date moed A
                    # course_name = self.code_dict[course]
                    self.exam_schedule_table.at[index,'קוד קורס'].append(course)
                    self.exam_schedule_table.at[index,'הערות'].append(f'{course} מועד א')
                    self.scheduled_courses.append(course)
                    moed_b_date = self.is_moed_b_possible(current_date, course)
                    if moed_b_date:
                        index_moed_b =  int(self.exam_schedule_table[pd.to_datetime(self.exam_schedule_table['תאריך']).values==moed_b_date].index.values)
                        self.exam_schedule_table.at[index_moed_b,'קוד קורס'].append(course)
                        self.exam_schedule_table.at[index_moed_b,'הערות'].append(f'{course} מועד ב')
                    else:
                        print(f'Problem to schedle moed b to {course}')
                
                    self.courses_to_place.remove(course)
                # Update blacklist accroding to new course
                    self.handle_blacklist(course, current_date, gap=4)
                    exams_scheduled +=1
                    
            if iteration_count >= max_iterations:
                print(f'Warning: Maximum iterations reached. {self.courses_to_place} not be scheduled.')
        # Add column of names of courses
        self.exam_schedule_table['שם קורס'] = self.exam_schedule_table['קוד קורס'].apply(lambda x: [self.code_dict[code] for code in x])
        self.exam_schedule_table = self.exam_schedule_table[['הערות','קוד קורס','שם קורס','תאריך']]
        


    def get_index_of_date(self,date):
        index = self.exam_schedule_table.loc[self.exam_schedule_table['תאריך']==date].index.values
        int_index = int(index)
        return int_index