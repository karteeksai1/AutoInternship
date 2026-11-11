# AutoInternship for Antigravity

An Antigravity plugin (two skills + safety rules) and a Chrome extension for internship applications. They find postings, tailor a one-page resume to each one, fill the form, and track every application. By default you review and click submit yourself. You can also ask Antigravity to fill everything (consent boxes and signature included), or to submit for you.

| Part | What it does |
|---|---|
| [`.agents/plugins/autointernship`](.agents/plugins/autointernship/) | The Antigravity plugin (`plugin.json`, `rules/AGENTS.md`, and two skills below). Automatically discovered when you open this workspace in Antigravity. |
| [`internship-application`](.agents/plugins/autointernship/skills/internship-application/) | Finds internships from the [SimplifyJobs list](https://github.com/SimplifyJobs/Summer2027-Internships), tailors and fact-checks your resume (Overleaf or Word), writes a cover letter wherever the form has a place for one, fills the application, and records what it entered. |
| [`internship-tracker`](.agents/plugins/autointernship/skills/internship-tracker/) | Keeps `tracker.xlsx` up to date with statuses, follow-ups, and interview prep. |
| [`autointernship`](autointernship/) | The AutoInternship Chrome extension. Fills the predictable fields (name, contact details, school, links, yes-or-no questions, dropdowns, self-identification answers you chose) from your saved profile, instantly and without using agent tokens. Antigravity finishes the rest. |

It submits only when you ask it to, and never uses LinkedIn, never types passwords, never adds anything to your resume that isn't in your master copy, and never deletes files.

## What you need

- **Google Antigravity** (Antigravity 2.0, Antigravity IDE, or the `agy` CLI).
- **Google Chrome** and an Antigravity browser integration:
  - Install the **Chrome DevTools** plugin (`antigravity-plugins-official/plugin/chrome-devtools-plugin`) from the Antigravity Marketplace so Antigravity can drive Google Chrome with the AutoInternship extension loaded, or use Antigravity's built-in `/browser` mode.
- **Python 3** with `pip install openpyxl pypdf` (plus `python-docx` if your master resume is `.docx`).
- Optional: [Tectonic](https://tectonic-typesetting.github.io/) (or `pdflatex`) so Antigravity can compile Overleaf resumes locally, and Poppler (`pdftoppm`) or `pdfplumber` for PDF layout checks. Without LaTeX installed, you compile resumes in Overleaf.
- Your master resume, in Overleaf (`.tex` source) or as a Word (`.docx`) file.

## Install

1. **Get this project.** Clone or download this repository.
2. **Load the Antigravity plugin.**
   - **Using this folder directly:** Open this repository as your workspace in Antigravity. `.agents/plugins/autointernship/` is discovered and enabled automatically (personal job-search files like `resume/`, `Applications/`, `jobs.txt`, `tracker.xlsx`, and `profile.json` are already in `.gitignore`).
   - **Using a separate job-search folder:** Copy `.agents/plugins/autointernship` into `~/.gemini/config/plugins/autointernship` so the plugin is available globally across all workspaces.
3. **Add the AutoInternship Chrome extension.** Install it from the [Chrome Web Store](https://chromewebstore.google.com/detail/autointernship/cdfkbdkmandhnmaejaknimdhepipbpin), or load [`autointernship/`](autointernship/) unpacked in `chrome://extensions` with **Developer mode** enabled. Fill in its profile page once (see [its README](autointernship/README.md)).
4. **Enable browser automation.** In Antigravity, add the **Chrome DevTools** plugin from the Marketplace (recommended so Antigravity can click **Fill with AutoInternship** inside Chrome) or turn on `/browser`.

## Start applying

1. In your job-search folder (either this repo or a separate folder if you installed the plugin globally), create a folder named `resume/` and put your master resume inside: either your Overleaf project downloaded as **Source** (unzipped) or your Word `.docx`.
2. Optional: add `profile.json` (use **Download backup** on the extension's profile page) and `jobs.txt` (posting links, one per line). Without `profile.json`, Antigravity creates it and asks only what your resume doesn't say.
3. Open your job-search folder in Antigravity and ask it to apply (see [Your first batch](#your-first-batch)).

In a batch, Antigravity launches parallel subagents (`invoke_subagent`) to tailor all the resumes and fill the forms at the same time (using your selected model for tailoring and `flash` for form-filling). It applies to at most two roles per company in 5 days, so recruiters don't see a flood of applications from you; the rest wait in `jobs.txt`.

Antigravity adds `Applications/` (one folder per application) and `tracker.xlsx` to your folder.

## Your first batch

Select your preferred Gemini model (e.g., **Gemini Pro** or **Gemini Flash**) and ask:

> Apply to 6 jobs fill all

Antigravity tailors a resume for each of the next 6 postings in `jobs.txt`, fills every form, and stops before Submit. You check each one and submit it.

Other requests: `"Apply to 6 jobs"` (leaves agreement boxes to you), `"Apply to 6 jobs and submit"`, `"Find data internships in CA"`, `"Where do my internship applications stand?"`.

## Sandbox & network access

Antigravity's terminal sandbox blocks outbound network access by default. When running `find_internships.py` or `fetch_posting.py`, Antigravity will request permission to run outside the sandbox (`BypassSandbox: true`), or you can configure Antigravity's **Internet Access Policy** in Settings. If network requests remain blocked in the terminal, Antigravity falls back to reading postings in the browser.

## Star history

<a href="https://github.com/pqthangv/AutoInternshipClaude/stargazers">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pqthangv/AutoInternshipClaude/star-chart-images/stars-dark.svg">
    <img alt="Star history chart" src="https://raw.githubusercontent.com/pqthangv/AutoInternshipClaude/star-chart-images/stars.svg">
  </picture>
</a>

## License

[MIT](LICENSE). This is a personal project, not affiliated with or endorsed by Google or Anthropic.
