#!/usr/bin/env python3
"""Discover and queue internship postings from public ATS boards (Greenhouse, Lever, Ashby) or discovered URLs.

Usage:
  # Scan specific ATS company boards (or <folder>/boards.txt, one board URL or provider:slug per line)
  python search_ats.py --folder "JOB_SEARCH_FOLDER" --board greenhouse:stripe --board lever:mistral \\
      --keyword intern --location India --location Remote --append

  # Queue individual URLs discovered via web search (deduplicated against tracker.xlsx and jobs.txt)
  python search_ats.py --folder "JOB_SEARCH_FOLDER" --add-url "https://jobs.lever.co/..." --append

Supports Greenhouse (boards-api.greenhouse.io), Lever (api.lever.co), and Ashby (api.ashbyhq.com).
Never accepts LinkedIn URLs. Reuses deduplication from find_internships.py.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import find_internships as fi

USER_AGENT = 'Mozilla/5.0 (compatible; AutoInternship job-search script; reads public job boards)'


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def parse_board_spec(raw):
    """Parse 'greenhouse:slug', 'lever:slug', 'ashby:slug', or a board URL into (provider, slug)."""
    s = raw.strip().split('#', 1)[0].strip()
    if not s:
        return None
    m = re.match(r'^(greenhouse|lever|ashby):([A-Za-z0-9_.-]+)$', s, re.I)
    if m:
        return m.group(1).lower(), m.group(2)
    u = urllib.parse.urlparse(s)
    host = u.netloc.lower()
    parts = [p for p in u.path.split('/') if p]
    if not parts:
        return None
    if 'greenhouse.io' in host:
        return 'greenhouse', parts[0]
    if 'lever.co' in host:
        return 'lever', parts[0]
    if 'ashbyhq.com' in host:
        return 'ashby', parts[0]
    return None


def fetch_board(provider, slug):
    """Return normalized job dicts from a public Greenhouse, Lever, or Ashby board."""
    jobs = []
    if provider == 'greenhouse':
        data = get_json(f'https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(slug)}/jobs')
        for j in data.get('jobs') or []:
            loc = ((j.get('location') or {}).get('name') or '').strip()
            updated = j.get('updated_at') or ''
            ts = _parse_iso(updated)
            jobs.append({
                'company': slug,
                'role': (j.get('title') or '').strip(),
                'locations': [loc] if loc else [],
                'posted': dt.date.fromtimestamp(ts).isoformat() if ts else '',
                'timestamp': ts or 0,
                'url': j.get('absolute_url') or '',
                'source': 'greenhouse',
            })
    elif provider == 'lever':
        data = get_json(f'https://api.lever.co/v0/postings/{urllib.parse.quote(slug)}?mode=json')
        for j in data if isinstance(data, list) else []:
            cats = j.get('categories') or {}
            locs = [cats.get('location')] if cats.get('location') else []
            if cats.get('allLocations'):
                locs = [l for l in cats['allLocations'] if l]
            ts = (j.get('createdAt') or 0) / 1000.0 if j.get('createdAt') else 0
            jobs.append({
                'company': slug,
                'role': (j.get('text') or '').strip(),
                'locations': locs,
                'posted': dt.date.fromtimestamp(ts).isoformat() if ts else '',
                'timestamp': ts,
                'url': j.get('hostedUrl') or j.get('applyUrl') or '',
                'source': 'lever',
            })
    elif provider == 'ashby':
        data = get_json(f'https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(slug)}')
        for j in data.get('jobs') or []:
            if j.get('isListed') is False:
                continue
            locs = [j['location']] if j.get('location') else []
            if j.get('isRemote') and not any('remote' in l.lower() for l in locs):
                locs.append('Remote')
            ts = _parse_iso(j.get('publishedAt') or '')
            jobs.append({
                'company': slug,
                'role': (j.get('title') or '').strip(),
                'locations': locs,
                'posted': dt.date.fromtimestamp(ts).isoformat() if ts else '',
                'timestamp': ts or 0,
                'url': j.get('jobUrl') or j.get('applyUrl') or '',
                'source': 'ashby',
            })
    return jobs


def _parse_iso(val):
    if not val:
        return None
    try:
        return dt.datetime.fromisoformat(val.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def existing_keys(folder):
    """Collect posting_keys and (company, role) keys already in tracker.xlsx and jobs.txt."""
    keys = set()
    name_keys = fi.tracker_keys(folder)
    tracker_path = os.path.join(folder, 'tracker.xlsx')
    if os.path.exists(tracker_path):
        try:
            import tracker
            _, ws, _ = tracker.open_book(tracker_path)
            for row in tracker.rows(ws):
                row = tracker.read_links(ws, row)
                keys |= fi.posting_keys(row.get('posting_url'))
        except Exception:
            pass
    jobs_path = os.path.join(folder, 'jobs.txt')
    _, lines = fi.jobs_urls(jobs_path)
    for line in lines:
        m = re.search(r'https?://\S+', line)
        if m:
            keys |= fi.posting_keys(m.group(0))
    return keys, name_keys, lines


def append_to_jobs(folder, lines, entries):
    """Insert new job lines above '# done' in jobs.txt in place."""
    if not entries:
        return 0
    jobs_path = os.path.join(folder, 'jobs.txt')
    new_lines = []
    for e in entries:
        note_parts = [p for p in (e.get('company'), e.get('role'), ', '.join((e.get('locations') or [])[:3]),
                                  f"posted {e['posted']}" if e.get('posted') else '') if p]
        suffix = f"  # {' | '.join(note_parts)}" if note_parts else ''
        new_lines.append(f"{e['url']}{suffix}")
    done_at = next((i for i, l in enumerate(lines) if l.strip().lower() == '# done'), len(lines))
    pending, rest = lines[:done_at], lines[done_at:]
    while pending and not pending[-1].strip():
        pending.pop()
    merged = pending + new_lines + ([''] if rest else []) + rest
    with open(jobs_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(merged) + '\n')
    return len(new_lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folder', default='.')
    ap.add_argument('--board', action='append', default=[], help='greenhouse:slug, lever:slug, ashby:slug, or board URL')
    ap.add_argument('--boards-file', help='path to file with one board per line (defaults to <folder>/boards.txt if present)')
    ap.add_argument('--add-url', action='append', default=[], help='individual posting URL to deduplicate and queue')
    ap.add_argument('--keyword', action='append', default=[], help='title must contain at least one keyword')
    ap.add_argument('--exclude-keyword', action='append', default=[], help='title must not contain any of these')
    ap.add_argument('--location', action='append', default=[], help='location filter (city, country, or Remote)')
    ap.add_argument('--days', type=int)
    ap.add_argument('--limit', type=int, default=25)
    ap.add_argument('--append', action='store_true')
    a = ap.parse_args()

    folder = os.path.abspath(a.folder)
    seen_keys, seen_names, lines = existing_keys(folder)
    listings = []
    skipped = {'linkedin_link': 0, 'already_queued_or_tracked': 0, 'keyword': 0, 'location': 0, 'too_old': 0}
    errors = []

    # 1. Queue individual URLs (e.g. discovered via web search)
    for raw_url in a.add_url:
        url = raw_url.strip()
        if not url:
            continue
        if 'linkedin.com' in url.lower():
            skipped['linkedin_link'] += 1
            continue
        pkeys = fi.posting_keys(url)
        if pkeys & seen_keys:
            skipped['already_queued_or_tracked'] += 1
            continue
        seen_keys |= pkeys
        listings.append({'company': '', 'role': '', 'locations': [], 'posted': '', 'url': url, 'source': 'url'})

    # 2. Scan public ATS boards
    board_specs = list(a.board)
    bfile = a.boards_file or os.path.join(folder, 'boards.txt')
    if os.path.exists(bfile):
        board_specs.extend(open(bfile, encoding='utf-8').read().splitlines())

    kw = [fi.norm(k) for k in a.keyword]
    ex = [fi.norm(k) for k in a.exclude_keyword]
    cutoff = (dt.datetime.now() - dt.timedelta(days=a.days)).timestamp() if a.days else None

    for raw in board_specs:
        parsed = parse_board_spec(raw)
        if not parsed:
            continue
        provider, slug = parsed
        try:
            board_jobs = fetch_board(provider, slug)
        except Exception as e:
            errors.append(f'{provider}:{slug}: {e}')
            continue
        for j in board_jobs:
            url = j['url']
            if not url or 'linkedin.com' in url.lower():
                skipped['linkedin_link'] += 1
                continue
            title = fi.norm(j['role'])
            if (kw and not any(k in title for k in kw)) or any(k in title for k in ex):
                skipped['keyword'] += 1
                continue
            if a.location and not fi.location_match(j['locations'], a.location):
                skipped['location'] += 1
                continue
            if cutoff and j['timestamp'] and j['timestamp'] < cutoff:
                skipped['too_old'] += 1
                continue
            pkeys = fi.posting_keys(url)
            nkey = (fi.norm(j['company']), title)
            if (pkeys & seen_keys) or nkey in seen_names:
                skipped['already_queued_or_tracked'] += 1
                continue
            seen_keys |= pkeys
            seen_names.add(nkey)
            listings.append(j)

    listings.sort(key=lambda x: -(x.get('timestamp') or 0))
    total = len(listings)
    listings = listings[:a.limit]
    for item in listings:
        item.pop('timestamp', None)

    added = append_to_jobs(folder, lines, listings) if a.append else 0
    fi.out({
        'ok': True,
        'matches': total,
        'shown': len(listings),
        'added_to_jobs_txt': added,
        'skipped': skipped,
        'errors': errors,
        'listings': listings,
    })


if __name__ == '__main__':
    main()
