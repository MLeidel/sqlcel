'''
sqlcel.py
Michael Leidel Nov 2020
updated: Feb 2024 - fix for module updates and remove ";" requirement. Added WinTheme.


███████  ██████  ██       ██████ ███████ ██
██      ██    ██ ██      ██      ██      ██
███████ ██    ██ ██      ██      █████   ██
     ██ ██ ▄▄ ██ ██      ██      ██      ██
███████  ██████  ███████  ██████ ███████ ███████
            ▀▀
'''
from tkinter import *
from tkinter.ttk import *  # defaults all widgets as ttk
from tkinter.font import Font
from tkinter import messagebox
from tkinter import filedialog
import os, io, sys
import logging
import threading
import subprocess
from ttkthemes import ThemedTk  # ttkthemes applied to all widgets
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from PIL import Image, ImageTk
import pandas as pd
import matplotlib.pyplot as plt
import iniproc  # ini file reader module (local)

#   OS
#   Linux
PYTHON = "python3"
#   Windows
# PYTHON = "pythonw.exe"

# change working directory to path for this file
p = os.path.realpath(__file__)
os.chdir(os.path.dirname(p))

# sql can set its own limits - so open it up
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
#pd.options.display.float_format = '{:,.2f}'.format

# get sqlcel.ini values
fg_, bg_, font_, size_, cursor_, tab_, ofg_, obg_, ofont_, \
remark_, section_, literal_, number_, wtheme_ = iniproc.read("sqlcel.ini",
                                                'Foreg',
                                                'Backg',
                                                'Font',
                                                'Size',
                                                'Cursor',
                                                'Tab',
                                                'Ofg',
                                                'Obg',
                                                'Ofont',
                                                'Remark',
                                                'Section',
                                                'Literal',
                                                'Number',
                                                'WinTheme'
                                                )

tbl_info = ""
SQL_file = ""
RUN_CONSOLE = False
DF = 0  # copy of displayed df. Used by launch_plotter
t = None

def edit_check():
    ''' Prompting to leave unsaved edits
        example: if edit_check() is False:
                    return
    '''
    resp = True
    if code.edit_modified():
        resp = messagebox.askokcancel('Confirm Edits',
                                      'Edits not saved\nOK to Leave Editing?')
    return resp

def open_sql(e=None):
    ''' Dialog to load SQL code file '''
    global SQL_file
    if edit_check() is False:
        return
    fsql = filedialog.askopenfilename(filetypes=(("All text", "*.txt"),
                                                 ("SQL", "*.sql"), ("All", "*.*")))
    if fsql:
        with open(fsql) as fh:
            content = fh.read()
            code.delete("1.0", END) # clear the Text widget
            code.insert(END, content) # insert the text
            SQL_file = fsql
            code.edit_modified(False)
            frm_sql.config(text="     SQL Code " + "- " + os.path.basename(fsql) + "   ")

def save_sql(e=None):
    ''' Dialog to save the SQL code file '''
    global SQL_file
    fsave = filedialog.asksaveasfilename(confirmoverwrite=True,
                                         initialdir=os.path.dirname(os.path.abspath(__file__)))
    if fsave:
        SQL_file = fsave
        file_save(None)
        frm_sql.config(text="     SQL Code " + "- " + os.path.basename(SQL_file) + "   ")


def file_save(event=None):
    ''' Save (write) the SQL code file  '''
    global SQL_file

    if len(SQL_file) < 2:
        save_sql(None)
        return

    if messagebox.askokcancel('Quick Save', 'OK to save: ...' + SQL_file[-16:]) is True:
        try:
            with open(SQL_file, "w") as fh:
                code.focus()
                fh.write(code.get("1.0", END)) # contents of SQL code Text widget
                # messagebox.showinfo("Save File", "Sql File Saved")
                code.edit_modified(False)
        except:
            messagebox.showerror("Save File", "Failed to save file\n'%s'" % SQL_file)
        return


def add_df_src(event=None):
    '''
    Dialog to locate input file and insert lines at cursor of code Text widget.
    Example:
        Input;
        Excelfiles/abcd1.xlsx
        0
        tbl
    0 can be changed to an actual sheet name
    tbl should be renamed to a name appropriate to the information in the table (file)
    '''
    f = filedialog.askopenfilename(filetypes=(("Excel", "*.xls*"),
                                              ("CSV text", "*.csv"),
                                              ("Sqlite", "*.*")))
    if f:
        new_code = "Input\n" + f + "\n0\ntbl\n\n"
        inx = code.index(INSERT)
        code.insert(inx, new_code)
        code.focus()


def quit_sql(event=None):
    ''' confirm program exit and exit or not '''
    if edit_check() is False:
        return
    if messagebox.askokcancel('SequelCell', 'OK to Exit?') is True:
        with open("winfoxy", "w") as fout:
            fout.write(str(root.winfo_x()) + "\n" + str(root.winfo_y()))
        t.cancel()  # stop the syntax colorize timer
        root.destroy()


#
# Handler functions for bottom frame
#

def select_all(event=None):
    ''' Select all contents in the output Text widget or code widget '''
    if event is None:
        # button click
        txt.focus()
        txt.tag_add(SEL, '1.0', END)
        txt.mark_set(INSERT, '1.0')
        txt.see(INSERT)
    else:
        # Ctrl-a bind to both code and txt
        event.widget.focus()
        event.widget.tag_add(SEL, '1.0', END)
        event.widget.mark_set(INSERT, '1.0')
        event.widget.see(INSERT)

def df_info_view():
    '''
    Actions for the "table info" button.
    1. Display a sample of the (dataframe) if a file path was selected .. or ..
    2. Popup the df.info for the last SQL execution result
    '''
    global tbl_info
    txt.focus()
    try:
        item = "0"  # default sheet 0
        tsel = code.selection_get()
        tsel = tsel.strip()
        code.tag_remove(SEL, "1.0", END)  # remove selection
        if len(tsel) > 4:
            # just the path or path & table name ?
            if "\n" in tsel:
                lst = tsel.split("\n")
                tsel = lst[0]   # this is the fullpath
                item = lst[1]   # could be numeric or alphanumeric
            else:
                route_msg("Note: No Sheet Selected", "Preview will be sheet 0", "info")
            if tsel.lower().endswith("xlsx") or tsel.lower().endswith("xls"):
                if item.isnumeric():
                    df = pd.read_excel(tsel, sheet_name=int(item), parse_dates=True)  # , parse_dates=True
                else:
                    df = pd.read_excel(tsel, sheet_name=item, parse_dates=True)
            elif tsel.lower().endswith("csv"):
                df = pd.read_csv(tsel, low_memory=False, encoding='utf-8')
            else:
                route_msg("Invalid Selection", "Preview only CSV and XLS(X) files", "warning")
                return

                # engine = create_engine('sqlite:///' + tsel, echo=False)
                # conn = engine.connect()
                # df = pd.read_sql_table('snippet', conn, parse_dates=True)
                # conn.close()

            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_').str.replace('(', '').str.replace(')', '')
            data_top = df.head()
            # display
            txt.insert(END, data_top)
            txt.insert(END, "\n")
            txt.insert(END, str(df.shape))
            txt.insert(END, "\n")
            return  # that's it, leave this method
    except:
        pass

    if tbl_info == "":  # may be empty if no SQL was run yet
        return

    tl = Toplevel()
    tl.wm_title("Info")
    L = Label(tl)
    L.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    L['text'] = tbl_info


def clear_output():
    ''' deletes everyting in the output Text widget and clears output information '''
    global tbl_info
    var_bottom.set("")
    txt.delete("1.0", END)
    tbl_info = ""


def alter_output_size(s):
    ''' changes text size based on Scale widget command '''
    newsize = Font(family=ofont_, size=int(float(s)))
    txt.config(font=newsize,
               tabs=(newsize.measure(' ' * 3), ))


def launch_plotter():
    ''' Popup to set and display xy plot using current table items '''
    global DF
    npcols = DF.columns.values
    ax = plt.gca()
    colistx = npcols.tolist()
    colisty = npcols.tolist()
    colistx.insert(0, "X COLUMN")
    colisty.insert(0, "Y COLUMN")


    def set_exec_plot():
        k = var_kind.get()
        x = var_x.get()
        y = var_y.get()
        cx = var_cx.get()

        if k == 'TYPE OF PLOT' or x == 'X COLUMN' or y == 'Y COLUMN' or cx == 'COLOR X':
            route_msg("Plot Setting Error", "One or more unset parameters", "error")
            return
        DF.plot(kind=k, x=x, y=y, color=cx, ax=ax)
        btn_plot['state'] = 'normal'


    def exec_plot():
        plt.show()
        pt.destroy()


    def plot_parm(*args):
        btn_plot.configure(state=DISABLED)


    pt = Toplevel()
    pt.wm_title("Plot")
    pt.geometry("220x245")  # Windows 220x185

    optionlist = ('TYPE OF PLOT', 'line', 'bar', 'scatter')
    var_kind = StringVar()
    var_kind.set(optionlist[0])
    OptionMenu(pt, var_kind, *optionlist).pack(pady=3, padx=3, fill=X)

    optionlist = colistx
    var_x = StringVar()
    var_x.set(optionlist[0])
    OptionMenu(pt, var_x, *optionlist).pack(pady=3, padx=3, fill=X)
    var_x.trace("w", plot_parm)

    optionlist = colisty
    var_y = StringVar()
    var_y.set(optionlist[0])
    OptionMenu(pt, var_y, *optionlist).pack(pady=3, padx=3, fill=X)
    var_y.trace("w", plot_parm)

    optionlist = ('COLOR X', 'red', 'blue', 'orange', 'black', 'green', 'purple')
    var_cx = StringVar()
    var_cx.set(optionlist[0])
    OptionMenu(pt, var_cx, *optionlist).pack(pady=3, padx=3, fill=X)
    var_cx.trace("w", plot_parm)

    btn_set = Button(pt, text='Set', command=set_exec_plot, width=20)
    btn_set.pack(pady=3, padx=3, fill=X)

    btn_plot = Button(pt, text='Plot', command=exec_plot, width=20, state='disabled')
    btn_plot.pack(pady=3, padx=3, fill=X)


#
# Functions to handle SQL execution
#

def create_df(filename, n, dates):
    '''
    Reads datafile and returns a Pandas DataFrame object
    Limited to one sheet per file request
    n is either named sheet or zero (0 meaning 1st sheet in the workbook)
    Sheet info is irrevelant for csv files
    n is the table name for sqlite files!
    '''
    try:
        if filename.endswith('xlsx') or filename.endswith('xls'):
            if n.isnumeric():
                # df = pd.read_excel(filename, sheet_name=int(n), parse_dates=dates)  # , parse_dates=True
                # Load spreadsheet
                df = pd.ExcelFile(filename).parse(sheet_name=int(n), parse_dates=dates)
            else:
                df = pd.ExcelFile(filename).parse(n, parse_dates=dates)
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_').str.replace('(', '').str.replace(')', '')
        elif filename.endswith('csv'):
            df = pd.read_csv(filename, parse_dates=dates, encoding='utf-8')
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_').str.replace('(', '').str.replace(')', '')
        else:
            engine = create_engine('sqlite:///' + filename, echo=False)  # , encoding='utf-8'
            conn = engine.connect()
            df = pd.read_sql_table(n, conn, parse_dates=dates)
            conn.close()
        return df
    except Exception as e:
        route_msg("Input Problem", e, "error")


def display_results(df):
    '''
    Create a string holding the new df info
        popup window uses this string
            and
    display the new SQL result (df) in the output Text widget
    '''
    global tbl_info
    global DF
    if RUN_CONSOLE:
        print(df)
    else:
        buf = io.StringIO()
        df.info(verbose=True, buf=buf)  # show_counts for Windows
        tbl_info = buf.getvalue()  # holds df.info string
        lst = tbl_info.split("\n")
        x = lst[1]
        rows = between(x, "RangeIndex: ", " entries")
        y = lst[2]
        cols = between(y, "Data columns (total ", " columns):")
        tblinfo = "{} rows, {} cols".format(rows, cols)
        var_bottom.set(tblinfo)
        txt.delete("1.0", END)
        txt.insert("1.0", df)
        txt.insert(END, "\n")
        DF = df.copy()
        frm_out.config(text="     SQL Output ")


def between(s, leader, trailer):
    '''
    Pull columns out of sql "select" statement
    Uses the keywords 'select ' and ' from'
    SQL keywords are case insensitive
    '''
    s = s.replace("distinct", "")  # for parsing the sql code columns
    s = s.replace("\n", " ")   # eliminate new lines for accurate parsing
    end_of_leader = s.lower().index(leader.lower()) + len(leader)  # case insensitive target
    start_of_trailer = s.lower().index(trailer.lower(), end_of_leader)  # case insensitive target
    cols = s[end_of_leader:start_of_trailer]
    return cols


def processCodeFile(e=None):
    '''
    "Execute" button was clicked
    Obtain the sql code file content for processing
    '''
    if RUN_CONSOLE is True:
        with open(SQL_file) as fh:
            sql = fh.read()
    else:
        '''
        When "Input:" code is present in the code window, the user can request
        to view the entire dataframe by selecting the fullpath and clicking "Execute"
        Note: poorly formed column names are re-constructed for usability
        (but not in the source file itself.)
        '''
        txt.focus()

        if code.tag_ranges(SEL):
            tsel = code.selection_get()
            if len(tsel) > 4:
                item = "0"  # default sheet 0
                tsel = tsel.strip()
                if "\n" in tsel:
                    lst = tsel.split("\n")
                    tsel = lst[0]   # this is the fullpath
                    item = lst[1]   # could be numeric or alphanumeric
                else:
                    route_msg("Note: No Sheet Selected", "Listing will be for sheet 0", "info")
                if tsel.lower().endswith("xlsx") or tsel.lower().endswith("xls"):
                    if item.isnumeric():
                        df = pd.read_excel(tsel, sheet_name=int(item), parse_dates=True)  # , parse_dates=True
                    else:
                        df = pd.read_excel(tsel, sheet_name=item, parse_dates=True)
                elif tsel.lower().endswith("csv"):
                    df = pd.read_csv(tsel, low_memory=False, encoding='utf-8')
                else:
                    route_msg("Invalid Selection", "Preview only CSV and XLS(X) files", "error")
                    return  # preview of Sqlite is not implemented
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_').str.replace('(', '').str.replace(')', '')
                # display the whole table (df)
                txt.insert(END, df)
                txt.insert(END, "\n")
                return  # that's it, leave this method

        sql = code.get("1.0", END)

    if RUN_CONSOLE is False:
        frm_out.config(text=" P r o c e s s i n g . . . ")
        frm_out.update()

    exec_sql(sql)

########################################################################

def exec_sql(sql):
    '''
    Setup the spreadsheet with pandas and sqlalchemy then execute the users sql statement
    display result in GUI and optional output to excel or csv
    '''
   # PARSE CODE FILE TO SETUP VARIABLE LISTS

    parser = 9  # flag for primitive parsing logic

    sql_file = []  # list of lines of code
    sql_code = ""  # just the SQL select statement
    sql_infile = []
    sql_sheet = []
    sql_tbl = []  # sheet number 0 default
    outpath = None
    datelist = None  # date reformating

    sql_file = sql.split("\n")

    for line in sql_file:

        ln = line.strip()

        if ln == "":
            continue
        if ln.startswith("#"):
            continue
        if ln[-1:] == ";":
            ln = ln[:-1]

        if parser == 11:  # Sql code must be LAST in code file
            sql_code = sql_code + ln + "\n"
            continue

        if ln.lower() == "output":
            if outpath is not None:
                route_msg("SQL File", "Only 1 'output;' path allowed", "error")
                return
            parser = 8
            continue

        if parser == 8:
            outpath = ln
            parser = 9
            continue

        if ln.lower() == "input":
            parser = 0
            continue

        if 0 <= parser <= 2:
            if parser == 0:
                sql_infile.append(ln)
            elif parser == 1:
                sql_sheet.append(ln)
            elif parser == 2:
                sql_tbl.append(ln)
                parser = 9  # done with this input file request
                continue
            parser += 1

        if ln.lower() == "datecols":
            parser = 10
            continue

        if parser == 10:
            datelist = ln.split(',')  # dates,dates,... to List
            parser = 9
            continue

        if ln.lower() == "sql":
            parser = 11
            continue

    if len(sql_infile) != len(sql_sheet) or len(sql_sheet) != len(sql_tbl):
        route_msg("SQL File", "Something wrong with input declarations", "error")
        return
    if not sql_code.lower().lstrip().startswith("select"):
        route_msg("SQL File", "Code missing in one or more sections.", "error")
        print(sql_code)
        return

    if datelist == None:  # No date cols declared in the code file
        datelist = True

    # CONNECT DATAFRAMES TO SQL ENGINE, CREATE TABLES AND EXECUTE SQL

    # engine = create_engine('sqlite://', echo=False, encoding='utf-8')
    engine = create_engine('sqlite://', echo=False)

    cols = between(sql_code, "select ", " from ")
    scols = ""
    nocomma = False
    # The following couple small bunches of code clean up the column names
    # by isolating function "," commas and removing unnecessary whitespace
    for c in cols:
        if c == "(":
            nocomma = True
        if c == ")":
            nocomma = False
        if c == ",":
            if nocomma is True:
                c = "^"
        scols += c

    list_of_cols = scols.split(",")
    list_of_cols = [i.strip() for i in list_of_cols]  # remove any whitespace around col names
    list_of_cols = [i.replace("^", ",") for i in list_of_cols]  # handle comma inside of column function


    if list_of_cols[0] == "*":
        # ALL COLUMNS '*' WORKS ONLY WITH ONE FILE REQUEST IN THE CODE FILE
        try:
            dataframe = create_df(sql_infile[0], sql_sheet[0], datelist)  # return df from file type
            dataframe.to_sql(sql_tbl[0], con=engine, if_exists='replace', index=True)

            with Session(engine) as session:
               results = pd.read_sql_query(sql_code, session.bind)
            final = pd.DataFrame(results, columns=dataframe.columns)

        except Exception as e:
            route_msg("SQL Syntax Error (single sheet)", e, "error")
        else:
            if not RUN_CONSOLE:
                display_results(final)

    else:  # WHEN MULTIPLE FILE REQUESTS APPEAR IN YOUR CODE - SQL STATEMENT MUST CONTAIN COLUMN NAMES

        # Input files are converted to DataFrames and registered as SQL tables
        for x in range(0, len(sql_tbl)):
            dataframe = create_df(sql_infile[x], sql_sheet[x], datelist)
            dataframe.to_sql(sql_tbl[x], con=engine, if_exists='replace', index=True)
            # Every thing is now ready to run the SQL against the tables
        try:
            # results = engine.execute(sql_code)
            #with Session(engine) as session:
               #results = pd.read_sql_query(sql_code, session.bind)
            results = pd.read_sql_query(sql_code, con=engine)
            final = pd.DataFrame(results)
        except Exception as e:
            route_msg("SQL Syntax Error (multiple sheets)", e, "error")
        else:
            #if not RUN_CONSOLE:
            display_results(final)

    # The Output; command can specify an output file for the results of the query
    if outpath is None:
        if RUN_CONSOLE is True:
            print("no output path")
    else:
        if outpath.endswith("xlsx") or outpath.endswith("xls"):
            final.to_excel(outpath, index=False)
        elif outpath.lower().endswith("csv"):
            final.to_csv(outpath, index=False)
        else:  # assuming sqlite then
            e = create_engine('sqlite:///' + outpath, echo=False)  # , encoding='utf-8'
            conn = e.connect()
            final.to_sql('table1', conn, if_exists='replace')
            conn.close()

        route_msg("Finished", "Output file created", "info")


def route_msg(title, text, typ):
    ''' directs GUI and CONSOLE runtime route_msg '''
    if RUN_CONSOLE:
        logging.debug(title + " - " + str(text))
        return

    frm_out.config(text="     SQL Output ")
    if typ == "error":
        messagebox.showerror(title, text)
    elif typ == "warning":
        messagebox.showwarning(title, text)
    else:  # assume its "info"
        messagebox.showinfo(title, text)
    return


def do_popup1(event):
    ''' handles right-click for context menu for code frame '''
    try:
        popup_code.tk_popup(event.x_root,
                            event.y_root)
    finally:
        popup_code.grab_release()

def pop1func(n):
    ''' Routes context menu actions for code frame '''
    if n == 1:  # Copy
        # FYI: pyperclip does not work with matplotlib
        root.clipboard_clear()  # clear clipboard contents
        root.clipboard_append(code.selection_get())  # append new value to clipbaord
    elif n == 2:  # Paste
        inx = code.index(INSERT)
        code.insert(inx, root.clipboard_get())
    else:  # Select All
        code.focus()
        code.tag_add(SEL, '1.0', END)
        code.mark_set(INSERT, '1.0')
        code.see(INSERT)

def do_popup2(event):
    ''' handles right-click for context menu for Output (display) frame '''
    try:
        popup_disp.tk_popup(event.x_root,
                            event.y_root)
    finally:
        popup_disp.grab_release()

def pop2func(n):
    ''' Routes context menu actions for Output frame '''
    if n == 1:  # Copy
        # FYI: pyperclip does not work with matplotlib
        root.clipboard_clear()  # clear clipboard contents
        root.clipboard_append(txt.selection_get())  # append new value to clipbaord
    elif n == 2:  # Paste
        inx = txt.index(INSERT)
        txt.insert(inx, root.clipboard_get())
    else:  # Select All
        select_all()

def highlite():
    ''' highlight code '''
    global t
    highlight_pattern(r'^[Ss][Qq][Ll]|^[Ii][Nn][Pp][Uu][Tt]|^[Oo][Uu][Tt][Pp][Uu][Tt]|^[Dd][Aa][Tt][Ee][Cc][Oo][Ll][Ss].*\n',
                      "sections", regexp=True)
    #highlight_pattern(r'^[IiSsOoDd].*\n', "sections", regexp=True)
    highlight_pattern(r"(\d+|\d\.\d|\.\d)", "numbers", regexp=True)
    highlight_pattern(r"[\"\'`](.*?)[\'\"`]", "literals", regexp=True)
    highlight_pattern(r'^#.*\n', "remarks", regexp=True)

    t = threading.Timer(1.25, highlite)  # every 1.5 seconds
    t.daemon = True  # for threading runtime error
    t.start()

def highlight_pattern(pattern, tag, start="1.0", end="end", regexp=False):
    ''' highlight code '''
    start = code.index(start)
    end = code.index(end)
    code.tag_remove(tag, start, end)
    code.mark_set("matchStart", start)
    code.mark_set("matchEnd", start)
    code.mark_set("searchLimit", end)
    count = IntVar()
    while True:
        index = code.search(pattern, "matchEnd", "searchLimit",
                            count=count, regexp=True)
        if index == "":
            break
        if count.get() == 0:
            break # degenerate pattern which matches zero-length strings
        code.mark_set("matchStart", index)
        code.mark_set("matchEnd", "%s+%sc" % (index, count.get()))
        code.tag_add(tag, "matchStart", "matchEnd")

def enlarge_code_frame():
    ''' verticle length increase '''
    h = code.cget("height")
    h += 2
    code.config(height=h)

def shrink_code_frame():
    ''' verticle length decrease '''
    h = code.cget("height")
    if h > 10:
        h -= 2
        code.config(height=h)

def new_code_file():
    ''' clear code Text and reset Filename '''
    global SQL_file
    SQL_file = ""
    code.delete("1.0", END) # clear the Text widget

def edit_ini(e):
    '''
    this will have to change for hosting OS
    '''
    # os.system("python3 edito.py sqlcel.ini")
    subprocess.call([PYTHON, "edito.py", "sqlcel.ini"])

#
#    Check if console execution requested
#       arg 1 is the SQL code file name
#
if len(sys.argv) > 1:
    SQL_file = sys.argv[1]
    RUN_CONSOLE = True
    logging.basicConfig(filename='log_sqlcel.txt', level=logging.NOTSET,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug("sqlcel.py - console run started: " + SQL_file)

    processCodeFile()

    sys.exit()




root = ThemedTk(theme=wtheme_)  # sqlcel.ini

style = Style()
style.configure("TButton", width=9)

#
# SQL Code Frame
#

frm_sql = LabelFrame(root)

frm_sql.grid(row=1, column=1, pady=4, padx=5, sticky='w')
frm_sql.config(text="     SQL Code ")

btn_open = Button(frm_sql, text='Open', command=open_sql)
btn_open.grid(row=1, column=1, sticky='w', padx=5, pady=5)
btn_save = Button(frm_sql, text='Save', command=file_save)
btn_save.grid(row=2, column=1, pady=5, padx=5, sticky='w')
btn_exec = Button(frm_sql, text='Execute', command=processCodeFile)
btn_exec.grid(row=3, column=1, pady=5, padx=5, sticky='w')
btn_exec = Button(frm_sql, text='Add Input', command=add_df_src)
btn_exec.grid(row=4, column=1, pady=5, padx=5, sticky='w')
btn_quit = Button(frm_sql, text='Quit', command=quit_sql)
btn_quit.grid(row=5, column=1, pady=5, padx=5, sticky='w')

code = Text(frm_sql, bg=bg_, fg=fg_, padx=5)
code.grid(row=1, column=2, rowspan=5, sticky='nsew', padx=5, pady=5)
efont = Font(family=font_, size=size_)
code.config(font=efont)
code.config(wrap=NONE, # wrap = "word"
            undo=True, # Tk 8.4
            height=12,
            width=80,
            insertbackground=cursor_,
            tabs=(efont.measure(' ' * int(tab_)), ))

scrollY = Scrollbar(frm_sql, orient=VERTICAL, command=code.yview)
scrollY.grid(row=1, column=3, rowspan=5, sticky='nsw')
code['yscrollcommand'] = scrollY.set
scrollX = Scrollbar(frm_sql, orient=HORIZONTAL, command=code.xview)
scrollX.grid(row=6, column=2, sticky='sew')
code['xscrollcommand'] = scrollX.set

code.tag_configure("numbers", foreground=number_)
code.tag_configure("literals", foreground=literal_)
code.tag_configure("remarks", foreground=remark_)
code.tag_configure("sections", foreground=section_)

#
# frame inside of frm_sql to hold sizing buttons
#
control_frame = Frame(frm_sql)
control_frame.grid(row=1, column=4)
btn = Button(control_frame, text='↑', width=2,
                      command=shrink_code_frame)
btn.grid(row=1, column=1, sticky='we')
btn = Button(control_frame, text='↓', width=2,
                      command=enlarge_code_frame)
btn.grid(row=2, column=1, sticky='we')
btn = Button(control_frame, text='X', width=2,
                      command=new_code_file)
btn.grid(row=3, column=1, sticky='we')

splash = '''Welcome to SequelCell 2.2
Begin coding a query here Or Open an existing query
  Shorcuts:
    Control-s   Save
    Alt-s       Save As
    Control-q   Exit
    Control-a   Select All
    Escape      Exit
    Control-e   Execute
    Control-o   Open Sql File
    Control-i   Insert Data Source
    F7          Settings Editor
'''
code.delete("1.0", END) # clear the Text widget
code.insert(END, splash) # insert the text
code.edit_modified(False)

#
# SQL Output Frame
#

frm_out = LabelFrame(root, text="     SQL Output ")
frm_out.grid(row=2, column=1, pady=4, padx=5, sticky='nsew')

txt = Text(frm_out, bg=obg_, fg=ofg_)
txt.grid(row=1, column=1, sticky='nsew', padx=2, pady=2)
efont = Font(family=ofont_, size=11)
txt.configure(font=efont)
txt.config(wrap=NONE, # wrap = "word"
           tabs=(efont.measure(' ' * 4), ))
scrollY = Scrollbar(frm_out, orient=VERTICAL, command=txt.yview)
scrollY.grid(row=1, column=2, sticky='nsw')
txt['yscrollcommand'] = scrollY.set
scrollX = Scrollbar(frm_out, orient=HORIZONTAL, command=txt.xview)
scrollX.grid(row=2, column=1, sticky='sew')
txt['xscrollcommand'] = scrollX.set

#
# Bottom Frame
#

frm_bottom = Frame(root)
frm_bottom.grid(row=3, column=1)

var_bottom = StringVar()
bottom_label = Label(frm_bottom, textvariable=var_bottom)
bottom_label.grid(row=1, column=0, pady=7, padx=5)

btn_all = Button(frm_bottom, text='Select All', command=select_all)
btn_all.grid(row=1, column=1, pady=7, padx=5)

btn_info = Button(frm_bottom, text='Table Info', command=df_info_view)
btn_info.grid(row=1, column=2, pady=7, padx=5)

btn_info = Button(frm_bottom, text='Clear', command=clear_output)  # clear_output
btn_info.grid(row=1, column=3, pady=7, padx=5)

btn_graph = Button(frm_bottom, text='Plot XY', command=launch_plotter)
btn_graph.grid(row=1, column=4, pady=7, padx=5)

slider = Scale(frm_bottom, from_=6, to=18,
               value=11,
               orient=HORIZONTAL,
               length=100,
               command=alter_output_size)
slider.grid(row=1, column=5, padx=5, pady=7)


#Popups - code Text widget and df (disp) Text widget
popup_code = Menu(tearoff=0, title="title")
popup_code.add_command(label="Copy",
                       command=lambda: pop1func(1))
popup_code.add_command(label="Paste",
                       command=lambda: pop1func(2))
popup_code.add_separator()
popup_code.add_command(label="Select All", command=lambda: pop1func(3))
code.bind("<Button-3>", do_popup1)

popup_disp = Menu(tearoff=0)
popup_disp.add_command(label="Copy",
                       command=lambda: pop2func(1))
popup_disp.add_command(label="Paste",
                       command=lambda: pop2func(2))
popup_disp.add_separator()
popup_disp.add_command(label="Select All", command=lambda: pop2func(3))
txt.bind("<Button-3>", do_popup2)

# Row 4
Sizegrip(root).grid(row=4, column=1, sticky="se")

#
# Configure Rows / Columns
#

root.rowconfigure(2, weight=1, pad=10)  # Output frame
root.columnconfigure(1, weight=1)  # Sql frame

frm_out.columnconfigure(1, weight=1, pad=10)  # Output frame
frm_out.rowconfigure(1, weight=1, pad=10)  # Output frame


#
# Hot Keys
#
root.bind('<Control-s>', file_save)
root.bind('<Alt-s>', save_sql)
root.bind('<Control-q>', quit_sql)
root.bind('<Control-a>', select_all)
root.bind('<Escape>', quit_sql)
root.bind('<Control-e>', processCodeFile)
root.bind('<Control-o>', open_sql)
root.bind('<Control-i>', add_df_src)
root.bind('<F7>', edit_ini)


# Restore App to last position on user screen
if os.path.isfile("winfoxy"):
    lcoor = tuple(open("winfoxy", 'r'))  # no relative path for this
    root.geometry('960x640+%d+%d'%(int(lcoor[0].strip()), int(lcoor[1].strip())))
else:
    root.geometry("960x640") # WxH+left+top

root.minsize(880, 640)
root.title("SequelCell V2.3")
root.protocol("WM_DELETE_WINDOW", quit_sql)

highlite()  # start the syntax colorization timer loop

img = Image.open("sqlcel.ico")
img = ImageTk.PhotoImage(img)
root.iconphoto(False, img)

root.mainloop()
