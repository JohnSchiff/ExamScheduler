import streamlit as st
import streamlit_authenticator as stauth
from datetime import date
import pandas as pd
from exam_scheduler import ExamScheduler
import data_processing as dp
import yaml
from yaml.loader import SafeLoader


class ExamSchedulerApp:
    def __init__(self):
        self.uploaded_courses_file = None
        self.uploaded_ifunim_file = None
        self.uploaded_limits_file = None
        st.set_page_config(page_title="שיבוץ בחינות", page_icon=":calendar:")
        self.show_login()

    def show_login(self):
        with open('config.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)

        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days'],
        )

        authenticator.login()
        if st.session_state['authentication_status']:
            authenticator.logout("Logout", "sidebar")
            st.sidebar.write(f'Welcome *{st.session_state["name"]}*')
            self.setup_ui()
        elif st.session_state['authentication_status'] is False:
            st.error('Username/password is incorrect')
        elif st.session_state['authentication_status'] is None:
            st.warning('Please enter your username and password')

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

        col1, col2 = st.columns([4, 2])
        self.uploaded_courses_file = col1.file_uploader(
            "קורסים", type=["csv", "xlsx"], key="uploader1", label_visibility='hidden')
        col2.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)  # Adjust height as needed

        col2.markdown(
            '<label class="file-upload-label">קובץ קורסים<span class="required">*</span></label>', unsafe_allow_html=True)
        col1, col2 = st.columns([4, 2])
        self.uploaded_ifunim_file = col1.file_uploader(
            "אפיונים", type=["csv", "xlsx"], key="uploader2", label_visibility='hidden')
        # Layout with file uploaders
        col2.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)  # Adjust height as needed
        col2.markdown('<label class="file-upload-label">קובץ אפיונים<span class="required">*</span></label>',
                      unsafe_allow_html=True)

        col1, col2 = st.columns([4, 2])
        self.uploaded_limits_file = col1.file_uploader(
            "אילוצים", type=["csv", "xlsx"], key="uploader3", label_visibility='hidden')
        col2.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)  # Adjust height as needed
        col2.markdown('<label class="file-upload-label">קובץ אילוצים  </label>', unsafe_allow_html=True)

        st.divider()
        # Layout with number input for days gap between exams
        col1, col2, col3, col4 = st.columns([0.1]*4)  # size of columns
        # self.days_gap_between_exams = col3.number_input(
        #     "פער בין מבחנים (ימים)", min_value=1, max_value=5, value=4, step=1, key="dte_min_input")

        self.start_date = col2.date_input(label='תאריך התחלה')
        self.end_date = col1.date_input(label='תאריך סוף')
        # Checking if the end date is before the start date
        if self.end_date < self.start_date:
            st.error("!תאריך הסוף לא יכול להיות מוקדם מתאריך ההתחלה")

        self.moed_radio_button = col3.radio('מועד', ['א', 'ב'], key='moed')
        self.semester = col4.radio('סמסטר', [1, 2], key='semester')

        if st.session_state.moed == 'ב':
            st.markdown('<label class="file-upload-label">מועד א\'</label>', unsafe_allow_html=True)
            self.uploaded_additional_file = st.file_uploader(
                "Additional File for Semester B", type=["csv", "xlsx"], key="uploader_additional")
        # Button to generate exam schedule
        st.divider()
        col1, col2, col3 = st.columns([0.2] * 3)  # size of columns
        self.gen_exams_button = col2.button(label='צור לוח מבחנים', disabled=False, on_click=self.create_exam_schedule)

        self.df_place = st.columns([1])[0]

    def on_option_change(self, key):
        print(f"Selected option: {st.session_state[key]}")

    def should_disable_button(self):
        # Check if any of the required files are not uploaded
        return not self.uploaded_courses_file or not self.uploaded_ifunim_file

    def create_exam_schedule(self):
        print(f'self.moed : {self.moed_radio_button} self.semester : {self.semester} ')
        if self.moed_radio_button == 'ב':
            if self.uploaded_additional_file is None:
                st.toast(f"חסר לוח מועד א'", icon="⚠️")
                return
        if self.uploaded_courses_file is None:
            st.toast(f"חסר קובץ קורסים", icon="⚠️")
            return
        if self.uploaded_ifunim_file is None:
            st.toast(f"חסר קובץ אפיונים", icon="⚠️")
            return
        df_ifunim = dp.get_ifunim_dataframe_from_file(self.uploaded_ifunim_file, semester=self.semester)
        df_courses = dp.get_courses_dataframe_from_file(self.uploaded_courses_file)
        limitations_file = dp.get_limitations(self.uploaded_limits_file)
        exam_scheduler = ExamScheduler(df_ifunim, df_courses, limitations_file,
                                       start_date=str(self.start_date), end_date=str(self.end_date))
        exam_scheduler.schedule()

        # Display DataFrame
        self.df_place.dataframe(exam_scheduler.exam_schedule_table, height=1500, width=2000)


# Run the app
if __name__ == "__main__":
    app = ExamSchedulerApp()
