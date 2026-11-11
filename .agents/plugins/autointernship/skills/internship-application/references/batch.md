# Batch runs: one subagent per posting

Read this when the user asks to work through `jobs.txt` or gives several links.

Use Antigravity's `invoke_subagent` (`TypeName: "self"` so subagents inherit all workspace and MCP tools, or `swarm` when running a coordinated parallel batch). Without subagent or browser access in subagents, follow "Without subagents" at the end.

- **Keep this conversation small.** Never fill forms or read form pages here. Your only browser work is in Submit mode when clicking Submit.
- **Models.** Launch tailoring subagents with `Model: "inherit"` (default), and launch form-filling subagents with `Model: "flash"` for faster, lower-cost execution (steps 4 and 6).
- **Reactive wakeup (no polling).** `invoke_subagent` runs asynchronously in the background and automatically notifies you when a subagent completes or messages back. Launch independent subagents in parallel and stop calling tools to wait for their replies.

## The run

1. **Tidy, fetch and screen the queue**, one call each (`SKILL.md`, "Batch runs"). Skip postings the tracker already has. Never start a subagent for a posting the screen marks `skip`: the fetch has moved it below `# done` with its reason (for links the user gave instead of `jobs.txt`, log it as `Skipped`). For a `check`, decide from its `screen_why` lines by `SKILL.md` step 2, here, and log a skip as `Skipped` with the reason. When too few are left, fetch again with a larger `--limit`. Order the rest by deadline, soonest first, then those with no deadline, newest first.

   **At most two per company.** For each company, count its postings in this batch plus its tracker rows from the last 5 days (`in_tracker`, by `date_added`; `Skipped` rows don't count). Keep at most two: the titles that fit the user best (major, skills, the kind of role they asked for), the earlier deadline on a tie. For a posting the fetch couldn't read, take the company from its `jobs.txt` note or link. Leave the rest in `jobs.txt` above `# done`, adding `held: 2 per company` to the line's note if it isn't there yet. If the user asks for more from one company ("all the Northwind roles"), use their number.

2. **Tailor**: launch one subagent per posting (`TypeName: "self"`, `Model: "inherit"`, `Workspace: "inherit"`) with the tailoring prompt. Start the first one alone (`--check-template` on this one only) and all the rest once it starts or in parallel, then wait for all replies. Postings the fetch couldn't get are read in the browser, so follow "Sharing the browser" for those. Don't read `tailoring.md`, `overleaf.md`, or the master yourself.

3. **Checkpoint** (step 4) from the summaries, one short block per posting. Read a drafts file only to show its answers, and not at all in auto mode. Add one line for postings held by the company limit (company: roles), so the user can swap one in or say to do them all; in auto mode they stay held.

4. **Fill**: launch one subagent per application (`TypeName: "self"`, `Model: "flash"`, `Workspace: "inherit"`) with the filling prompt, all non-conflicting ones at once, following "Sharing the browser". Queue any second application on the same company/Workday account until the first replies. If they reply `NO BROWSER`, fill them all yourself, as in "Without subagents".

5. **Hand-off**: one message for the whole batch: one line per tab (company and role, and what's needed: "sign in to Workday", "attach `C:\...\Maya_Chen_Resume_Northwind.pdf`"), then the questions from every form, grouped so one answer covers every form that asks it. Before sending, check each question against `profile.json` yourself (every field and `savedAnswers`, by meaning); send the ones it answers straight back to their subagents (step 6 via `send_message` or a follow-up `invoke_subagent`) instead of asking. In Submit mode without auto, also show the written answers the subagents drafted on the form (each record's "Written answers"); send this message even when nothing else needs the user, and wait.

6. **Continue**: when the user is done, message each paused filling subagent with `send_message` (or re-invoke `invoke_subagent` with the filling prompt if the subagent already finished its turn) with what the user did and their answers. Each continues from its `application-record.md` in the same tab. Repeat once if new steps came up.

7. **Submit** (Submit mode only): do it yourself, never in a subagent. For each application whose check passed (or failed only on check 3, written answers, which the user has since seen and accepted), switch to its tab, confirm it's on the review page, and follow "Submitting" in `submitting.md`.

8. **Report** once, one line per posting (step 8). Move processed links in `jobs.txt` below `# done`, editing in place. Held postings get one line together at the end ("Held, 2 per company: ...") and stay above `# done`. Postings the screen skipped get one line too ("Skipped by the screen: Company Role (reason), ..."). Save the answers listed under `To save:` to `profile.json` without asking (`references/profile.md`) and say in one line what you saved. If `profile.json` changed in this batch, or any reply's `Extension answers:` is lower than its number of `savedAnswers`, add: "In the AutoInternship extension, open the profile page, click **Restore from backup** and choose `<folder>/profile.json`, so the Fill button uses the new answers." End with one line telling the user to start a new conversation for the next batch.

A posting with a wall the user can't clear in the hand-off (a broken page, a closed posting, an assessment) is `Needs you`; move on.

## Sharing the browser

- **Confirm browser tools exist first.** Make sure Antigravity's browser tools or an active Chrome MCP plugin (such as `chrome-devtools-plugin`) are available before launching filling subagents.
- **No limit on how many at once**, except the queueing below. If the user asks for a limit, use their number.
- **One at a time per sign-in.** Never run two forms at once on the same account: two on one Workday site (such as `northwind.wd5.myworkdayjobs.com`) or two on one company's careers site. Queue the second behind the first. Greenhouse, Lever and Ashby forms for different companies can run at the same time.
- **If they get in each other's way** (two subagents report failing clicks, cross-tab interference, or a missing tab), let the running ones finish, then fill the rest one at a time.
- **If a tab or browser session resets**, each affected subagent stops with `stopped: browser session reset` and returns its progress. Re-launch it with the third kind of `Tab:` line so it opens a new tab and continues from `application-record.md` without starting over.

## Tailoring prompt

Fill in the `<...>` parts and pass this as `Prompt` to `invoke_subagent`:

```
You're tailoring one internship application in a batch run by the internship-application skill.
With read_file (not cat), read <skill>/SKILL.md, the posting and the profile first, and do SKILL.md
steps 1 and 2 for this posting only (the tracker check is already done): create the job folder, save job-posting.md,
check eligibility. If it's a skip, reply now. Otherwise read <skill>/references/tailoring.md (and references/overleaf.md
if the master is .tex) and the master, then do step 3: tailor, check and save the resume, write changes.md, write the
cover letter when tailoring.md's "Cover letter" says (optional fields included), and draft any written answers into
<scratch>/answers/<NN>.md. Read each file once.
Don't open the application form, don't change the tracker, and don't start subagents of your own.
Work only from the master resume: never open resumes, resume-src or changes.md in other job folders.
For a .tex master, never type LaTeX into a shell command, heredoc or script: use write_file and edit_file (copying files with cp, head or cat is fine).
- Posting: <fetched file> | <link: open it in a new tab of your own, read it, close that tab; pass its tab/page id on every browser action and leave other tabs alone>
- Job-search folder: <folder>  Master resume: <path>  Profile: <folder>/profile.json
- Scratch space: <scratch>/<NN>   Today: <YYYY-MM-DD>
- Master template check: <add --check-template | already done, leave it out>
Reply with only these lines:
Posting: <Company> - <Role>, deadline <date or none>
Eligibility: ok | skip: <reason>
Folder: <job folder>
Resume: <PDF file name>; page <filled, or N lines free and why>
Changes: <two or three short lines>
Gaps: <one line>
Cover letter: <file name (and the combined PDF's), or none: the Cover letter line's value>
Answers: <drafts file, or none>
Problems: <none, or what needs the user>
```

Log a `skip` as `Skipped` with its reason (in auto mode) or show it at the checkpoint. Give `--check-template` only to the first tailoring subagent.

## Filling prompt

Fill in the `<...>` parts and pass this as `Prompt` to `invoke_subagent` (`Model: "flash"`):

```
You're filling one internship application in a batch run by the internship-application skill.
Read <skill>/references/filling.md (and references/submitting.md unless the mode is Review) with read_file,
not cat. Read each file once. You don't need SKILL.md.
Mode: <Review | Fill all | Submit>. Never click Submit in any mode: in Submit mode, fill as in Fill all,
then run "The check before Submit" from submitting.md on the review page and report the result.
iCIMS has no review page, and every step button says Submit. It only saves the step, except on the last
step still to do: the current step once every other one is completed (a green check on its circle;
"(Completed Step)" in the page text), whatever its number. That step's heading counts its forms
("Portal Specific Forms (1/3)"): click Submit on each form before the final one, then fill the final one
(3/3) and stop without clicking Submit. With no count, treat the form on screen as the final one.
In Review mode, stop when that last step opens.
Don't leave the step that takes the resume until it shows the tailored PDF's file name; if you can't attach
it there (on iCIMS, Replace Resume shows the file box), stop on that step and hand it over.
Attach or paste the cover letter wherever the form takes one, optional fields included (filling.md, "Cover letter").
The user <saw | didn't see (auto)> the drafted answers.
For this application only: fill the form in the user's browser up to the review page or the first thing
that needs the user, add each page's fields to application-record.md as you go, and log the tracker row
(filling.md, "Logging the tracker row"; run scripts from <skill>). Don't start subagents of your own.
Fill everything you can. Before you list a question, check profile.json (every field and savedAnswers, by meaning):
list only what nothing there, in the master resume or in the posting answers. Don't edit profile.json; put new
answers under To save.
Browser work (filling.md has the rest): find fields via DOM/accessibility snapshots and click or scroll them
by element handle/selector/UID, never by raw screen coordinates. At most one screenshot per page, on its own.
- Job folder: <folder>  Application link: <url; an icims.com link with in_iframe=1 added>  Resume: <PDF path>  Answers: <drafts file, or none>
- Cover letter: <letter path and cover-letter.txt path (and the combined PDF's), or none>  Master resume: <path>
- Profile: <folder>/profile.json  Tracker: <folder>/tracker.xlsx
- Tab: <open a new tab of your own | continue in tab <id>: the user has since <what they did>, and answered: <answers>
  | open a new tab of your own and continue from application-record.md: the browser session reset>
If you have no browser automation or Chrome MCP tools available, stop immediately and reply only "NO BROWSER".
Other subagents may be filling forms in other tabs of this browser. Always target only your own tab/page id,
and never switch to, close, or use any other tab. If your tab is gone but the browser is still up, open a new
tab and continue from application-record.md. If the browser session itself is gone, stop and reply with
Status: stopped: browser session reset.
Reply with only these lines:
Status: review page | needs the user | stopped: browser session reset | stopped: <why>
Tab: <id> <url>
For the user: <one line, or none>
Questions: <each question word for word, with its choices, or none>
Written answers: <none, or "in application-record.md" for ones you drafted on the form>
Agreed for you: <short list, or none>
To save: <answers the user gave that will come up again, for profile.json, or none>
Extension answers: <N from "Profile: N saved answers." in the Fill report, or none>
Submit check: <passed | failed: which> (Submit mode only)
```

## Without subagents

Do the same run here: tailor everything first (steps 1 to 3 for each posting), one combined checkpoint, fill each application in its own tab up to where it needs the user, one hand-off for the batch, continue each form when the user is done, record and log each, and report once.
