from exam_scheduler import ExamScheduler
import data_processing as dp
from tkinter import Tk, ttk, filedialog, messagebox,BOTH,NORMAL,DISABLED,TOP,X
import pandas as pd


class ExamScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("לוח מבחנים")
        self.root.geometry("800x400")
        self.root.iconbitmap('BIU_LOGO.jpg')
        self.external_file = None
        self.test_files_imported = False
        self.ifunim_imported = False
        self.df_ifunim = None
        self.df_courses = None
        
        
        self.columns = ("תאריך", "קוד קורס", "שם קורס")

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 12), padding=10)
        style.configure("Treeview", font=("Helvetica", 12))
        style.configure("Treeview.Heading", font=("Helvetica", 14, "bold"))

    def create_widgets(self):
        # Create a frame for the buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(side=TOP, fill=X, padx=10, pady=10)
        # Add buttons to the frame
        self.export_button = ttk.Button(button_frame, text="ייצוא לאקסל", command=self.export_to_excel, state=DISABLED)
        self.export_button.grid(row=0, column=0, padx=5, sticky='e')

        self.process_button = ttk.Button(button_frame, text="עיבוד נתונים", command=self.process_data, state=DISABLED)
        self.process_button.grid(row=0, column=1, padx=5, sticky='e')

        self.import_limitations_button = ttk.Button(button_frame, text="קובץ מגבלות", command=self.import_limitations)
        self.import_limitations_button.grid(row=0, column=2, padx=5, sticky='e')
        self.import_limitations_entry = ttk.Entry(button_frame)
        self.import_limitations_entry.grid(row=1, column=2, padx=5,pady=10 ,sticky='ew')
        
        self.import_courses_button = ttk.Button(button_frame, text="קובץ קורסים ", command=self.import_courses_file)
        self.import_courses_button.grid(row=0, column=3, padx=5, sticky='e')
        self.import_courses_entry = ttk.Entry(button_frame)
        self.import_courses_entry.grid(row=1, column=3, padx=5, pady=10, sticky='ew')
        
        self.import_ifunim_button = ttk.Button(button_frame, text="קובץ אפיונים ", command=self.import_ifunim)
        self.import_ifunim_button.grid(row=0, column=4, padx=5, sticky='e')
        self.import_ifunim_entry = ttk.Entry(button_frame)
        self.import_ifunim_entry.grid(row=1, column=4, padx=5, pady=10, sticky='ew')
        
        # Create a Treeview widget
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show='headings')
        self.tree.pack(fill=BOTH, expand=True)


            
    def display_data_in_gui(self, data):
        # Define the column headings
        for col in self.columns:
            self.tree.heading(col, text=col)

        # Insert the sample data
        for item in data:
            self.tree.insert('', 'end', values=item)
        
        
    def export_to_excel(self):
        # Ask the user for confirmation
        response = messagebox.askyesno("אישור ייצוא", "האם אתה בטוח שברצונך לייצא את הנתונים לאקסל?")
        if response:
            # Extract data from Treeview
            rows = []
            for row_id in self.tree.get_children():
                row = self.tree.item(row_id)['values']
                rows.append(row)

            # Create a DataFrame and export to Excel
            df = pd.DataFrame(rows, columns=self.columns)
            df.to_excel("לוח מבחנים.xlsx", index=False)
            messagebox.showinfo("ייצוא מוצלח", "הנתונים ייוצאו בהצלחה לקובץ לוח מבחנים.xlsx")
        else:
            messagebox.showinfo("ייצוא מבוטל", "הייצוא בוטל על ידי המשתמש")

    def import_limitations(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            self.external_file = file_path
            file_path = self.file_path_name_to_display(file_path)
            self.import_limitations_entry.delete(0, 'end')
            self.import_limitations_entry.insert(0, file_path)
            
    def import_courses_file(self):
        # Open file dialog to select test files
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            # Load the Excel file into a DataFrame
            self.df_courses = dp.get_courses_dataframe_from_file(file_path)
            self.test_files_imported = True
            self.check_ready_to_process()
            file_path = self.file_path_name_to_display(file_path)
            self.import_courses_entry.delete(0, 'end')
            self.import_courses_entry.insert(0, file_path)
            
  
        
        
    def import_ifunim(self):
        # Open file dialog to select limitations file
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            # Load the Excel file into a DataFrame
            self.df_ifunim = dp.get_ifunim_dataframe_from_file(file_path)
            # Here we simply print the limitations data for illustration
            self.ifunim_imported = True
            self.check_ready_to_process()
            file_path = self.file_path_name_to_display(file_path)
            self.import_ifunim_entry.delete(0, 'end')
            self.import_ifunim_entry.insert(0, file_path)
            
    def check_ready_to_process(self):
        if self.test_files_imported and self.ifunim_imported:
            self.process_button.config(state=NORMAL)

    def process_data(self):
        # Placeholder function for data processing
        df = dp.merge_ifunim_and_coursim(self.df_ifunim, self.df_courses)
        aa = ExamScheduler(df, external_file= self.external_file)
        aa.schedule_exams()
        self.export_button.config(state=NORMAL)
        data = list(aa.exam_schedule.itertuples(index=False, name=None))
        self.display_data_in_gui(data=data)
    
    @staticmethod
    def file_path_name_to_display(file_name):
        name_display = file_name.split('/')[-1].split('.xlsx')[0]
        return name_display
    
# Create the main application window
root = Tk()
app = ExamScheduleApp(root)
root.mainloop()
