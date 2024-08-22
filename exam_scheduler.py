import pandas as pd
import data_processing as dp
import math
from Logger import logger
import random
from datetime import timedelta

class ExamScheduler:
    def __init__(self,df_ifunim, limitations, start_date, end_date,gap,start_secondS):
        self.df_ifunim = df_ifunim
        self.limitations=limitations
        self.gap_dict=self.get_gap_dict(limitations.copy()) # Individual gap, apparently not very useful
        ## Dates ##
        self.start_date = start_date
        self.end_date = end_date
        self.gap = gap
        self.tempGap=gap # will be useful when gap is too big.
        self.courses_per_program_dict = dp.get_courses_per_program_dict(df_ifunim)
        self.dynamic_dict = self.courses_per_program_dict.copy()
        # Example 66101: [66867, 66826, 66827...]
        self.crossed_course_dict = dp.gen_crossed_courses_dict_from_prog_dict(self.courses_per_program_dict)
        # Generate dynamic dict
        self.longest_program=dp.longest_program(self.courses_per_program_dict)
        self.sort_dynamic_dict()
        # when building the schedle we use courses_per_program_dict for deriving courses.
        # therefore we derive here the set of all courses from the same source
        all_courses_list = self.courses_per_program_dict.values()
        combined_list = [item for sublist in all_courses_list for item in sublist]
        self.allCourses= set(combined_list)
        # restrictions (replacing the blackList)
        self.restrictions=self.initialRestrictions(self.allCourses)
        
        
        self.code_dict = dict(zip(df_ifunim['course_code'], df_ifunim['course_name']))
        self.courses_to_place = list(df_ifunim['course_code'])
        # Get list of unavilable dates to exams based on limitioans file
        #self.dates_to_exclude = dp.get_unavailable_dates_from_limit_file(self.limitiaons_file)
        
        # Create exam table with dates 
        self.exam_schedule_table = self.create_exam_schedule_table()
        if start_secondS is not None:
            self.exam_schedule_table=dp.filter_sunday_thursday(self.exam_schedule_table, start_secondS)
        self.Ndates=len(self.exam_schedule_table)
        self.pairs_gap=self.get_pairs_gap()
        self.scheduled_courses = []
        self.maxAday=1 #  helps to spread the courses over the period

    def get_pairs_gap(self):
        pairs_gap={}
        for pair, value in self.longest_program.items():
            # Set the value to 3 if it is smaller than the original value
            tempGap=math.floor(self.Ndates/self.longest_program[pair])
            updated_value = self.gap if tempGap > self.gap else tempGap
            # Update the new dictionary with the pair and updated value
            pairs_gap[pair] = updated_value
        return pairs_gap

    def schedule(self):
        Ndates=len(self.exam_schedule_table)
        # Ncoursess = len(self.allCourses)
        # testPerDate=math.ceil(Ncoursess/Ndates)
        # #testPerDate is the average number per day rounded up
        """Schedule Moed A for the course."""
        programs = list(self.dynamic_dict.keys())
        proN=0  # counting the programs
        # עבור כל מסלול במסלולים לפי הסדר
        for program in programs:
            proN+=1
            print("Program" +str(proN)+" : "+program)
            # Lprogram=len(program)
            # Agap=math.floor(Ndates/Lprogram)
            # if Agap<self.gap:
            #     self.tempGap=Agap
            # else:
            #     self.tempGap=self.gap

            if program in self.dynamic_dict and self.dynamic_dict[program] is not None:
                for course in self.dynamic_dict[program]:
                    # print("looking for schedule: "+str(course))
                    found=False
                    for index, row in self.exam_schedule_table.iterrows():
                        current_date = row['date']
                        c0=self.limits_from_file(current_date,course)
                        ### Conditions for schedule that can be violated
                        c1=current_date not in self.restrictions[course] # dynamic restrictions
                        c2=len(self.exam_schedule_table.at[index, 'code'])<self.maxAday # Not too many at the same date
                        ################################################                     
                        if c0 and c1 and c2:
                            self.put_exam_date(index,course,current_date)                            
                            found=True
                            break
                    ### Brutal schedule: doesn't find a date for course
                    if not found:
                        # print("#### Brutal Schedule ####"+str(course)+" of program "+program)
                        for index, row in self.exam_schedule_table.iterrows():
                            current_date = row['date']
                            c0=self.limits_from_file(current_date,course)
                            c2=len(self.exam_schedule_table.at[index, 'code'])<self.maxAday # Not too many at the same date
                            # x is the number of courses k days before and after the test of the same program.
                            x=self.count_courses_in_period(current_date, program, 1)
                            crowded=x>=2
                            exams=row['code']
                            if c0 and c2 and not exams and not crowded:
                                self.put_exam_date(index,course,current_date)
                                found=True
                                break
                    if not found: # more brutal
                        for index, row in self.exam_schedule_table.iterrows():
                            current_date = row['date']
                            c0=self.limits_from_file(current_date,course)
                            c2=len(self.exam_schedule_table.at[index, 'code'])<self.maxAday # Not too many at the same date
                            # checks whether there is a same progaram course at the day
                            x=self.count_courses_in_period(current_date, program, 0)
                            sameDay=x>0
                            y=self.count_courses_in_period(current_date, program, 1)
                            crowded=y>=2
                            if c0 and c2 and not sameDay and not crowded:
                                self.put_exam_date(index,course,current_date)
                                found=True
                                break
                                
                    if not found:
                        print("Even brutality doesnt help for course "+str(course))               

                        
                                

            if program in self.dynamic_dict and len(self.dynamic_dict[program])>0:
                str0="Scheduling " + program + " is impossible.\n"
                str1="It contains "+str(len(self.courses_per_program_dict[program])) + " courses,"
                str2=" available dates:"+str(len(self.exam_schedule_table))
                logger.add_remark(str0 + str1 + str2)
                print(str0 + str1 + str2)
        if len(self.scheduled_courses) < len(self.courses_to_place):
            not_scheduled_courses = set(self.courses_to_place) - set(self.scheduled_courses)
            print(f'missing {len(not_scheduled_courses)} courses {list(not_scheduled_courses)}')
        #self.validate_exam_table(self.df_first_exam)
        self.prepare_results_to_export(self.exam_schedule_table)          
        # self.df_first_exam   
        self.arrangePrograms()
        return self.exam_schedule_table
    def put_exam_date(self,index,course,current_date):
        # print("List of "+str(current_date)+": "+str(row['code']))
        # print("Scheduling "+str(course)+" at "+str(current_date)+".")
        #  שבץ בטבלה של לוח המבחנים בעמודת "code" 
        self.exam_schedule_table.at[index, 'code'].append(course)
        # תוסיף הערה בטבלת לוח המבחנים תחת עמודת "descriptions"   
        #self.exam_schedule_table.at[index, 'descriptions'].append(f'{course} מועד א') 
        # הוסף קורס לרשימת קורסים ששובצו           
        self.scheduled_courses.append(course)
        # מחק קורס מהמילון הדינמי
        self.remove_course_from_dynamic_dict(course)
        # תמחק מסלולים ריקים (אם יש)
        self.remove_empty_programs_from_dynamic_dict()
        # סדר את הרשימה שוב לפי המסלול הכי ארוך ובתוך כל מסלול לפי הקורס עם הכי הרבה קורסים חופפים
        ### I dont think it is needed to resort every time.
        # self.sort_dynamic_dict()
        # עדכן את הרשימה השחורה
        self.update_restrictions(course, current_date)
        self.maxAday=math.floor(len(self.scheduled_courses)/self.Ndates)+2
    def limits_from_file(self,current_date,course):
        c0=True # Predetermined restrictions from file
        for index2, row2 in self.limitations.iterrows():
            cn=row2['course']
            c01=(cn==course or cn=='*') and row2['start']>current_date
            c02=(cn==course or cn=='*') and row2['end']<current_date
            c03=(cn==course or cn=='*') and row2['blocked']==current_date
            if  c01 or  c02 or c03:
                c0=False
        return c0

    def _generate_dates_range(self):
        """
        Generate a range of dates from the start date to the end date.
        The end date is determined by the end_date if it exists,
        otherwise by the end_date.
        """
        end_date = self.end_date if self.end_date else self.end_date
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
        ### I am not sure the second sorting is helpful
        # self.sort_courses_inside_program()
        
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
        # if self.dates_to_exclude:
        #     exam_schedule_table = exam_schedule_table[~exam_schedule_table['date'].isin(self.dates_to_exclude)].reset_index(drop=True)
        # if self.semester == 1:
        #     exam_schedule_table = dp.filter_sunday_thursday(exam_schedule_table, self.start_of_next_semester_date)
        # Add column of exam with empty list  
        exam_schedule_table['code'] = [[] for _ in range(len(exam_schedule_table))]
        # Add column of Comments with empty list  
        exam_schedule_table['descriptions'] = [[] for _ in range(len(exam_schedule_table))]
        
        # dataframe for Moed A until (include) end of moed A
        # self.df_first_exam = exam_schedule_table.loc[exam_schedule_table.date<= pd.to_datetime(self.end_date)]
        if self.end_date is not None:
            # dataframe for Moed B starts day after end of moed A
            self.df_second_exam =exam_schedule_table.loc[exam_schedule_table.date> pd.to_datetime(self.end_date)]
            
        return exam_schedule_table   
        
    def update_restrictions(self,course:int, current_date: str):
        g=self.gap
        gCourse=g
        if course in self.gap_dict:
            gCourse=self.gap_dict[course]
        # Remove scheuled course from blacklist 
        crossed_courses = self.crossed_course_dict[course]
        # When there was no new crossed courses to add to blacklist
        if not crossed_courses:
            return
        # Iterate over the crossed courses
        for crossed_course in crossed_courses:
            pair = (course, crossed_course) if course < crossed_course else (crossed_course, course)
            g=gCourse
            # Check if it's not already in blacklist
            current_date_pd = pd.to_datetime(current_date)
            # Add expiration date of 4 days           
            if crossed_course in self.gap_dict:
                g=min(g,self.gap_dict[crossed_course])
                # print("course:"+str(course)+", second course:"+str(crossed_course))
                # print("gCourse:"+str(gCourse)+", gCrossed course:"+str(self.gap_dict[crossed_course]))
            if pair in self.pairs_gap:
                g=min(g,self.pairs_gap[pair])
                #print("Longest same program limitation gap:"+str(self.pairs_gap[pair]))
                #print("Eventually Gap:"+str(g))
                
            limit_days_period = pd.date_range(start=current_date_pd-pd.Timedelta(days=g), end=current_date + pd.Timedelta(days=g))
            # print("The gap is: "+str(g))
            self.restrictions[crossed_course].update(limit_days_period)
            # if moed_b:
            #     if course in self.blocked_dates_dict:
            #         del self.blocked_dates_dict[course]
            #         print(f'remove {course} from blacklist')
            #     limit_days_before= pd.date_range(start=current_date_pd - pd.Timedelta(days=self.gap), end=current_date + pd.Timedelta(days=self.gap))
            #     # limit_days_before = pd.date_range(end=current_date, periods=4)
            #     limit_days_period = limit_days_period.union(limit_days_before)
            # if crossed_course not in self.blocked_dates_dict:
            #     self.blocked_dates_dict[crossed_course] = limit_days_period
            # else:
            #     self.blocked_dates_dict[crossed_course] = self.blocked_dates_dict[crossed_course].union(limit_days_period)
        return
    
    def validate_exam_table(self, df):
        for _, row in df.explode('code').iterrows():
            curernt_course = row['code']
            if pd.isna(curernt_course):
                continue
            current_date = row['date']
            crossed_courses = self.crossed_course_dict[curernt_course]
            date_range = pd.date_range(start=current_date - pd.Timedelta(days=self.gap), end=current_date + pd.Timedelta(days=self.gap))
            for date in date_range:
                courses_on_date = df[df['date'] == date]['code'].explode().tolist()
                # break
                for crossed_course in crossed_courses:
                    if crossed_course in courses_on_date:
                        raise ValueError(f'Conflict detected: Crossed course {crossed_course} on {date} conflicts with {curernt_course} on {current_date} gap: {self.gap}')
                
        print(f'gap of {self.gap} days is OK')
    
    def prepare_results_to_export(self, df):
        df = df.copy()
        df.loc[:,'name'] = df['code'].apply(lambda x: [self.code_dict[code] for code in x])
        df = df[['descriptions','code','name','date']]
        # Change date timestamp to string 
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        # Dict for Hebrew column
        result_table_dict = {
        'descriptions':'הערות',
        'code': 'קוד קורס',
        'name': 'שם קורס',
        'date': 'תאריך',
                    }        

        # Rename columns to Hebrew
        df.columns = df.columns.map(result_table_dict)
        
        return df

    def initialRestrictions(self,allCourses):
        # Initializing the restircitons of all courses. Each course appears anyway.
        restrict={}
        for course in allCourses:
            restrict[course]=set()                         
        return restrict 
    def get_gap_dict(self,limitations):
        df = limitations.sort_values(by='course')
        # Drop duplicates while keeping the first occurrence and ignoring NaNs in 'blocked'
        df_filtered = df.dropna(subset=['gap']).drop_duplicates(subset=['course'], keep='first')
        course_gap_dict = df_filtered.set_index('course')['gap'].to_dict()
        return course_gap_dict
    def arrangePrograms(self):
        # Get the list of programs
        programs = list(self.courses_per_program_dict.keys())
        # Initialize the new DataFrame with 'date' and program columns
        columns = ['date'] + programs
        new_df = pd.DataFrame(columns=columns)
        # Iterate through each row in exam_schedule_table
        for _, row in self.exam_schedule_table.iterrows():
            date = row['date']
            courses = row['code']            
            # Create a dictionary to store courses for each program for the current date
            row_data = {'date': date}
            # for program in programs:
            #     row_data[program] = []
            # For each course, check which programs it belongs to and add it to the corresponding program column
            for course in courses:
                for program, program_courses in self.courses_per_program_dict.items():
                    if course in program_courses:
                        row_data[program]=course            
            # # Convert lists to strings to avoid having lists in the DataFrame cells
            # for program in programs:
            #     row_data[program] = ', '.join(map(str, row_data[program]))
            new_df = pd.concat([new_df, pd.DataFrame([row_data])], ignore_index=True)
            # # Append the row data to the new DataFrame
            # new_df = new_df.append(row_data, ignore_index=True)
        return new_df
        # new_df.to_excel('TablePerPrograms.xlsx', index=False)


    def count_courses_in_period(self, D, P, k):
        # Convert D to a datetime object if it's not already
        if isinstance(D, str):
            D = pd.to_datetime(D)

        # Get the list of courses for the given program P
        program_courses = self.courses_per_program_dict.get(P, [])

        # Calculate the start date of the period (k days before D)
        start_date = D - timedelta(days=k)
        end_date = D + timedelta(days=k)
        # Filter the schedule table to include only the dates in the specified period
        mask = (self.exam_schedule_table['date'] >= start_date) & (self.exam_schedule_table['date'] <= end_date)
        filtered_schedule = self.exam_schedule_table[mask]

        # Initialize a counter for the courses
        count = 0

        # Iterate through the filtered schedule and count the courses that fit the program
        for _, row in filtered_schedule.iterrows():
            courses_on_date = row['code']
            count += len(set(courses_on_date) & set(program_courses))

        return count

    
        


  
