import pandas as pd
import data_processing as dp



class ExamScheduler:
    def __init__(self, data_from_files, start_date=None,
                 end_moed_alef_date=None,end_moed_bet_date=None,semester=2,
                 limitiaons_file=None, start_date_next_semester=None,gap=3):

        # Data from files
        self.data_from_files = data_from_files
        ## Dates ##
        self.start_date = start_date
        self.end_moed_alef_date = end_moed_alef_date 
        self.end_moed_bet_date = end_moed_bet_date 
        self.start_date_next_semester = start_date_next_semester
        
        # Determine which semester
        self.semester = semester    
        
        # External limitioans file
        self.limitiaons_file = limitiaons_file
        
        # Example  66101: [א' כלכלה ת במנעס ...]
        self.programs_per_course_dict =  dp.get_programs_per_course_dict(data_from_files)
        
        # Example א' כלכלה  :     [66101,668767]
        self.courses_per_program_dict = dp.get_courses_per_program_dict(data_from_files)
        
        # Example 66101: [66867, 66826, 66827...]
        self.crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(self.courses_per_program_dict)
        
        # Generate dynamic dict
        self.dynamic_dict = self.courses_per_program_dict.copy()
        self.sort_dynamic_dict()
        
        self.code_dict = dict(zip(data_from_files['course_code'], data_from_files['course_name']))
        self.courses_to_place = list(data_from_files['course_code'])
        
        # Gen exam tables
        self.blocked_dates_dict  = dp.get_dict_of_blocked_dates_for_course_from_limitiaons_file(self.limitiaons_file)
        
        # Get list of unavilable dates to exams based on limitioans file
        self.dates_to_exclude = dp.get_unavailable_dates_from_limit_file(self.limitiaons_file)
        
        # Create exam tale with dates 
        self.exam_schedule_table = self.create_exam_schedule_table()
        
        # list to hold all scheduled to moed alef
        self.moed_alef_scheduled = []
        # list to hold all scheduled to moed bet
        self.moed_bet_scheduled = []
        # gap between crossed courses
        self.gap = gap
         
         
    def _generate_dates_range(self):
        """
        Generate a range of dates from the start date to the end date.
        The end date is determined by the end_moed_bet_date if it exists,
        otherwise by the end_moed_alef_date.
        """
        end_date = self.end_moed_bet_date if self.end_moed_bet_date else self.end_moed_alef_date
        dates_range = pd.date_range(start=self.start_date, end=end_date)
        return dates_range
    
    def sort_courses_list_by_max_crossed_courses(self, program:list):
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
        sorted_temp_dict = dict(sorted(temp_dict.items(), key=lambda item: item[1],reverse=True))
        sorted_courses_list = list(sorted_temp_dict.keys())
        
        return sorted_courses_list
    
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
        sorted_keys = sorted(self.dynamic_dict, key=lambda k: len(self.dynamic_dict[k]),reverse=True)
        # Create a new dictionary with the programs sorted by their number of courses
        dict_sorted_keys = {k:self.dynamic_dict[k] for k in sorted_keys}
        # Update dynamic_dict to the new sorted dictionary
        self.dynamic_dict = dict_sorted_keys
        
    def sort_dynamic_dict(self):
        """
        Perform a full sort of the dynamic_dict.
        First, programs are sorted by the number of courses.
        Then, courses inside each program are sorted by the number of crossed courses.
        """
        self.sort_programs_by_num_of_courses()
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
        for program in  list(self.dynamic_dict.keys()):
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
        if self.dates_to_exclude:
            exam_schedule_table = exam_schedule_table[~exam_schedule_table['date'].isin(self.dates_to_exclude)].reset_index(drop=True)
        if self.semester == 1:
            exam_schedule_table = dp.filter_sunday_thursday(exam_schedule_table, self.start_of_next_semester_date)
        # Add column of exam with empty list  
        exam_schedule_table['code'] = [[] for _ in range(len(exam_schedule_table))]
        # Add column of Comments with empty list  
        exam_schedule_table['descriptions'] = [[] for _ in range(len(exam_schedule_table))]
        
        # dataframe for Moed A until (include) end of moed A
        self.df_first_exam = exam_schedule_table.loc[exam_schedule_table.date<= pd.to_datetime(self.end_moed_alef_date)]
        if self.end_moed_bet_date is not None:
            # dataframe for Moed B starts day after end of moed A
            self.df_second_exam =exam_schedule_table.loc[exam_schedule_table.date> pd.to_datetime(self.end_moed_alef_date)]
            
        return exam_schedule_table   
        
    # def get_course(self, current_date: str)-> str | None:
    #     """
    #     Choose a course from the list of courses to place and check if it fits well with the given date.
    #     If no course fits, return None.

    #     Args:
    #         current_date (str): The date to check against the blocked dates for each course.

    #     Returns:
    #         str or None: The chosen course that fits the date, or None if no suitable course is found.
    #     """
    #     for course in self.courses_to_place:
    #         # Check if the course is not in the blocked dates dictionary or if the current date is not blocked for the course
    #         if course not in self.blocked_dates_dict or current_date not in self.blocked_dates_dict[course]:
    #             return course
    #     return None



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

        
    
    
    def schedule_moed_a(self):
        """Schedule Moed A for the course."""
        iterations = 0
        while self.dynamic_dict and iterations < 100:
            for index, row in self.df_first_exam.iterrows():
                current_date = row['date']
                # המסלולים 
                programs = list(self.dynamic_dict.keys())
                # עבור כל מסלול במסלולים לפי הסדר
                for program in programs:
                    #  רוץ על הקורסים של המסלול (שגם הם מסודרים לפי סדר)
                    for course in self.dynamic_dict[program]:
                        # אם הקורס לא מופיע ברשימה השחורה, או מופיע אבל התאריך הנוכחי לא מפריע
                        if course not in self.blocked_dates_dict or current_date not in self.blocked_dates_dict[course]:
                            #  שבץ בטבלה של לוח המבחנים בעמודת "code" 
                            self.df_first_exam.at[index, 'code'].append(course)
                            # תוסיף הערה בטבלת לוח המבחנים תחת עמודת "descriptions"   
                            self.df_first_exam.at[index, 'descriptions'].append(f'{course} מועד א') 
                            # הוסף קורס לרשימת קורסים ששובצו           
                            self.moed_alef_scheduled.append(course)
                            # מחק קורס מהמילון הדינמי
                            self.remove_course_from_dynamic_dict(course)
                            # תמחק מסלולים ריקים (אם יש)
                            self.remove_empty_programs_from_dynamic_dict()
                            # סדר את הרשימה שוב לפי המסלול הכי ארוך ובתוך כל מסלול לפי הקורס עם הכי הרבה קורסים חופפים
                            self.sort_dynamic_dict()
                            # עדכן את הרשימה השחורה
                            self.update_blacklist(course, current_date) 
                            break
                    break
                
            iterations +=1
        if len(self.moed_alef_scheduled) < len(self.courses_to_place):
            not_scheduled_courses = set(self.courses_to_place) - set(self.moed_alef_scheduled)
            print(f'missing {len(not_scheduled_courses)} courses {list(not_scheduled_courses)}')
            
                     
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
                    self.moed_bet_scheduled.append(course)
                    break     
            
                     
    # def schedule_exams(self ,max_iterations=10,just_moed_a=False):
    #     """_summary_
    #     This function schedualing the exams based on lazy algorithm
    #     :param int max_iterations: _description_, defaults to 2
        
    #     """
    #     iterations = 0
    #     while self.courses_to_place and iterations <max_iterations:   
    #         print(f' itrartion :{iterations} Lenght coures : {len(self.courses_to_place)}' )
    #         # iterate over all possible dates
    #         for index ,row in self.df_first_exam.iterrows():
    #             if not self.courses_to_place:
    #                 break
    #             # Get the curernt date 
    #             current_date = row['date']
    #             # Get  course ,In case no course avaliable, skip to next date
    #             course = self.get_course(current_date)
    #             if not course:
    #                 continue
    #             if course not in self.moed_alef_scheduled:
    #                 self.schedule_moed_a(course, current_date)
    #             if course not in self.moed_bet_scheduled and not just_moed_a:
    #                 self.schedule_moed_b(course,current_date)
                        
    #         iterations +=1
                    
                            
        # print(f'Warning: Maximum iterations reached. {self.courses_to_place} not be scheduled.')
        # Add column of names of courses
        self.exam_schedule_table['name'] = self.exam_schedule_table['code'].apply(lambda x: [self.code_dict[code] for code in x])
        self.exam_schedule_table = self.exam_schedule_table[['descriptions','code','name','date']]
        
        self.validate_exam_table()
        self.prepare_results_to_export()

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
    
    def prepare_results_to_export(self):
        
        # Change date timestamp to string 
        self.exam_schedule_table['date'] = self.exam_schedule_table['date'].dt.strftime('%Y-%m-%d')
        
        # Dict for Hebrew column
        result_table_dict = {
        'descriptions':'הערות',
        'code': 'קוד קורס',
        'name': 'שם קורס',
        'date': 'תאריך',
                    }        

        # Rename columns to Hebrew
        self.exam_schedule_table.columns = self.exam_schedule_table.columns.map(result_table_dict)