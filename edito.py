'''
code file: edito.py
date: Feb 22, 2021
comments:
    Very Little Text Editor
    to use only for single
    purpose.
use:
    python3 edito.py file_to_edit
'''
from tkinter import *
from tkinter.ttk import *  # defaults all widgets as ttk
from tkinter import messagebox
import os, sys
import iniproc  # ini file reader module (local)
from tkinter.font import Font
from ttkthemes import ThemedTk  # ttkthemes is applied to all widgets
from tkinter import messagebox

class Application(Frame):
    ''' main class docstring '''
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.pack(fill=BOTH, expand=True, padx=4, pady=4)
        self.create_widgets()

    def create_widgets(self):
        ''' creates GUI for app '''
        # expand widget to fill the grid
        self.columnconfigure(1, weight=1, pad=100)
        self.rowconfigure(1, weight=1, pad=20)
        root.geometry("430x300+100+100")

        self.txt = Text(self, padx=5, bg=bg_, fg=fg_)
        self.txt.grid(row=1, column=1, sticky='ewns')
        efont = Font(family=font_, size=size_)
        self.txt.configure(font=efont)
        self.txt.config(wrap = NONE, # wrap = NONE
               undo = True, # Tk 8.4
               width = 40,
               height= 12,
               insertbackground=cursor_,
               tabs = (efont.measure(' ' * 4),))
        self.txt.focus()

        self.scrolly = Scrollbar(self, orient=VERTICAL, command=self.txt.yview)
        self.scrolly.grid(row=1, column=2, sticky='wsn')  # use nse
        self.txt['yscrollcommand'] = self.scrolly.set

        btnClose = Button(self, text='Save & Close',
                          command=self.btnClose_click,
                          width=20)
        btnClose.grid(row=2, column=1, pady=15)

        # attempt to read file
        if len(sys.argv) < 2:
            print("missing file name")
            sys.exit()

        try:
            with open(sys.argv[1]) as fh:
                text = fh.read()
                self.txt.insert("1.0", text)
                root.title(os.path.basename(sys.argv[1]))
        except Exception as e:
            messagebox.showerror("Error", e)


    def btnClose_click(self):
        ''' save the file and exit program '''
        text = self.txt.get("1.0", END).strip() + "\n"
        with open(sys.argv[1], "w") as fh:
            fh.write(text)
        messagebox.showinfo("Alert!", "Restart sqlcel.py for changes to take effect.")
        root.destroy()


# get sqlcel.ini values
fg_, bg_, font_, size_, cursor_, wtheme_ = iniproc.read("sqlcel.ini",
                                                'Foreg',
                                                'Backg',
                                                'Font',
                                                'Size',
                                                'Cursor',
                                                'WinTheme'
                                                )

# ttkthemes
# 'alt', 'scidsand', 'classic', 'scidblue',
# 'scidmint', 'scidgreen', 'default', 'scidpink',
# 'arc', 'scidgrey', 'scidpurple', 'clam', 'smog'
# 'kroc', 'black', 'clearlooks'
# 'radiance', 'blue' : https://wiki.tcl-lang.org/page/List+of+ttk+Themes
root = ThemedTk(theme=wtheme_)

# change working directory to path for this file
p = os.path.realpath(__file__)
os.chdir(os.path.dirname(p))


root.title("Mi Edito")
# root.protocol("WM_DELETE_WINDOW", save_location)  # UNCOMMENT TO SAVE GEOMETRY INFO
Sizegrip(root).place(rely=1.0, relx=1.0, x=0, y=0, anchor=SE)
# root.resizable(None,None) # no resize & removes maximize button
root.minsize(430, 300)  # width, height
app = Application(root)
app.mainloop()
