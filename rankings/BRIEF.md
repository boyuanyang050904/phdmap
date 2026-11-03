# Ranking-table brief (stage 0.4)

Goal: rankings/<subject>.csv with header exactly `school,rank,source`, ~60+ US schools
(keep all ties at the boundary), approximating the **latest U.S. News Best Graduate
Schools** ranking for that subject (science rankings were refreshed in the 2026 edition,
released 2026-04-07; use the latest edition you can find evidence for).

Hard rules
1. NEVER fetch usnews.com (its robots.txt disallows Anthropic agents) — not with curl,
   lib.fetch, WebFetch or Playwright.  Search-result snippets are not a source either.
2. A row may cite a URL only if you fetched that page yourself with the project fetcher
   and the page text states the rank:
       cd /home/user/phdmap && python3 -c "import sys;sys.path.insert(0,'.');\
from lib.fetch import fetcher;r=fetcher().get('URL');print(r.status);print(r.text[:200])"
   (it caches, honours robots.txt and rate limits; BlockedByRobots => skip that source).
   Strip HTML yourself (bs4/lxml are installed) and find the sentence with the rank.
3. Source priority: (a) the school's / department's own official news page announcing
   its U.S. News rank (these often also list schools tied with it — you may use those
   too, citing the same URL); (b) a third-party page that republishes the U.S. News
   table and says which edition; (c) only for rows still missing, your own knowledge,
   with source = `estimate`.
4. rank = integer; ties share the same integer (U.S. News "#41 (tie)" -> 41).
5. school = full official name in U.S. News style, e.g. "University of California,
   Berkeley", "University of Michigan--Ann Arbor", "Washington University in St. Louis".
6. Also write rankings/evidence/<subject>.jsonl: one JSON object per non-estimate row:
   {"school","rank","edition","source_url","fetched_at","quote"} where quote is the
   exact sentence from the page.
7. Sort by rank. Do not touch any other files in the repo.
