from exam_scheduler import ExamScheduler
import data_processing as dp
from tkinter import ttk, filedialog, messagebox,BOTH,NORMAL,DISABLED,TOP,X,Label, RIGHT
import pandas as pd
from ttkthemes import ThemedTk
from PIL import Image, ImageTk

#TODO delete imports when make it .exe
import os
import sys
class ExamScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("שיבוץ בחינות")
        self.root.geometry("800x800")
        self.external_file = None
        self.test_files_imported = False
        self.ifunim_imported = False
        self.df_ifunim = None
        self.df_courses = None
        
        
        # Load and resize the image
        image = Image.open('BIU_LOGO.jpg')  # Replace with your image path
        image = image.resize((150, 150), Image.LANCZOS)  # Resize as needed
        # Convert the Image object into a Tkinter-compatible photo image
        self.photo = ImageTk.PhotoImage(image)
        
        # Create a Label widget to display the image
        self.logo_label = ttk.Label(self.root, image=self.photo)
        self.logo_label.grid(row=0, column=0, sticky="e", padx=5, pady=5) 
        self.root.grid_columnconfigure(0, weight=1)
        # self.root.grid_columnconfigure(1, weight=1)
        # self.root.grid_rowconfigure(1, weight=1)
        # Convert Image object to Tkinter PhotoImage object
        
        self.columns = ("תאריך", "קוד קורס", "שם קורס")

        self.setup_styles()
        self.create_widgets()
        # self.configure_grid()
        
    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 14), padding=5)
        style.configure("TEntry", font=("Helvetica", 14), padding=5)
        style.configure("TLabel", font=("Helvetica", 14))
        style.configure("Treeview", font=("Helvetica", 14))
        style.configure("Treeview.Heading", font=("Helvetica", 14, "bold"))
        
        # Custom style for red asterisk
        style.configure("Red.TLabel", foreground="red", font=("Helvetica", 16, "bold"))

    def create_widgets(self):
        # Create a frame for the buttons
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        button_frame.grid_columnconfigure(0, weight=1)
        # Add buttons to the frame
        self.export_button = ttk.Button(button_frame, text="ייצוא לאקסל", command=self.export_to_excel, state=DISABLED)
        self.export_button.grid(row=0, column=0, padx=5, sticky='e')

        self.process_button = ttk.Button(button_frame, text="צור לוח בחינות", command=self.process_data, state=DISABLED)
        self.process_button.grid(row=0, column=1, padx=5, sticky='e')

        self.import_limitations_entry = ttk.Entry(button_frame)
        self.import_limitations_entry.grid(row=1, column=2, padx=5,pady=10 ,sticky='ew')
        self.import_limitations_button = ttk.Button(button_frame, text="קובץ מגבלות", command= lambda:self.import_file('get_limitations_from_another_file',self.import_limitations_entry,'external_file'))
        self.import_limitations_button.grid(row=0, column=2, padx=5, sticky='e')
        
        self.import_courses_entry = ttk.Entry(button_frame)
        self.import_courses_entry.grid(row=1, column=3, padx=5, pady=10, sticky='ew')
        self.courses_asterisk = ttk.Label(button_frame, text="*", font=("Helvetica", 16, "bold"), style="Red.TLabel")
        self.courses_asterisk.grid(row=1, column=3, padx=5, sticky='w')
        self.import_courses_button = ttk.Button(button_frame, text="קובץ קורסים ", command= lambda:self.import_file('get_courses_dataframe_from_file',self.import_courses_entry,'df_courses'))
        self.import_courses_button.grid(row=0, column=3, padx=5, sticky='e')
        
        self.import_ifunim_entry = ttk.Entry(button_frame)
        self.import_ifunim_entry.grid(row=1, column=4, padx=5, pady=10, sticky='ew')
        self.ifunim_asterisk = ttk.Label(button_frame, text="*",style="Red.TLabel", font=("Helvetica", 16, "bold"))
        self.ifunim_asterisk.grid(row=1, column=4, padx=5, sticky='w')
        self.import_ifunim_button = ttk.Button(button_frame, text="קובץ אפיונים ", command=lambda:self.import_file('get_ifunim_dataframe_from_file',self.import_ifunim_entry,'df_ifunim'))
        self.import_ifunim_button.grid(row=0, column=4, padx=5, sticky='e')
        

        # Create a Treeview widget
        tree_frame = ttk.Frame(self.root)
        tree_frame.grid(row=2, column=0)

        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show='headings')
        self.tree.grid(row=3, column=0)
        
        
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

                        
    def import_file(self, dp_function_name, entry_widget, dataframe_attribute):
        # Open file dialog to select Excel files
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
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
            file_path_display = self.file_path_name_to_display(file_path)
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, file_path_display)
        
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
    
# Create the main application window ThemedTk
if __name__ == "__main__": 
    root = ThemedTk(theme='equilux')  
    app = ExamScheduleApp(root)
    root.mainloop()
