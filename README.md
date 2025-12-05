# What It Does

This repository presents  is a graphical application for reviewing file
differences in a side-by-side view. It's designed for systematic code
review workflows where multiple file diffs need to be examined,
annotated, and navigated efficiently.  Core Concept

The application displays changes from version control systems - either
committed changes or in-progress uncommitted modifications. Multiple
file diffs are organized in a tabbed interface with a file list
sidebar, allowing reviewers to systematically work through all changes
in a changeset.


# Software Prerequisites

- <code>python3</code>

  An executable named <code>python3</code> must be installed and on ${PATH}.

- <code>pyqt6</code>

This Python module must be installed to be able to generate the
Tcl/Tk-based menu used for viewing the generated diffs:

If this module is not installed, the `view-review` will stop
with an error indicating such.

On Ubuntu, this can be satisfied with:

    sudo apt install python3-pyqt6

- <code>requests</code>

To use the '--url' option of <code>vrt</code> and fetch diffs from a
URL, you must have the <code>requests</code> module installed.

On MacOS, and Windows <code>cmd.exe</code>, this can be satisfied with:

    pip3 install requests


- <code>keyring</code>

The Python keyring module is an interface to the host OS key ring, and
its use facilitates only having to enter your credentials for
URL-based diff viewing once.

It can be installed with pip, on MacOS and Windows, and some Linux
distributions:

    pip3 install keyring

On Ubuntu, it must be installed with:

    sudo apt install python3-keyring

If you prefer to not use this, you can add '--no-keyring' to the 'vrt'
invocation.  However, if keyring cannot be imported, the software will
also transparently not use it.

# Supported Operating Systems

 - Linux
 - MacOS
 - Windows

#  `view-review-tabs` (`vrt`)

This tool shows a single window, with the list of files contained in
the change -- including the commit message, if one is present -- in
the sidebar.  Clicking on an element in the sidebar loads it into a
tab in the view area.

This tool only provides viewing diffs with the built-in diff engine,
but the entire UI surrounding the diffs exposes many capabilities that
give a better holistic approach to reviewing code.


# `view-review` (`vr`)

This, older, tool shows a menu of all the files in the change.
Clicking on an element in the list will open the base and modified
files in a separate window using the selected diff viewer.

Ultimately, the `Claude-QT` engine will be removed from this diff
manager, as all of its functionality is now subsumed by
`view-review-tabs`.

## Supported Viewers

This system currently supports the following side-by-side diff viewers,
selectable from the <code>Viewer</code> menu.

- Claude-QT (Claude-generated, experimental, pyqt6)
- Emacs
- Meld
- TkDiff
- Vim

If any of Emacs, Meld, TkDiff or Vim cannot be found in commonly-used
install paths for that program, it will not be included in the
<code>Viewer</code> menu.


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
  uncommitted content.

- **Committed Changes**

  If revision information (-c) is provided, `diff-review` will produce
  a review for all the files changed in the specified revision.

# Usage

1. Clone this repository to any location on the computer.  For
   purposes of this text, we shall assume it has been placed at `~/diff-review`.


2. On POSIX-like systems, load the `aliases` file.

   This alias file is for Bash users.  Those using some other
   incompatible shell will have to provide their own translation.  Any
   submissions will be gladly accepted.

   `source ~/diff-review/scripts.d/aliases`

   This will provide three aliases in your current shell environment:
   `dr`, `vr` and `vrt`.  These directly reference the `diff-review`,
   `view-review`, and `view-review-tabs` programs respectively,
   bypassing the need to update `${PATH}`.

   The examples below will use these aliases.

   On Windows cmd.exe, replace 'dr' with a a full path to
   'diff-review.cmd', and 'view-review-tabs.cmd', which both reside in
   the root directory of the repository.

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
Viewer :  vrt --diff-dir '/home/thutt/review/default'
Viewer :  vrt --diff-url https://<fqdn>:443/home/thutt/review/default
Viewer :  vr -R '/home/thutt/review' -r 'default'
Elapsed:  0:00:00.094165
```

The lines beginning with `Viewer` are commands that can be executed
to view the diffs.

```
vr
```

Pressing `Esc` from both `vrt` and `vr` will  quit.


## Combine and view multiple changes

  The following command will generate diffs for a sequential range of
  emacs commits.

```
dr -c 4418a37c5df^..cb17a8bbf39
```

That command will produce the following output on the console, which
can be directly viewed by executing `vrt` or  `vr`:

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
Viewer :  vrt --diff-dir '/home/thutt/review/default'
Viewer :  vrt --diff-url https://<fqdn>:443/home/thutt/review/default
Viewer :  vr -R '/home/thutt/review' -r 'default'
Elapsed:  0:00:00.397989
```

## View uncommitted changes

This example will show how untracked, unstaged and staged changes are
processed.

Execute the following:

```
touch untracked;
cat README README >readme;
mv readme README;
git rm config.bat;
```

Now, run `dr`, which will produce the console output:

```
diff-review:  /home/thutt/review/default

   unstaged   README
     delete   config.bat
  untracked   untracked

Changes:  unstaged [1 files, 130 lines]  staged [1 files  385 lines]
Viewer :  vrt --diff-dir '/home/thutt/review/default'
Viewer :  vrt --diff-url https://<fqdn>:443/home/thutt/review/default
Viewer :  vr -R '/home/thutt/review' -r 'default'
Elapsed:  0:00:00.190448
```

As ever, both `vrt` and `vr` can be used to view the changes.

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

Changes:  unstaged [0 files, 0 lines]  staged [2 files  515 lines]
Viewer :  vrt --diff-dir '/home/thutt/review/default'
Viewer :  vrt --diff-url https://<fqdn>:443/home/thutt/review/default
Viewer :  vr -R '/home/thutt/review' -r 'default'
Elapsed:  0:00:00.191670
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

Changes:  unstaged [1 files, 274 lines]  staged [2 files  515 lines]
Viewer :  vrt --diff-dir '/home/thutt/review/default'
Viewer :  vrt --diff-url https://<fqdn>:443/home/thutt/review/default
Viewer :  vr -R '/home/thutt/review' -r 'default'
Elapsed:  0:00:00.190435
```

## Clean up repository

Now that the examples are finished, you can delete the `emacs` clone.

# Advanced Usage

Invoking either `dr` or `vr` with `--help` will show the current set
options that the program takes.  Using these options will allow more
complex invocations -- such as naming the output, or putting it into a
different directory location.

- Claude-QT (pyqt6)

  This viewer program was entirely generated through conversations
  with Claude.ai.  When it is deemed to be working well-enough, it
  will likely become the default viewer, replacing TkDiff.

  The Help menu describes how to use the features of the program.
