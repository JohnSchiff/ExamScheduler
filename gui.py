from exam_scheduler import ExamScheduler
import data_processing as dp
from tkinter import ttk, filedialog, messagebox,NORMAL,DISABLED
import pandas as pd
from ttkthemes import ThemedTk
from PIL import Image, ImageTk

class ExamScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("שיבוץ בחינות")
        self.root.geometry("800x1200")
        self.external_file = None
        self.test_files_imported = False
        self.ifunim_imported = False
        self.df_ifunim = None
        self.df_courses = None
        
        
        # Load and resize the image
        image = Image.open('BIU_LOGO.jpg')  # Replace with your image path
        image = image.resize((150, 150), Image.LANCZOS)  # Resize as needed
        self.photo = ImageTk.PhotoImage(image)
        
        # Create a frame for the logo
        logo_frame = ttk.Frame(self.root)
        logo_frame.pack(pady=1, anchor="ne",fill="both")
        self.logo_label = ttk.Label(logo_frame, image=self.photo)
        self.logo_label.pack(side='right')
        s = ttk.Label(logo_frame, text=' מערכת שיבוץ בחינות',font=("Helvetica", 22, "bold"), foreground='black')
        s.pack(side="left", expand=True)

        
        self.columns = ("תאריך", "קוד קורס", "שם קורס")

        self.setup_styles()
        self.create_widgets()
        
    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 14), padding=5)
        style.configure("TEntry", font=("Helvetica", 14), padding=5)
        style.configure("TLabel", font=("Helvetica", 14))
        style.configure("Treeview", background="lightblue", font=("Helvetica", 14))
        style.configure("Treeview.Heading", font=("Helvetica", 14, "bold"))
        
        # Custom style for red asterisk
        style.configure("Red.TLabel", foreground="red", font=("Helvetica", 16, "bold"))

    def create_widgets(self):

        entries_frame = ttk.Frame(self.root)
        entries_frame.pack(fill='x')
# 
        self.import_limitations_button = ttk.Button(entries_frame, text="קובץ מגבלות", command=lambda: self.import_file('get_limitations_from_another_file', self.import_limitations_entry, 'external_file'))
        self.import_limitations_button.pack(padx=5, pady=5, side="right")
        self.import_limitations_entry = ttk.Entry(entries_frame)
        self.import_limitations_entry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        
        entries_frame2 = ttk.Frame(self.root)
        entries_frame2.pack(fill='x')
        self.import_courses_button = ttk.Button(entries_frame2, text="קובץ קורסים", command=lambda: self.import_file('get_courses_dataframe_from_file', self.import_courses_entry, 'df_courses'))
        self.import_courses_button.pack(side="right", padx=5)
        self.import_courses_entry = ttk.Entry(entries_frame2)
        self.import_courses_entry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.asterisk_label = ttk.Label(entries_frame2, text="*", foreground="red")
        self.asterisk_label.pack(side='right')
        
        
        entries_frame3 = ttk.Frame(self.root)
        entries_frame3.pack(fill='x')
        self.import_ifunim_button = ttk.Button(entries_frame3, text="קובץ אפיונים", command=lambda: self.import_file('get_ifunim_dataframe_from_file', self.import_ifunim_entry, 'df_ifunim'))
        self.import_ifunim_button.pack(side="right", padx=5)
        self.import_ifunim_entry = ttk.Entry(entries_frame3)
        self.import_ifunim_entry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.asterisk_label2 = ttk.Label(entries_frame3, text="*", foreground="red")
        self.asterisk_label2.pack(side='right')

        
        entries_frame4 = ttk.Frame(self.root)
        entries_frame4.pack(fill='x')
        self.process_button = ttk.Button(entries_frame4, text="צור לוח בחינות", command=self.process_data, state=DISABLED)
        self.process_button.pack(padx=5, pady=5)



        # Create a frame for the Treeview widget
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show='headings')
        self.tree.pack(fill="both", expand=True)
        # Add headings to the Treeview
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
            
        self.export_button = ttk.Button(self.root, text="ייצוא לאקסל", command=self.export_to_excel, state=DISABLED)
        self.export_button.pack(padx=5, pady=5)
        
    def display_data_in_gui(self, data):
        # Define the column headings
        for col in self.columns:
            self.tree.heading(col, text=col)

        # Insert the sample data
        for item in data:
            self.tree.insert('', 'end', values=item)
        
        
    def export_to_excel(self):
        # Ask the user for confirmation
        response = messagebox.askyesno("אישור ייצוא", "האם אתה בטוח שברצונך לייצא את לוח המבחנים לאקסל?")
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

                        
    def import_file(self, dp_function_name, entry_widget, dataframe_attribute):
        # Open file dialog to select Excel files
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            import pdb  
            import rlcompleter
            pdb.Pdb.complete=rlcompleter.Completer(locals()).complete
            pdb.set_trace() 
            # Load the Excel file into a DataFrame using the appropriate method
            dataframe = getattr(dp, dp_function_name)(file_path)
            setattr(self, dataframe_attribute, dataframe)
            # Set the file imported flag if applicable
            if dataframe_attribute == 'df_courses':
                self.test_files_imported = True
            elif dataframe_attribute == 'df_ifunim':
                self.ifunim_imported = True
            # Check if ready to process
            self.check_ready_to_process()
            # Update the entry widget with the file path
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, file_path)
        
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
    
# Create the main application window ThemedTk
if __name__ == "__main__": 
    root = ThemedTk(theme='blue')  
    app = ExamScheduleApp(root)
    root.mainloop()
