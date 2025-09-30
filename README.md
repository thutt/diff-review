# Software Prerequisites

- tkinter

This Python module must be installed to be able to generate the
Tcl/Tk-based menu used for viewing the generated diffs:

If this module is not installed, the `view-review` will stop
with an error indicating such.



At least one of the following utilities must be installed to fully use
this tool.

- TkDiff
- Meld

If these modules are not installed, the buttons in the menu will not
function, as each button is set to execute one of these programs to
view the differences.



# Description / Terminology


Change is omnipresent in the software industry.  To help you manage
changes to source, this tool enables viewing of uncommitted and
committed changes in a Git repository.

Before going further, let us take a moment to understand the
terminology used herein to describe the constituent parts of a change.
Each file contained in a change always has two components:


1. **Base file**

    The base file refers to the original file, before modifications
    have been made.  In most cases, the base file comes from the SCM,
    but in some cases, such as an `add`, the base file does not
    exist in the SCM.  When the base file does not exist in the SCM,
    and empty file is used in its stead.


2. **Modified file**

   The modified file, obviously, refers to the after-change file.

   For uncommitted changes, it usually refers to the change-containing
   on-disk file.  But, for modification such as `delete`, an empty
   file will be used.

   For committed changes, the modified file usually comes from the
   SCM, but case where the modified file no longer exists, such as
   `delete`, an empty file will be used in its place.

There are two modes in which this tool can operate: <em>uncommitted
changes</em>, and <em>committed changes</em>.


- **Uncommitted Changes**

  If no revision information (-c) is provided, `diff-review` will
  produce a review for for all `untracked`, `unstaged` and
  `staged` files.

  An uncommitted change includes all modified files, as well as
  `untracked` files, that are in the repository.  By default, they will
  all be included in the generated review, but a command line option
  can disable reviewing of untracked files.

  For purposes of generating viewable diffs, there is no difference
  between `unstaged` and `staged`; the tool uses the current, on-disk,
  uncommited content.

- **Committed Changes**

  If revision information (-c) is provided, `diff-review` will produce
  a review for all the files changed in the specified revision.

# Usage

1. Clone this repository to any location on the computer.  For
purposes of this text, we shall assume it has been placed at `~/diff-review`.


2. Load the `aliases` file.

   This alias file is for Bash users.  Those using some other
   incompatible shell will have to provide their own translation.  Any
   submissions will be gladly accepted.

   `source ~/diff-review/scripts.d/aliases`

   This will provide two aliases in your current shell environment:
   `dr` and `vr`.  These directly reference the `diff-review` and
   `view-review` programs respectively, bypassing the need to update
   `${PATH}`.

   The examples below will use these aliases.

# Examples

These examples with use `emacs` as the source of changes to review.
Take the time now to go get a basic `emacs` source tree:

    git clone https://github.com/emacs-mirror/emacs.git


If you prefer to use the official site, it is here, but it is
extremely slow:


    git clone https://git.savannah.gnu.org/git/emacs.git


## Set aliases in your shell environment

  As shown above in the <em>Usage</em> section, load the aliases into
  your shell.

## View a single committed change

  The following command will generate diffs for a  25-year-old `emacs`
  change.

```
dr -c a3ba27daef3
```

That command will produce the following output on the console:

```
diff-review:  /home/thutt/review/default

  modify   src/ChangeLog
  modify   src/gmalloc.c

Changes:  committed [2 files, 249 lines]
Viewer :  view-review -R /home/thutt/review -r default
Elapsed:  0:00:00.111161
```

The lines beginning with `TkDiff` and `Meld` are commands that can be
executed to view the diffs.  But, in this case since `dr` was used,
`vr` can be run to load the viewer for the diff.

```
vr
```

When the program showing the menu of files that can be reviewed is
focused, pressing `Esc` will quit.


## Combine and view multiple changes

  The following command will generate diffs for a sequential range of
  emacs commits.

```
dr -c 4418a37c5df^..cb17a8bbf39
```

It will produce the following console output:


That command will produce the following output on the console, which
can be viewed by executing `vr`:

```
diff-review:  /home/thutt/review/default

  modify   admin/notes/unicode
  modify   doc/lispref/modes.texi
  modify   doc/lispref/parsing.texi
  modify   doc/lispref/positions.texi
  modify   lisp/comint.el
  modify   lisp/dired-x.el
  modify   lisp/emacs-lisp/easy-mmode.el
  modify   lisp/emacs-lisp/ring.el
  modify   lisp/international/mule-cmds.el
  modify   lisp/international/ucs-normalize.el
  modify   lisp/net/eww.el
  modify   lisp/net/rcirc.el
  modify   lisp/progmodes/gdb-mi.el
  modify   lisp/progmodes/php-ts-mode.el
  modify   lisp/subr.el
  modify   lisp/time.el
  modify   lisp/vc/log-edit.el
  modify   lisp/vc/vc.el
  modify   src/doc.c
  modify   src/editfns.c
  modify   test/lisp/comint-tests.el
  modify   test/lisp/dom-tests.el
  modify   test/lisp/international/mule-tests.el
  modify   test/lisp/international/ucs-normalize-tests.el
  modify   test/lisp/net/tramp-tests.el
  modify   test/lisp/textmodes/ispell-resources/fake-aspell-new.bash
  modify   test/lisp/textmodes/ispell-tests/ispell-aspell-tests.el
  modify   test/lisp/textmodes/ispell-tests/ispell-hunspell-tests.el
  modify   test/lisp/textmodes/ispell-tests/ispell-international-ispell-tests.el
  modify   test/lisp/textmodes/ispell-tests/ispell-tests.el

Changes:  committed [30 files, 378 lines]  
Viewer :  view-review -R /home/thutt/review -r default
Elapsed:  0:00:00.594228

```

## View uncommitted changes

This example will show how untracked, unstaged and staged changes are
processed. 

Execute the following:

```
touch untracked
cat README README >readme
mv readme README
git rm config.bat
```

Now, run `dr`, which will produce the console output:

```
diff-review:  /home/thutt/review/default

   unstaged   README
     delete   config.bat
  untracked   untracked

Changes:  unstaged [1 files, 130 lines]  staged [1 files  384 lines]
Viewer :  view-review -R /home/thutt/review -r default
Elapsed:  0:00:00.116628
```

As ever, `vr` can be used to view the changes.

Next, stage the `README` file and re-generate the diffs with `dr`.

```
git add README

```

The console output will appear like this:

```
diff-review:  /home/thutt/review/default

     staged   README
     delete   config.bat
  untracked   untracked

Changes:  unstaged [0 files, 0 lines]  staged [2 files  514 lines]
Viewer :  view-review -R /home/thutt/review -r default
Elapsed:  0:00:00.115293

```

Finally, make another modification to `README` to show how its state
returns to `unstaged` after executing `dr`.

```
cp BUGS README
```

The console output will look like this:

```
diff-review:  /home/thutt/review/default

   unstaged   README
     delete   config.bat
  untracked   untracked

Changes:  unstaged [1 files, 274 lines]  staged [2 files  514 lines]
Viewer :  view-review -R /home/thutt/review -r default
Elapsed:  0:00:00.114766
```

## Clean up repository

Now that the examples are finished, you can delete the `emacs` clone.

# Advanced Usage

Invoking either `dr` or `vr` with `--help` will show the current set
options that the program takes.  Using these options will allow more
complex invocations -- such as naming the output, or putting it into a
different directory location.
