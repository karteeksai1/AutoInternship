# Tailoring an Overleaf (LaTeX) resume

The master is under `resume/` in the job-search folder (Overleaf: Menu → Download → Source, unzipped). Never edit it. Tailor and build a copy in scratch space; only after it passes the checks, copy the PDF and the tailored source (as `resume-src/`) into the job folder.

## Find the main file

The .tex file with `\documentclass`. If several have it, prefer `main.tex`, then one named like a resume. Files pulled in with `\input` or `\include` are part of the resume; edit them in the copy too.

## Edit only the words

Templates define their own commands in the preamble (before `\begin{document}`), such as `\resumeItem{...}`, `\resumeSubheading{title}{dates}{organization}{location}` or `\resumeProjectHeading{...}{date}`.

- Never type LaTeX into a shell command, heredoc or script: write it with `write_file` (new files) or `edit_file` (changes). Commands that only copy, cut or join existing files (`cp`, `head`, `cat`) are fine.
- Leave the preamble and every `\newcommand` definition alone, except the spacing numbers you may adjust when squeezing (tailoring.md), and: if it compiles with pdflatex and lacks `\input{glyphtounicode}` and `\pdfgentounicode=1`, add both to the copy.
- Change only the text inside the template commands' arguments and plain body text.
- Reorder by moving whole items (one `\resumeItem{...}` line, or a heading with its item list). Trim by deleting whole items. Keep every `{` matched with its `}`.
- Keep the master's conventions: date style (`Jan 2026 -- Present`), separators (`$|$`), capitalization, bold and italics.
- Lines starting with `%` are comments. You may uncomment an old bullet if it fits this internship better.

## Escape special characters in anything you write

| Write | As | Example |
|---|---|---|
| & | `\&` | R\&D |
| % | `\%` | cut load time 40\% |
| $ | `\$` | \$5K budget |
| # | `\#` | C\# |
| _ | `\_` | snake\_case |
| { } | `\{ \}` | |
| ~ | `\textasciitilde{}` | |
| ^ | `\textasciicircum{}` | |

An unescaped `%` comments out the rest of the line, including the closing brace. `C++`, `/`, `-` and `.` are fine. Copy the master's quotes and dashes.

## Build and check

`check_tailored.py` builds the copy with `build_resume.py`. Add `--expect` with one or two phrases you just added. Exit codes:

- **0 or 2, built.** Lines past the margin: shorten the new line. `fix` saying expected text isn't readable: for pdflatex, make sure the copy's preamble has `\input{glyphtounicode}` and `\pdfgentounicode=1`. Margins too tight or text below 9pt: undo the last squeeze.
- **2 with `lines_over`, too long**: trim ("Trimming to one page" in tailoring.md), or squeeze when only a few lines are over and the next cut is a strong match. Run again.
- **Space at the bottom** (empty lines under `review`): add lines ("Filling the page" in tailoring.md) and run again. Leave the space only when nothing else fits, and say so in changes.md.
- **1, compile error**: read `errors`, `suspect_lines` and `hints`; it's almost always a special character or brace in your text. Fix and run again. After three failed tries, undo your last round of edits, build that, and tell the user what you couldn't change.
- **3, no LaTeX here**: handle what the bullet comparison and fact-check flagged, save the copy to the job folder as `resume-src/`, and tell the user to compile it in Overleaf (zip resume-src and use New Project → Upload Project, or paste the changed lines into a copy of their project). Keep filling the application, leave the resume upload for the user, and log the row as `Needs you` with next step "compile resume in Overleaf, then attach".

A missing package or font that isn't in the project folder (such as fontawesome5) counts as exit 3.

## Keeping a copy in Overleaf

Not needed: the PDF and source are in the job folder. To redo a saved build, rebuild in scratch and save again, moving the saved PDF and resume-src/ into `_old/` first. To get the tailored version into Overleaf, zip resume-src and use New Project → Upload Project.
