class Logger:
    def __init__(self,name=""):
        self.name=name
        self.remarks = []
        self.remarks.append("Name: "+str(name))

    def add_remark(self, remark):
        self.remarks.append(remark)

    def save_to_file(self, filename):
        with open(filename, 'w') as file:
            for remark in self.remarks:
                file.write(remark + '\n')

    def print_log(self):
        for remark in self.remarks:
            print(remark)

logger=Logger("Global Logger")