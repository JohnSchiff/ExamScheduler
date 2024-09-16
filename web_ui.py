import streamlit as st
from datetime import date
import pandas as pd
from exam_scheduler import ExamScheduler
import data_processing as dp
import hashlib


#TODO Check smeester a courses 
class ExamSchedulerApp:
    def __init__(self):
        self.uploaded_courses_file = None
        self.uploaded_ifunim_file = None
        self.uploaded_limits_file = None

        # Initialize session state for authentication
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False
        
        if not st.session_state.logged_in:
            self.show_login()
        else:
            st.set_page_config(page_title="שיבוץ בחינות", page_icon=":calendar:")
            self.setup_ui()
    def show_login(self):
        st.title("Login Page")

        # Load secrets
        user_data = st.secrets["users"]

        # User input fields
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        # Login button
        if st.button("Login"):
            if self.check_credentials(username, password, user_data):
                st.session_state.logged_in = True
                st.rerun()  # Reload the app to show the main content
            else:
                st.error("Invalid username or password")

    def check_credentials(self, username, password, user_data):
        # Hash the password for comparison
        def hash_password(password):
            return hashlib.sha256(password.encode()).hexdigest()

        hashed_password = hash_password(password)
        for user in user_data:
            if user["username"] == username and hash_password(user["password"]) == hashed_password:
                return True
        return False
    
    def setup_ui(self):
        
        st.image('BIU_LOGO.png')
        # Custom CSS for the file uploader labels
        st.markdown(
            """
            <style>
            .file-upload-label {
                font-size: 24px;
                text-align: center;
                direction: rtl;
                display: block;
                align-items: center;
                margin-bottom: 10px;
            }
            .required {
                color: red;
            }
            .custom-dataframe {
                font-size: 20px;  /* Adjust font size */
                text-align: center;
                direction: rtl;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown('<label class="file-upload-label">קובץ קורסים של המחלקה<span class="required">*</span></label>', unsafe_allow_html=True)
        # Layout with file uploaders
        self.uploaded_courses_file = st.file_uploader("קורסים", type=["csv", "xlsx"], key="uploader1", label_visibility='hidden')
        st.markdown('<label class="file-upload-label">קובץ אפיונים<span class="required">*</span></label>', unsafe_allow_html=True)
        self.uploaded_ifunim_file = st.file_uploader("אפיונים", type=["csv", "xlsx"], key="uploader2", label_visibility='hidden')
        st.markdown('<label class="file-upload-label">קובץ אילוצים</label>', unsafe_allow_html=True)
        self.uploaded_limits_file = st.file_uploader("(אופציונלי)", type=["csv", "xlsx"], key="uploader3", )

        # Layout with number input for days gap between exams
        col1, col2,col3, col4= st.columns([0.1] * 4)  # size of columns
        # self.days_gap_between_exams = col3.number_input(
        #     "פער בין מבחנים (ימים)", min_value=1, max_value=5, value=4, step=1, key="dte_min_input")

        self.moed = col2.radio('מועד',['א','ב'])
        self.semester = col3.radio('סמסטר',[1,2])
        # Button to generate exam schedule
        col1, col2, col3 = st.columns([0.2] * 3)  # size of columns
        self.gen_exams_button = col2.button(label='צור לוח מבחנים', disabled=False, on_click=self.create_exam_schedule)


        self.df_place = st.columns([1])[0]

    def should_disable_button(self):
        # Check if any of the required files are not uploaded
        return not self.uploaded_courses_file or not self.uploaded_ifunim_file

    def create_exam_schedule(self):
        print(f'self.moed : {self.moed} self.semester : {self.semester} ')
        if not self.uploaded_courses_file or not self.uploaded_ifunim_file:
            st.error('This is a not working ')
            return
        df_ifunim = dp.get_ifunim_dataframe_from_file(self.uploaded_ifunim_file, semester=2)
        df_courses = dp.get_courses_dataframe_from_file(self.uploaded_courses_file)
        limitations_file = self.uploaded_limits_file
        df = dp.merge_ifunim_and_coursim(df_ifunim, df_courses)
        exam_scheduler = ExamScheduler(df, external_file=limitations_file, gap=self.days_gap_between_exams)
        exam_scheduler.schedule_exams()

        # Display DataFrame 
        self.df_place.dataframe(exam_scheduler.exam_schedule, height=1500, width=2000)
# Run the app
if __name__ == "__main__":
    app = ExamSchedulerApp()


