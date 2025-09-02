# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import sys
try:
    import tkinter
except:
    print("fatal: Python3 tkinter module is not installed.")
    sys.exit(10)


def tkdiff(button, base, modi):
    os.system("/usr/bin/tkdiff %s %s &" % (base, modi))
    button.configure(bg="grey", fg="white")

def output(review_name, scm):
    root = tkinter.Tk()
    root.title(review_name)
    frm  = tkinter.Frame(root)
    row  = 0
    frm.grid()

    for f in scm.dossier_:
        base   = os.path.join(f.base_dir_, f.rel_path_)
        modi   = os.path.join(f.modi_dir_, f.rel_path_)
        label  = tkinter.Label(frm, text=f.action())
        button = tkinter.Button(frm, text=f.rel_path_)
        lamb   = lambda button=button, b=base, m=modi: tkdiff(button, b, m)
        button.configure(command=lamb)

        label.grid(column=0, row=row, sticky="nsew")
        button.grid(column=1, row=row, sticky="nsew")
        row = row + 1

    quit  = tkinter.Button(frm, text="Quit", command=root.destroy)
    quit.configure(bg="red", fg="white")
    quit.grid(column=1, row=row)

    root.mainloop()
