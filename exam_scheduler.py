import pandas as pd
from datetime import timedelta
import data_processing as dp

start_date = '2024-06-30'
end_date = '2024-09-12'

# List of dates to exclude based on word file (holidays, fast ...etc)
dates_to_exclude = ['2024-07-04','2024-07-05','2024-07-23',
                    '2024-07-24','2024-08-06','2024-08-06',
                    '2024-08-07','2024-08-08','2024-08-09',
                    '2024-08-13','2024-08-14','2024-08-25',
                    '2024-08-26','2024-08-27','2024-08-28',
                    '2024-08-29','2024-08-30','2024-09-02',
                    '2024-09-03','2024-09-10','2024-09-11',
                    '2024-09-12']
class ExamScheduler:
    def __init__(self, df, start_date=start_date, end_date=end_date, dates_to_exclude=dates_to_exclude,external_file=None):
        self.start_date = start_date
        self.end_date = end_date
        self.dates_to_exclude = dates_to_exclude
        self.df = df
        self.external_file = external_file
        self.courses_dict =  dp.get_courses_dict(df)
        self.programs_dict = dp.get_programs_dict(df)
        self.code_dict = dict(zip(df['קוד'], df['שם']))
        self.courses_list = list(self.courses_dict.keys())
        self.exam_schedule = self.create_exam_schedule()
        self.blocked_dates  = self.create_blocked_dates()
        
    def create_exam_schedule(self):
        """  
        Generate dataframe of possible dates for exams.
        """
        # Convert the date range to a list
        dates_range = pd.date_range(start=self.start_date, end=self.end_date)
        # Show it as a DataFrame with column 'date'    
        exam_schedule = pd.DataFrame(data=dates_range, columns=['date'])
        # Filter out Shabbat days
        exam_schedule = exam_schedule[exam_schedule['date'].dt.day_name() != 'Saturday']
        # Filter out excluded dates
        exam_schedule = exam_schedule[~exam_schedule.date.isin(self.dates_to_exclude)].reset_index(drop=True)
        # Add column of exam with empty list  
        exam_schedule['exam'] = [[] for _ in range(len(exam_schedule))]
        return exam_schedule   
        
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
    
    def get_course(self):
        """  
        This function choose course  from a list and check if it fits well.
        if not  - it keeps trying until it goes all over the list 
        """
        for course in self.courses_list:
            # In case the chosen course is not in black list
            if course not in self.blocked_dates:
                return course
        # When there was no luck after max_attempts attempts return False
        return False


    def handle_blacklist(self, course:int, current_date: pd.Timestamp, gap:int):
        """   
        This function update blocked date s  
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
        limit_dicts = self.get_limit_dict_from_external_file(self.external_file)
        return limit_dicts
    
    def schedule_exams(self ,max_iterations=2):
        iteration_count = 0
        while self.courses_list and iteration_count < max_iterations:
            print(f'iteration_count is {iteration_count}')
            iteration_count +=1
            # iterate over all possible dates
            for index ,row in self.exam_schedule.iterrows():
                # Get the date 
                current_date = row['date'].date()
                # Check blacklist 
                self.check_blacklist_dayly(current_date)
                # Get random course 
                course = self.get_course()
                # In case no course avaliable, skip to next date
                if not course:
                    continue
                # When course was found - remove it from coureses list
                self.courses_list.remove(course)
                # Schedule the course in the date 
                self.exam_schedule.at[index,'exam'].append(course)
                # Update blacklist accroding to new course
                self.handle_blacklist(course, current_date, gap=4)
            if iteration_count >= max_iterations:
                print(f'Warning: Maximum iterations reached. {self.courses_list} not be scheduled.')
     
        self.exam_schedule['exam_name'] = self.exam_schedule['exam'].apply(lambda x: [self.code_dict[code] for code in x])

    @staticmethod   
    def get_limit_dict_from_external_file(file=None) -> dict:
        if file is None:
            return {}
        df = pd.read_excel(file)
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