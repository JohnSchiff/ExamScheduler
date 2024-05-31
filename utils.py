import pandas as pd

def are_strings_same(string1:str, string2:str) -> bool:
    """
        
    a = 'מבוא לכלכלה-מיקרו'
    b = 'מבוא לכלכלה - מיקרו'
 
    """
    word1 = string1.replace(" ","")
    word1 = word1.replace("-", "")
    word2 = string2.replace(" ","")
    word2 = word2.replace("-", "")
    return word1==word2

def create_dict_of_classes(df):
    path_dict= {}
    for index, row in df.iterrows():
            for path in row['אפיון'].split(','):
                if path in path_dict.keys():
                    path_dict[path].append(row['שם'])
                else:
                    path_dict[path] = [row['שם']]
    return path_dict

def get_rows_of_programs_names(df: pd.DataFrame) -> list[int]:
    prgrams_names_rows = df[df.count(axis=1)==1].index.to_list()
    last_row = prgrams_names_rows[-1]
    if last_row == len(df) - 1:
        prgrams_names_rows.remove(last_row)
    return prgrams_names_rows


def get_programs_names(df: pd.DataFrame,prgrams_names_rows ) -> list[str]:
    programs_names = df.loc[prgrams_names_rows][0].to_list()
    programs_names = [name.strip() for name in programs_names]
    return programs_names
    
def filter_out_based_on_values(df: pd.DataFrame, col: int|str, values: list) -> pd.DataFrame:
    if not isinstance(values, list):
        values = [values] 
    df = df.loc[~ df[col].isin(values)]
    return df


def handle_course_code_value(df):
    """
    Convert code from string to integer
    """
    kod = 'קוד'
    if kod not in df.columns:
        return print(f'must have {kod} column')
    # Get code course without sub-course, i.e the dash sign
    df[kod] = df[kod].str.split('-').str[0].str.strip()
    # Convert to numneric
    df[kod] = pd.to_numeric(df[kod], errors='coerce')
    # Drop rows with No code for course
    df = df.dropna(subset=kod)
    # Convert from Float to Int
    df.loc[:,kod] = df[kod].astype(int)
    return df