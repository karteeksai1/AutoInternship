#!/usr/bin/env python3
"""Find internships from the SimplifyJobs list and queue them in jobs.txt.

Source: the data file behind https://github.com/SimplifyJobs/Summer2027-Internships (updated daily).

Usage:
  python find_internships.py --folder "JOB_SEARCH_FOLDER" [filters] [--append]
  python find_internships.py --folder "JOB_SEARCH_FOLDER" --tidy
      Moves links in jobs.txt that are already in tracker.xlsx (same link, job ID, or company and role), listed
      twice, or (for a U.S. profile) outside the U.S. by their note's location, below "# done". Nothing is
      downloaded and nothing is deleted.

Filters (all optional; without them, sensible defaults come from profile.json in the folder):
  --term "Summer 2027"        internship term (default: profile's internship term, else Summer 2027)
  --category software|data|hardware|product|quant   (repeatable; default: all)
  --location CA --location Seattle --location Remote  (repeatable; state codes, cities, SF, NYC, Remote)
  --keyword data --keyword analyst                  (repeatable; any must appear in the title)
  --exclude-keyword phd --exclude-keyword senior    (repeatable)
  --degree "Bachelor's"       keep listings open to this degree level (default: from profile.json)
  --needs-sponsorship         drop listings marked "Does Not Offer Sponsorship" or "U.S. Citizenship is Required".
                              Default from profile.json: if the user needs sponsorship, citizenship-only listings are
                              dropped; "Does Not Offer Sponsorship" listings are dropped only for seniors, since
                              underclassmen apply for the experience.
  --no-citizenship            drop "U.S. Citizenship is Required" listings
  --days 30                   only listings posted in the last N days
  --limit 25                  at most N results, newest first
  --append                    add the results to jobs.txt (above any "# done" line), one link per line with a note
  --include-abroad            keep listings outside the U.S. (a U.S. profile drops them: the user's call, 2026-11-08)

Skips LinkedIn links (LinkedIn prohibits automated tools) and listings that are closed, already in tracker.xlsx (same company and role) or already in jobs.txt.
Prints one JSON object. Exit codes: 0 ok, 1 bad input, 6 couldn't download the list (network).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import urllib.request

SOURCE = 'https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json'
REPO = 'https://github.com/SimplifyJobs/Summer2027-Internships'
CATEGORIES = {
    'software': {'Software', 'Software Engineering'},
    'data': {'AI/ML/Data', 'Data Science, AI & Machine Learning'},
    'hardware': {'Hardware', 'Hardware Engineering'},
    'product': {'Product', 'Product Management'},
    'quant': {'Quant', 'Quantitative Finance'},
}
for alias, target in (('ai', 'data'), ('ml', 'data'), ('swe', 'software'), ('pm', 'product')):
    CATEGORIES[alias] = CATEGORIES[target]
CITY_ALIASES = {
    'san francisco': ['sf', 'san francisco'], 'sf': ['sf', 'san francisco'],
    'new york': ['nyc', 'new york'], 'nyc': ['nyc', 'new york'],
    'bay area': ['sf', 'san francisco', 'san jose', 'santa clara', 'mountain view', 'palo alto', 'sunnyvale',
                 'menlo park', 'redwood city', 'cupertino', 'oakland', 'fremont', 'milpitas', 'san mateo', 'foster city'],
    'la': ['los angeles', 'la,'], 'los angeles': ['los angeles'],
}


def out(obj, code=0):
    print(json.dumps(obj, indent=1, default=str))
    sys.exit(code)


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower()).strip()


def degree_level(text):
    t = norm(text)
    if re.search(r'\bph ?d\b|doctor', t):
        return 'PhD'
    if re.search(r'\bmba\b', t):
        return 'MBA'
    if re.search(r'master|\bm ?s\b|\bm ?sc\b|\bm ?eng\b|\bm ?a\b', t):
        return "Master's"
    if re.search(r'associate', t):
        return "Associate's"
    if re.search(r'bachelor|\bb ?s\b|\bb ?a\b|\bb ?sc\b|\bb ?eng\b|undergrad', t):
        return "Bachelor's"
    return None


def load_profile(folder):
    p = os.path.join(folder, 'profile.json')
    try:
        return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def below_senior(profile, term):
    """True for freshmen, sophomores and juniors; False for seniors and graduate students; None if unknown."""
    st = str(profile.get('classStanding') or '').lower()
    if st:
        if re.search(r'senior|fourth|4th|final|grad', st):
            return False
        if re.search(r'fresh|first|1st|soph|second|2nd|junior|third|3rd', st):
            return True
    grad = str(profile.get('expectedGraduation') or ((profile.get('education') or [{}])[0] or {}).get('end', ''))
    gy, ty = re.search(r'(20\d{2})', grad), re.search(r'(20\d{2})', term)
    if gy and ty:
        return int(gy.group(1)) > int(ty.group(1))
    return None


def location_match(locations, prefs):
    if not prefs:
        return True
    locs = [l.lower() for l in locations]
    for p in prefs:
        q = p.strip()
        if re.fullmatch(r'[A-Za-z]{2}', q) and q.upper() == q:  # state code like CA
            if any(re.search(rf',\s*{q.lower()}\b', l) for l in locs):
                return True
            continue
        ql = q.lower()
        if ql == 'remote':
            if any('remote' in l for l in locs):
                return True
            continue
        for alias in CITY_ALIASES.get(ql, [ql]):
            if any(alias == l or alias in l for l in locs):
                return True
    return False


STATE_CODES = {'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
               'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA',
               'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC', 'PR'}
US_PLACE = re.compile(r'\b(united states|usa|u\.s\.a?|nyc|new york|san francisco|sf|bay area|silicon valley|seattle|boston|chicago|'
                      r'austin|los angeles|washington,? d\.?c\.?|alabama|alaska|arizona|arkansas|california|colorado|connecticut|'
                      r'delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|'
                      r'massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|'
                      r'new mexico|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|'
                      r'south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming)\b|\bLA\b', re.I)
ABROAD = re.compile(r'\b(canada|united kingdom|uk|england|scotland|wales|ireland|germany|france|india|china|singapore|japan|korea|'
                    r'taiwan|hong kong|israel|netherlands|spain|portugal|poland|mexico|brazil|argentina|chile|colombia|australia|'
                    r'new zealand|switzerland|sweden|norway|denmark|finland|italy|austria|belgium|czechia|czech republic|romania|'
                    r'hungary|greece|turkey|vietnam|philippines|malaysia|indonesia|thailand|uae|united arab emirates|saudi arabia|'
                    r'egypt|nigeria|kenya|south africa|luxembourg|estonia|lithuania|ukraine|serbia|bulgaria|croatia|pakistan|qatar|'
                    r'costa rica|peru|london|toronto|vancouver|montreal|montréal|ottawa|waterloo|markham|calgary|burnaby|mississauga|'
                    r'dublin|berlin|munich|paris|amsterdam|zurich|zürich|geneva|tokyo|seoul|bangalore|bengaluru|hyderabad|pune|'
                    r'mumbai|chennai|gurgaon|gurugram|noida|tel aviv|sydney|melbourne|shanghai|beijing|shenzhen|taipei|warsaw|'
                    r'krakow|kraków|prague|madrid|barcelona|lisbon|stockholm|copenhagen|oslo|helsinki|milan|vienna|brussels|'
                    r'edinburgh|manchester|mexico city|são paulo|sao paulo|manila|kuala lumpur|bangkok|dubai)\b', re.I)
PROVINCE = re.compile(r',\s*(ON|BC|QC|AB|MB|SK|NS|NB|NL|PE)\b')


def home_is_us(profile):
    return norm(profile.get('authCountry') or profile.get('country')) in ('united states', 'usa', 'us', 'united states of america')


def outside_us(places):
    """True when the locations name only places outside the U.S. ("London, UK, Edinburgh, UK"), False when one is in
    the U.S., None when they don't say ("Remote"). SimplifyJobs writes U.S. places as "City, ST", "NYC" or "SF"."""
    text = ', '.join(places) if isinstance(places, (list, tuple)) else str(places or '')
    canada = re.search(r'\bcanada\b', text, re.I) or PROVINCE.search(text)
    codes = {c for c in re.findall(r',\s*([A-Z]{2})\b', text) if c in STATE_CODES and not (c == 'CA' and canada)}
    if codes or US_PLACE.search(text) or re.search(r'\bUS\b', text):
        return False
    if ABROAD.search(text) or canada:
        return True
    return None


def tracker_keys(folder):
    path = os.path.join(folder, 'tracker.xlsx')
    keys = set()
    if not os.path.exists(path):
        return keys
    try:
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True).active
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not row:
                continue
            keys.add((norm(row[2]), norm(row[3])))  # company, role
    except Exception:
        pass
    return keys


def jobs_urls(path):
    if not os.path.exists(path):
        return set(), []
    lines = open(path, encoding='utf-8').read().splitlines()
    urls = {m.group(0).split('?')[0].rstrip('/') for l in lines for m in [re.search(r'https?://\S+', l)] if m}
    return urls, lines


UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
# Query parameters that say where a click came from or how the page is shown, not which job it is
TRACKING = re.compile(r'(utm_[a-z]+|gh_src|source|src|ref|referrer|lever-source|lever-origin|embed|in_iframe|mode|iis|iisn)$')


def posting_keys(url):
    """Every way to recognize one posting behind different links.

    The same job turns up as boards.greenhouse.io/x/jobs/1 and job-boards.greenhouse.io/x/jobs/1?gh_src=...,
    as a company page with ?gh_jid=1, as an Ashby link with and without /application?embed=true, or as a Workday
    link whose location part differs. Comparing whole links missed those, so each link also yields its job ID.
    """
    m = re.match(r'https?://(?:www\.)?([^/?#\s]+)([^?#\s]*)(?:\?([^#\s]*))?', str(url or '').strip().lower())
    if not m:
        return set()
    host, query = m.group(1), m.group(3) or ''
    path = re.sub(r'/(application|apply(/[a-z]+)?)$', '', m.group(2).rstrip('/'))  # form pages of the same posting
    # Keep the query except tracking: company pages put the job in it (open-positions/?gh_jid=1, jobs?id=2)
    params = sorted(p for p in query.split('&') if p and not TRACKING.match(p.split('=')[0]))
    keys = {host + path + ('?' + '&'.join(params) if params else '')}
    gh = re.search(r'(?:^|&)gh_jid=(\d+)', query)
    if host.endswith('greenhouse.io'):  # its embed form takes the ID as token=; elsewhere token= is something else
        gh = re.search(r'/jobs/(\d+)', path) or re.search(r'(?:^|&)token=(\d+)', query) or gh
    if gh:  # Greenhouse job IDs are unique across all boards, so a company page's gh_jid matches the board link
        keys.add('greenhouse:' + gh.group(1))
    if host.endswith(('ashbyhq.com', 'lever.co')):
        u = re.search(UUID, path)
        if u:
            keys.add('uuid:' + u.group(0))
    if 'myworkday' in host:  # myworkdayjobs.com and myworkdaysite.com
        req = re.search(r'_([a-z0-9-]*\d[a-z0-9-]*)$', path)  # the link ends with the requisition: ..._R12345, ..._JR-004521
        parts = path.split('/')  # myworkdaysite.com links read /[en-US/]recruiting/<tenant>/<site>/job/...
        after = parts[parts.index('recruiting') + 1] if 'recruiting' in parts[:-1] else host
        tenant = host.split('.')[0] if 'myworkdayjobs' in host else after
        if req:  # requisition numbers repeat across companies, so the tenant is part of the key
            keys.add(f'workday:{tenant}:{req.group(1)}')
    return keys


def name_key(company, role):
    return f'name:{norm(company)}|{norm(role)}' if norm(company) and norm(role) else None


def tidy(folder):
    """Move links already in the tracker, or listed twice, below jobs.txt's '# done' line.

    The top of the queue goes stale when a run forgets to move what it processed, and each batch then re-checked
    every pick against tracker.xlsx with one-off scripts. Matching uses the link, its job ID, and the company and
    role from the line's note (any status counts, Skipped included). Lines are moved, never deleted.
    """
    jobs_path = os.path.join(folder, 'jobs.txt')
    tracker_path = os.path.join(folder, 'tracker.xlsx')
    if not os.path.exists(jobs_path):
        out({'ok': False, 'error': f'no jobs.txt in {folder}'}, 1)
    tracked = {}
    if os.path.exists(tracker_path):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tracker  # prints its own error and exits when openpyxl is missing
        tracker.lock_tracker(tracker_path)  # never read the workbook halfway through another call's save
        _, ws, _ = tracker.open_book(tracker_path)
        for row in tracker.rows(ws):
            row = tracker.read_links(ws, row)
            for k in posting_keys(row['posting_url']) | {name_key(row['company'], row['role'])}:
                if k:
                    tracked.setdefault(k, row)

    lines = open(jobs_path, encoding='utf-8').read().splitlines()
    done_at = next((i for i, l in enumerate(lines) if l.strip().lower() == '# done'), len(lines))
    keep, moved, seen = [], [], set()
    us_only = home_is_us(load_profile(folder))  # the user's call (2026-11-08): batches skip jobs outside the U.S.
    for line in lines[:done_at]:
        m = re.search(r'https?://\S+', line)
        if not m:
            keep.append(line)
            continue
        rest = line[m.end():]
        note = rest.split('#', 1)[1].strip() if '#' in rest else ''
        parts = [p.strip() for p in note.split('|')]
        links = posting_keys(m.group(0))
        # The same title at the same company counts as applied (the tracker row), but two queued lines count as
        # duplicates only by link or job ID: one title is often posted separately per city (Chicago, London).
        named = {name_key(parts[0], parts[1])} - {None} if len(parts) > 1 else set()
        hit = next((tracked[k] for k in links | named if k in tracked), None)
        if hit:
            moved.append((line, note or m.group(0), f"in tracker: {hit['id']} {hit['status']}".strip()))
        elif links & seen:
            moved.append((line, note or m.group(0), 'listed twice'))
        elif us_only and len(parts) > 2 and outside_us(parts[2]):
            moved.append((line.rstrip() + ' | not in the U.S.', note, 'not in the U.S.'))
        else:
            keep.append(line)
        seen |= links

    if moved:
        while keep and not keep[-1].strip():
            keep.pop()
        merged = keep + ['', '# done'] + [l for l, _, _ in moved] + lines[done_at + 1:]
        with open(jobs_path, 'w', encoding='utf-8') as f:  # rewrites jobs.txt in place; nothing is deleted
            f.write('\n'.join(merged) + '\n')
    shown = [f'{n[:80]} ({why})' for _, n, why in moved[:10]]
    return {'ok': True, 'moved_below_done': len(moved),
            'in_tracker': sum(1 for *_, why in moved if why.startswith('in tracker')),
            'listed_twice': sum(1 for *_, why in moved if why == 'listed twice'),
            'not_in_us': sum(1 for *_, why in moved if why == 'not in the U.S.'),
            'left_in_queue': sum(1 for l in keep if re.search(r'https?://', l)),
            'moved': shown + ([f'... {len(moved) - 10} more'] if len(moved) > 10 else [])}


def fetch():
    cache = os.path.join(tempfile.gettempdir(), 'simplify-summer2027-listings.json')
    try:
        if os.path.exists(cache) and (dt.datetime.now().timestamp() - os.path.getmtime(cache)) < 3 * 3600:
            return json.load(open(cache, encoding='utf-8'))
        req = urllib.request.Request(SOURCE, headers={'User-Agent': 'internship-application-skill'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        open(cache, 'wb').write(data)  # temp folder only
        return json.loads(data)
    except Exception as e:
        out({'ok': False, 'code': 'NETWORK', 'error': f'Could not download the SimplifyJobs list: {e}',
             'hint': f'Allow raw.githubusercontent.com in network settings, or open {REPO} in the browser and read the table there.'}, 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folder', default='.')
    ap.add_argument('--term')
    ap.add_argument('--category', action='append', default=[])
    ap.add_argument('--location', action='append', default=[])
    ap.add_argument('--keyword', action='append', default=[])
    ap.add_argument('--exclude-keyword', action='append', default=[])
    ap.add_argument('--degree')
    ap.add_argument('--needs-sponsorship', action='store_true', default=None)
    ap.add_argument('--no-citizenship', action='store_true')
    ap.add_argument('--days', type=int)
    ap.add_argument('--limit', type=int, default=25)
    ap.add_argument('--append', action='store_true')
    ap.add_argument('--include-abroad', action='store_true', help='keep listings outside the U.S. (dropped by default for a U.S. profile)')
    ap.add_argument('--tidy', action='store_true', help='only move queued links already in the tracker below "# done"')
    a = ap.parse_args()

    folder = os.path.abspath(a.folder)
    if a.tidy:
        out(tidy(folder))
    profile = load_profile(folder)
    defaults_used = {}

    term = a.term
    if not term:
        m = re.search(r'(summer|fall|winter|spring)\s+(20\d{2})', str(profile.get('internshipTerm', '')), re.I)
        term = f'{m.group(1).title()} {m.group(2)}' if m else 'Summer 2027'
        defaults_used['term'] = term

    degree = a.degree
    if not degree:
        edu = (profile.get('education') or [{}])[0]
        degree = degree_level(edu.get('degree', ''))
        if degree:
            defaults_used['degree'] = degree
    forced = a.needs_sponsorship is True
    needs_sponsorship = forced or profile.get('needsSponsorship') == 'yes'
    below = below_senior(profile, term)
    # Before senior year the user applies for experience, so no-sponsorship postings stay in.
    drop_no_sponsor = needs_sponsorship and (forced or below is False)
    drop_citizenship = needs_sponsorship or a.no_citizenship  # needing sponsorship means not a citizen
    if not forced and needs_sponsorship:
        defaults_used['sponsorship'] = ('keeping postings that do not sponsor (below senior)' if not drop_no_sponsor
                                        else 'dropping postings that do not sponsor (senior)')

    cats = set()
    for c in a.category:
        key = c.strip().lower()
        if key not in CATEGORIES:
            out({'ok': False, 'error': f'unknown category: {c}', 'categories': ['software', 'data', 'hardware', 'product', 'quant']}, 1)
        cats |= CATEGORIES[key]

    data = fetch()
    cutoff = (dt.datetime.now() - dt.timedelta(days=a.days)).timestamp() if a.days else None
    tracked = tracker_keys(folder)
    jobs_path = os.path.join(folder, 'jobs.txt')
    queued, lines = jobs_urls(jobs_path)
    kw = [norm(k) for k in a.keyword]
    ex = [norm(k) for k in a.exclude_keyword]

    skipped = {'linkedin_link': 0, 'closed': 0, 'term': 0, 'category': 0, 'location': 0, 'outside_us': 0, 'keyword': 0, 'degree': 0,
               'sponsorship': 0, 'too_old': 0, 'already_tracked': 0, 'already_in_jobs_txt': 0}
    us_only = home_is_us(profile) and not a.include_abroad
    results = []
    for x in data:
        if 'linkedin.com' in (x.get('url') or '').lower():  # never queue LinkedIn; apply on the company's site
            skipped['linkedin_link'] += 1; continue
        if not x.get('active') or not x.get('is_visible', True):
            skipped['closed'] += 1; continue
        if term not in (x.get('terms') or []):
            skipped['term'] += 1; continue
        if cats and x.get('category') not in cats:
            skipped['category'] += 1; continue
        if not location_match(x.get('locations') or [], a.location):
            skipped['location'] += 1; continue
        if us_only and outside_us(x.get('locations') or []):
            skipped['outside_us'] += 1; continue
        title = norm(x.get('title'))
        if (kw and not any(k in title for k in kw)) or any(k in title for k in ex):
            skipped['keyword'] += 1; continue
        degrees = x.get('degrees') or []
        if degree and degrees and degree not in degrees:
            skipped['degree'] += 1; continue
        sp = x.get('sponsorship', '')
        if (drop_no_sponsor and sp == 'Does Not Offer Sponsorship') or \
                (drop_citizenship and sp == 'U.S. Citizenship is Required'):
            skipped['sponsorship'] += 1; continue
        if cutoff and (x.get('date_posted') or 0) < cutoff:
            skipped['too_old'] += 1; continue
        if (norm(x.get('company_name')), title) in tracked:
            skipped['already_tracked'] += 1; continue
        if x.get('url', '').split('?')[0].rstrip('/') in queued:
            skipped['already_in_jobs_txt'] += 1; continue
        results.append(x)

    results.sort(key=lambda x: -(x.get('date_posted') or 0))
    seen, unique = set(), []
    for x in results:  # the same role is sometimes listed twice under different links
        key = (norm(x.get('company_name')), norm(x.get('title')))
        if key not in seen:
            seen.add(key)
            unique.append(x)
    skipped['duplicate_listing'] = len(results) - len(unique)
    results = unique
    total_matches = len(results)
    results = results[:a.limit]
    listings = [{
        'company': x['company_name'], 'role': x['title'], 'locations': x.get('locations', []),
        'posted': dt.date.fromtimestamp(x['date_posted']).isoformat() if x.get('date_posted') else '',
        'category': x.get('category'), 'degrees': x.get('degrees', []), 'sponsorship': x.get('sponsorship'),
        'url': x.get('url'),
    } for x in results]

    added = 0
    if a.append and listings:
        new_lines = [f"{l['url']}  # {l['company']} | {l['role']} | {', '.join(l['locations'][:3])} | posted {l['posted']}"
                     for l in listings]
        done_at = next((i for i, l in enumerate(lines) if l.strip().lower() == '# done'), len(lines))
        pending, rest = lines[:done_at], lines[done_at:]
        while pending and not pending[-1].strip():
            pending.pop()
        merged = pending + new_lines + ([''] if rest else []) + rest
        with open(jobs_path, 'w', encoding='utf-8') as f:  # rewrites jobs.txt in place; nothing is deleted
            f.write('\n'.join(merged) + '\n')
        added = len(new_lines)

    out({'ok': True, 'source': REPO, 'term': term, 'filters': {
        'categories': a.category, 'locations': a.location, 'keywords': a.keyword, 'exclude_keywords': a.exclude_keyword,
        'degree': degree, 'drop_no_sponsorship_postings': drop_no_sponsor,
        'drop_citizenship_required': drop_citizenship, 'below_senior': below, 'days': a.days}, 'defaults_from_profile': defaults_used,
        'matches': total_matches, 'shown': len(listings), 'added_to_jobs_txt': added, 'skipped': skipped, 'listings': listings})


if __name__ == '__main__':
    main()
