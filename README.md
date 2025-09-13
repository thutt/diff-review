Change is omnipresent in the software industry.  Understanding that
change provides a big-picture view of a whole project, but there are
scant few tools that afford the ability to see a change, side-by-side
with the previous version of the file.

That is a particularly acute issue if viewing a change from the past
is desired.  Sure, it's possible to use the SCM to view patches to a
single file, but that's a terribly awful way to look at changes
because all context is lost.

Some SCMs can do this.  But none of them very well.

For git, this tool will create viewable diffs for untracked, unstaged,
staged and committed files via a simple runtime interface.

To generate the diffs for a change in this repository, select the
change and execute:

    diff-review  -r review-name -c 66ff4bb

This produces the following on the console:

    diff-review:  /home/thutt/review/review-name

      modify   scripts.d/dr.d/drgit.py
      modify   scripts.d/dr.d/drutil.py

    Changes:  committed [2 files, 274 lines]
    TkDiff :  view-review --viewer tkdiff -r review-name
    Meld   :  view-review --viewer meld -r review-name

To view the diffs, execute the command to launch your favorite viewer.
This will bring up a menu showing the files included in the change.
Select a file from the menu to view the diffs.

If you are working on a project and want to view the current state of
the files, use:

    diff-review -r review-name

This will do the same thing for untracked, unstaged and staged files
in your source tree.  Notice how it shows the changes to stated, and
unstaged files.  In this example, drgit.py is both staged and
unstaged.

    diff-review -r review-name

    diff-review:  /home/thutt/review/gungla

      unstaged   scripts.d/dr.d/drgit.py

    Changes:  unstaged [1 files, 1 lines]  staged [1 files  1 lines]
    TkDiff :  view-review -R /home/thutt/review --viewer tkdiff -r gungla
    Meld   :  view-review -R /home/thutt/review --viewer meld -r gungla

Or, if you want to view a range of changes, you can provide the
appropriate Git command, like this.

    diff-review -r review-name -c 8f7b0b4..b9d15fb

By default, the reviews are written into ~/reviews, and that entire
directory structure can be removed at any time.
