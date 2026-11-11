# Interview prep

Prepare the user to walk in knowing what the company has seen from them, with true stories for the likely questions.

## Read first

1. The job folder: `job-posting.md`, `application-record.md` (including changes before submitting and the timeline), `changes.md`, the resume PDF sent (or `resume-src/`), and any cover letter.
2. The master resume and profile.json, for facts the tailored version left out.
3. What the user said about the interview: date, time and time zone, format (phone, video, on-site), who they'll meet, and the round (recruiter screen, technical, behavioral, final). If the round is unknown, write for a mix and say so at the top.
4. With web search, a quick look at the company and team (what they make, one or two recent news items), with links. Without it, skip this; don't guess.

## Rules

- **No invented facts.** Stories, numbers, tools and outcomes come only from the resume sent, the master, the profile or the application record. Where an answer needs a detail only the user knows, write `[Fill in: ...]`.
- Show the user's written answers word for word, so they stay consistent with them.
- Every line on the resume sent needs something ready behind it.
- Keep the document readable in about 15 minutes.

## Before saving

Draft in scratch space, then fact-check, allowing the company, role and interviewer names:

```
python scripts/check_resume.py "<master resume>" "<scratch>/interview-prep.md" --known "<folder>/profile.json" --known "<job folder>/application-record.md" --allow "<Company>" --allow "<Role>" --allow "<Interviewer>"
```

Company research brings new names and numbers; that's expected. Check every flag in the stories and intro sections, and remove anything that isn't the user's real experience. Save `interview-prep.md` in the job folder, moving an older one into `_old/` first.

## Document layout

```
# Interview prep: Role at Company

**Interview:** <date, time and time zone>, <format>, with <whom>, <round>

## The role in brief
3 to 5 bullets: what the team does, what the intern will work on, the posting's main requirements.

## The company in brief
2 to 4 bullets, with links for anything from the web.

## What they've seen from you
- Resume sent: <file name>. The lines most likely to come up: <3 to 5 bullets that match the posting best>.
- Your written answers: <each question, then the answer word for word>.
- Cover letter: <its main points, or "none">.

## Your 30-second introduction
A short paragraph in the user's voice: year and school, major, one or two relevant experiences or projects, and why this internship. Facts only.

## Your stories
4 to 6 stories, each for a question theme the posting or the round suggests. Common internship themes: a project you're proud of, working on a team or with a disagreement, a challenge or mistake, learning something quickly, why this company.

### <Theme>: <the real project, job or activity it uses>
- **Situation and task:** ...
- **What you did:** ... (the user's own part of group work)
- **Result:** ... (from the resume, or [Fill in: ...])
- **If they dig deeper:** [Fill in: the hardest part, what you'd do differently]

## Project deep dives
For each project on the resume sent: what it does, the user's part, the tools and why they were chosen (or [Fill in: why]), one hard problem, and what they'd improve next.

## Technical topics to review
From the posting's requirements and the tools on the resume sent, list concrete subtopics with one way to practice each. For example: SQL → joins, GROUP BY, window functions; practice by writing three queries against a sample dataset. For coding rounds, say so plainly: data structures and easy-to-medium practice problems in the language they list first.

## Gaps and honest answers
For each gap in changes.md that the interviewer might raise: a truthful answer that names the closest real experience and shows willingness to learn. Never claim the missing skill.

## Questions to ask them
4 to 6 questions specific to this team and role (what an intern's first project usually is, how success is measured, how the team works), not ones the posting already answers.

## Before and after
- Check the time zone, the link or address, and have the resume sent open.
- Within 24 hours after: a short thank-you note. Offer to draft it, using one specific thing from the conversation.
```

Afterwards, tell the user where it is, how many `[Fill in: ...]` spots need their input, and offer a short practice interview in chat.
