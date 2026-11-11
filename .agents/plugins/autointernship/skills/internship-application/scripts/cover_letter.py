#!/usr/bin/env python3
"""Turn a cover letter written as plain text into a one-page PDF, and check it.

Usage:
  python cover_letter.py LETTER.txt --profile profile.json --master MASTER --company "Northwind" --role "Data Analyst Intern"
         --out NAME_Cover_Letter_Company.pdf [--posting job-posting.md] [--combine RESUME.pdf] [--max-words 250]

LETTER.txt is the letter itself, from the greeting ("Dear Northwind hiring team,") to the sign-off ("Sincerely,"
and the name on the next line). Paragraphs are separated by a blank line; a single line break stays a line break.
The same text is what gets pasted into a form's cover-letter text box, so it carries no header.

What it does:
  1. Writes a LaTeX letter: the name and contact line from profile.json, today's date and the company, then the
     text. It's built with build_resume.py, so it compiles wherever the resume does (pdflatex, XeLaTeX or Tectonic,
     whose f-ligatures build_resume breaks up so the PDF's text stays searchable).
  2. Checks the result: one page, the word limit, no placeholders, the company named, the PDF text readable, and
     every number and tool-like term found in the master resume or profile (check_resume.py). Terms the posting
     has but the master doesn't are listed apart: fine for naming the company's work, never as the user's skill.
  3. --combine RESUME.pdf also writes NAME_Resume_and_Cover_Letter_Company.pdf beside --out, resume first, for a
     form whose only upload box has to take both.

Why a script: the first letters were hand-written LaTeX, three or four calls each, and one of them came out with
"ﬁ" ligature characters in its text. The text-to-PDF step is the same every time; only the words need Antigravity.

Prints one JSON object: "fix" (change before saving), "review" (look at each one), the word count and the paths.
Exit codes: 0 nothing to fix or review, 2 something under fix or review, 1 bad input or compile error,
3 no LaTeX here (the text checks still ran; make the PDF another way).
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']

# The letter is typeset in plain T1 Latin Modern, which pdflatex and XeTeX (Tectonic) both handle the same way
# only when the source is ASCII, so every other character becomes a LaTeX command here.
SPECIAL = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
           '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}', '<': r'\textless{}', '>': r'\textgreater{}',
           '|': r'\textbar{}', '"': r'\textquotedbl{}'}
UNICODE = {'–': '--', '—': '---', '‘': '`', '’': "'", '“': '``', '”': "''",
           '…': r'\ldots{}', '•': r'\textbullet{}', ' ': '~', '£': r'\pounds{}',
           '€': r'\texteuro{}', '°': r'\textdegree{}', '×': r'$\times$', '→': r'$\rightarrow$',
           'ß': r'\ss{}', 'æ': r'\ae{}', 'Æ': r'\AE{}', 'ø': r'\o{}', 'Ø': r'\O{}',
           'ł': r'\l{}', 'Ł': r'\L{}', '‐': '-', '‑': '-'}
# One accent on a letter ("é") is a single glyph in T1 fonts and reads back as text. Stacked accents ("ễ") and
# "Đ" don't: they came back from the PDF as "Nguy ˜ên" and "Ðà", which a tracking system can't match. Those
# letters are written without their marks in the PDF, and the report lists them.
ACCENTS = {'́': "\\'", '̀': '\\`', '̂': '\\^', '̃': '\\~', '̈': '\\"', '̧': '\\c',
           '̌': '\\v', '̊': '\\r', '̄': '\\=', '̆': '\\u', '̇': '\\.', '̨': '\\k',
           '̋': '\\H'}
PLAIN = {'đ': 'd', 'Đ': 'D'}


def tex_escape(text, notes):
    """ASCII LaTeX for the text. notes['plain'] collects letters written without their marks, notes['unsupported']
    characters left out."""
    out = []
    for ch in text:
        if ch in SPECIAL:
            out.append(SPECIAL[ch])
        elif ord(ch) < 128:
            out.append(ch)
        elif ch in UNICODE:
            out.append(UNICODE[ch])
        elif ch in PLAIN:
            out.append(PLAIN[ch])
            notes['plain'].add(ch)
        else:
            base, *marks = unicodedata.normalize('NFD', ch)
            if ord(base) >= 128 or not marks or not all(unicodedata.combining(m) for m in marks):
                notes['unsupported'].add(ch)
            elif len(marks) == 1 and marks[0] in ACCENTS:
                out.append(ACCENTS[marks[0]] + '{' + base + '}')
            else:
                out.append(base)
                notes['plain'].add(ch)
    return ''.join(out)


def header_lines(prof):
    name = ' '.join(x for x in (str(prof.get('firstName') or '').strip(), str(prof.get('lastName') or '').strip()) if x)
    place = ', '.join(x for x in (str(prof.get('city') or '').strip(), str(prof.get('state') or '').strip()) if x)
    links = [re.sub(r'^(https?://)?(www\.)?', '', str(prof.get(k) or '').strip()).rstrip('/')
             for k in ('linkedin', 'github', 'portfolio', 'website')]
    phone = str(prof.get('phone') or '').strip()
    digits = re.sub(r'\D', '', phone)
    us = flat(prof.get('country')).strip() in ('', 'us', 'usa', 'united states', 'united states of america')
    if us and (re.fullmatch(r'1?\d{10}', digits) and not phone.startswith('+') or phone.startswith('+1') and len(digits) == 11):
        phone = f'({digits[-10:-7]}) {digits[-7:-4]}-{digits[-4:]}'  # profiles often keep bare digits ("5550102030")
    contact = [str(prof.get('email') or '').strip(), phone, place]
    # Links get a line of their own: on one line with the rest, the contact line wrapped mid-list.
    return name, [c for c in contact if c], [l for l in links if l]


def letter_tex(prof, company, text, notes):
    name, contact, links = header_lines(prof)
    lines = [' \\textbar{} '.join(tex_escape(c, notes) for c in part) for part in (contact, links) if part]
    today = dt.date.today()
    paras = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    body = '\n\n'.join(r'\\'.join(tex_escape(l.strip(), notes) for l in p.splitlines() if l.strip()) for p in paras)
    return '\n'.join([
        r'\documentclass[11pt,letterpaper]{article}',
        r'\usepackage[margin=1in]{geometry}',
        r'\usepackage[T1]{fontenc}',
        r'\usepackage{lmodern}',
        r'\input{glyphtounicode}',  # pdflatex: real text in the PDF for tracking systems; build_resume guards these under Tectonic
        r'\pdfgentounicode=1',
        r'\setlength{\parindent}{0pt}',
        r'\setlength{\parskip}{0.9em}',
        r'\pagestyle{empty}',
        # No hyphenation: a word split across lines ("com-munity") reads back from the PDF as two words.
        r'\raggedright\hyphenpenalty=10000\exhyphenpenalty=10000',
        r'\begin{document}',
        r'{\Large\bfseries ' + tex_escape(name, notes) + r'}\\[2pt]',
        '\\\\\n'.join(lines),
        '',
        r'\vspace{0.6em}',
        f'{MONTHS[today.month - 1]} {today.day}, {today.year}',
        '',
        tex_escape(company, notes),
        '',
        body,
        r'\end{document}',
        ''])


def run_script(name, *args):
    """Run one of the scripts beside this one and return (exit code, its JSON result)."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, os.path.join(HERE, name), *args], capture_output=True,
                       encoding='utf-8', errors='replace', env=env)
    try:
        return r.returncode, json.loads(r.stdout)
    except json.JSONDecodeError:
        return 1, {'ok': False, 'error': f'{name} gave no result: {(r.stderr or r.stdout).strip()[-400:]}'}


def flat(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower().replace('’', "'")
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s).strip() + ' '


def company_named(company, text):
    """The full name, or the name without a leading "The" and a company suffix ("Northwind" for "Northwind Inc.")."""
    words = flat(company).split()
    short = [w for w in words if w not in ('the', 'inc', 'llc', 'ltd', 'corp', 'corporation', 'co', 'plc', 'lp', 'llp')]
    return any(c and f' {" ".join(c)} ' in flat(text) for c in (words, short))


def role_words(role):
    """The words that make a title this role's: no seasons, years or "intern"."""
    role = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', role)
    stop = {'intern', 'interns', 'internship', 'summer', 'fall', 'spring', 'winter', 'the', 'and', 'for', 'of', 'with',
            'program', 'student', 'co', 'op', 'coop', 'undergraduate', 'graduate', 'campus', 'early', 'career'}
    return [w for w in flat(role).split() if len(w) > 2 and w not in stop and not w.isdigit()]


def pdf_text(pdf):
    try:
        from pypdf import PdfReader
        return '\n'.join((p.extract_text() or '') for p in PdfReader(pdf).pages)
    except Exception:
        pass
    if shutil.which('pdftotext'):
        return subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, errors='replace').stdout
    return None


def combine(resume, letter, out):
    """Resume pages first, then the letter. Returns an error message, or None."""
    try:
        from pypdf import PdfWriter
        w = PdfWriter()
        for f in (resume, letter):
            w.append(f)
        with open(out, 'wb') as fh:
            w.write(fh)
        return None
    except ImportError:
        pass
    if shutil.which('pdfunite'):
        r = subprocess.run(['pdfunite', resume, letter, out], capture_output=True, text=True, errors='replace')
        return None if r.returncode == 0 else f'pdfunite failed: {r.stderr.strip()[:200]}'
    return 'combining needs pypdf or pdfunite, and neither is here'


def move_old(path):
    """Like build_resume.py: a file already at the path goes into _old/ beside it, with the date and time."""
    if os.path.exists(path):
        old = os.path.join(os.path.dirname(path), '_old')
        os.makedirs(old, exist_ok=True)
        base, ext = os.path.splitext(os.path.basename(path))
        shutil.move(path, os.path.join(old, f"{base}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('letter')
    ap.add_argument('--profile', required=True)
    ap.add_argument('--master', required=True)
    ap.add_argument('--company', required=True)
    ap.add_argument('--role', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--posting')
    ap.add_argument('--combine', metavar='RESUME.pdf')
    ap.add_argument('--max-words', type=int, default=250)
    a = ap.parse_args()
    for p in [a.letter, a.profile, a.master] + [x for x in (a.posting, a.combine) if x]:
        if not os.path.isfile(p):
            print(json.dumps({'ok': False, 'error': f'not found: {p}'}))
            return 1
    try:
        prof = json.load(open(a.profile, encoding='utf-8-sig'))
    except ValueError as e:
        print(json.dumps({'ok': False, 'error': f"couldn't read the profile: {e}"}))
        return 1
    text = open(a.letter, encoding='utf-8-sig').read().replace('\r\n', '\n')
    fix, review = [], []

    words = len(re.findall(r"[A-Za-z0-9][\w'’.-]*", text))
    if words > a.max_words:
        fix.append(f'{words} words; keep it under {a.max_words}.')
    elif words < 120:
        review.append(f'Only {words} words: say why this company and team, with one or two pieces of evidence.')
    if not company_named(a.company, text):
        fix.append(f'The letter never names {a.company}.')
    rw = role_words(a.role)
    if rw and sum(f' {w} ' in flat(text) for w in rw) < max(1, len(rw) // 2):
        review.append(f'The letter doesn\'t name the role ("{a.role}").')

    # Facts: the same check as the resume's, with the company and role allowed. Terms that are only in the posting
    # are usually the company's own products or teams, which a letter may name but never claim as the user's skills.
    allow = ['--allow', a.company, '--allow', a.role]
    _, facts = run_script('check_resume.py', a.master, a.letter, '--known', a.profile, *allow)
    if facts.get('error'):
        review.append('Fact check did not run: ' + facts['error'])
    posting = flat(open(a.posting, encoding='utf-8', errors='replace').read()) if a.posting else ''
    from_posting = [t for t in facts.get('new_terms', []) if posting and flat(t).strip() and flat(t) in posting]
    unknown = [t for t in facts.get('new_terms', []) if t not in from_posting]
    if facts.get('placeholders'):
        fix.append('Placeholders left in: ' + ', '.join(facts['placeholders']))
    if facts.get('new_numbers'):
        review.append('Numbers not in the master or profile: ' + ', '.join(facts['new_numbers']) + '. Keep only real ones.')
    if unknown:
        review.append('Terms not in the master, profile or posting: ' + ', '.join(unknown) + '. Trace each to the master or remove it.')
    if from_posting:
        review.append('Terms from the posting, not the master: ' + ', '.join(from_posting)
                      + '. Fine when naming the company\'s work; never as the user\'s own skill.')

    notes = {'plain': set(), 'unsupported': set()}
    source = letter_tex(prof, a.company, text, notes)
    if notes['unsupported']:
        fix.append('Characters the PDF can\'t show: ' + ' '.join(sorted(notes['unsupported'])) + '. Write the letter without them.')
    if notes['plain']:
        marked = sorted({w for w in re.findall(r"[\w'’-]+", text) if any(c in w for c in notes['plain'])})
        review.append('Written without accent marks in the PDF, so tracking systems can read them: ' + ', '.join(marked)
                      + '. The text to paste keeps them.')

    name = header_lines(prof)[0]
    out = os.path.abspath(a.out)
    result = {'pdf': None, 'combined': None, 'words': words}
    build_dir = tempfile.mkdtemp(prefix='cover-letter-')  # system temp, outside the user's folders
    try:
        tex = os.path.join(build_dir, 'cover_letter.tex')
        with open(tex, 'w', encoding='utf-8', newline='\n') as f:
            f.write(source)
        code, built = run_script('build_resume.py', tex, '--out', out, '--max-pages', '1', *(['--expect', name] if name else []))
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    if code == 3:
        result.update({'ok': False, 'code': 'NO_LATEX', 'fix': fix, 'review': review,
                       'error': 'No LaTeX engine here, so no PDF was made. The text checks above still ran.'})
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return 3
    if code == 1:
        result.update({'ok': False, 'code': 'COMPILE_ERROR', 'errors': built.get('errors') or built.get('error'),
                       'fix': fix, 'review': review})
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return 1

    result['pdf'] = built.get('pdf') or out
    if code == 2 or (built.get('pages') or 1) > 1:
        fix.append(f"Runs past one page (about {built.get('lines_over')} lines over): shorten it.")
    if built.get('missing_text'):
        fix.append('Not readable as text in the PDF: ' + ', '.join(built['missing_text']))
    for w in built.get('warnings') or []:
        if 'past the margin' in w:
            review.append('A line runs past the margin (usually a long link in the contact line).')
        elif 'garbage' in w or 'Very little text' in w:
            fix.append(w)
    got = pdf_text(result['pdf'])
    if got and re.search('[ﬀ-ﬆ]', got):
        fix.append('The PDF\'s text has ligature characters ("ﬁ"), which tracking systems can\'t match.')

    if a.combine and not fix:
        both = os.path.join(os.path.dirname(out), os.path.basename(out).replace('_Cover_Letter_', '_Resume_and_Cover_Letter_'))
        if both == out:
            both = os.path.splitext(out)[0] + '-with-resume.pdf'
        move_old(both)
        err = combine(os.path.abspath(a.combine), result['pdf'], both)
        if err:
            fix.append(f"Couldn't make the combined PDF ({err}). Attach the resume and the letter separately.")
        else:
            result['combined'] = both

    result.update({'ok': not fix, 'fix': fix, 'review': review})
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 2 if fix or review else 0


if __name__ == '__main__':
    sys.exit(main())
