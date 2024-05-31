import pandas as pd
import random
from datetime import timedelta

class ExamScheduler:
    def __init__(self,start_date, end_date, dates_to_exclude, courses_dict,programs_dict, code_dict, external_file=None) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.dates_to_exclude = dates_to_exclude
        self.courses_dict = courses_dict
        self.programs_dict = programs_dict
        self.code_dict = code_dict
        self.courses_list = list(courses_dict.keys())
        self.df_dates = self.create_df_dates()
        self.external_file = external_file
        self.blocked_dates  = self.create_blocked_dates()
        
        if self.external_file:
            self.blocked_dates = self.get_limit_dict_from_external_file()
        
    def create_df_dates(self):
        """  
        Generate dataframe of possible dates for exams.
        """
        # Convert the date range to a list
        dates_range = pd.date_range(start=self.start_date, end=self.end_date)
        # Show it as a DataFrame with column 'date'    
        df_dates = pd.DataFrame(data=dates_range, columns=['date'])
        # Filter out Shabbat days
        df_dates = df_dates[df_dates['date'].dt.day_name() != 'Saturday']
        # Filter out excluded dates
        df_dates = df_dates[~df_dates.date.isin(self.dates_to_exclude)].reset_index(drop=True)
        # Add column of exam with empty list  
        df_dates['exam'] = [[] for _ in range(len(df_dates))]
        return df_dates   
        
    def get_crossed_courses(self, course:int) -> set:
        """
        By given course, get "black list" of courses which are not allowed with it
        i.e crossed courses from programs dictioonary
        """
        crossed_courses = set() # Create an empty set to store "black list"
        # iterate over program dictionary
        for program, courses in self.programs_dict.items():
            if course in courses:
                # Add to courses to the "black list"
                crossed_courses.update(courses)
        # remove from black list the course itself
        crossed_courses.discard(course)
        
        return crossed_courses
    
    def get_random_course(self)-> str|None:
        """  
        This function choose course  from a list and check if it fits well.
        if not  - it keeps trying until it goes all over the list 
        """
        for course in self.courses_list:
            # Randomly choose course from list
            random_course = random.choice(self.courses_list)
            # In case the chosen course is not in black list
            if random_course not in self.blocked_dates:
                return random_course
            # If the course in black list
            attempts +=1
        # When there was no luck after max_attempts attempts return False
        return False


    def handle_blacklist(self, course:int, current_date: pd.Timestamp, gap:int):
        """   
        This function create blacklist initialy or update it 
        """
        crossed_courses = self.get_crossed_courses(course)
        # When there was no new crossed courses to add to blacklist
        if not crossed_courses:
            return
        # Iterate over the crossed courses
        for course in crossed_courses:
            # Check if it's not already in blacklist
            if course not in self.blocked_dates:
                # Add expiration date of 4 days
                self.blocked_dates[course] = pd.date_range(start=current_date,end=current_date+timedelta(days=gap))
        return

    def check_blacklist_dayly(self, current_date: pd.Timestamp):  
        """
        This function updates the expiration date of courses in blacklist
        if expired date - it will remove this course from the list 
        """ 
        # Where blacklist is empty
        if not self.blocked_dates:
            return 
        # Empty list to store expired date courses to remove
        course_to_remove_from_blacklist = []
        for course, blocked_dates_range in self.blocked_dates.items():
            if str(current_date) not in blocked_dates_range:
                course_to_remove_from_blacklist.append(course)         
        for course in course_to_remove_from_blacklist:
            # Remove course from blacklist dict
            del self.blocked_dates[course]

    def create_blocked_dates(self):
        if not self.external_file:
            return {}
        return self.get_limit_dict_from_external_file(self.external_file)
        
    def get_limit_dict_from_external_file(self, file:str) -> dict:
        df = pd.read_excel(self.external_file)
        new_cols = {col: col.strip() for col in df.columns}
        df.rename(columns=new_cols, inplace=True)
        df.rename(columns={'קוד קורס':'קוד'},inplace=True)
        limit_dict = {}
        for i, row in df.iterrows():
            course = row['קוד']
            start = row['התחלה']
            end = row['סוף']
            limit_dict[course] = pd.date_range(start=start, end=end)
        return limit_dict 
    
    def schedule_exams(self ,max_iterations=2):
        df_dates = self.create_df_dates()
        iteration_count = 0
        while self.courses_list and iteration_count < max_iterations:
            iteration_count +=1
            # iterate over all possible dates
            for index ,row in df_dates.iterrows():
                self.create_blocked_dates()
                # In case there are no more courses to schedule exit the loop
                if not self.courses_list:
                    break
                # Get the date 
                current_date = row['date'].date()
                # Check blacklist 
                self.check_blacklist_dayly(current_date)
                # Get random course 
                course = self.get_random_course()
                # In case no course avaliable, skip to next date
                if not course:
                    continue
                # When course was found - remove it from coureses list
                self.courses_list.remove(course)
                # Schedule the course in the date 
                df_dates.at[index,'exam'].append(course)
                # Update blacklist accroding to new course
                self.handle_blacklist(course, current_date, gap=4)
            if iteration_count >= max_iterations:
                print(f'Warning: Maximum iterations reached. {self.courses_list} not be scheduled.')
     
        df_dates['exam_name'] = df_dates['exam'].apply(lambda x: [self.code_dict[code] for code in x])
        return df_dates