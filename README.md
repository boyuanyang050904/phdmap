# phdmap — PhD program discovery & application tracker

Personal tool for choosing and tracking US PhD applications (Fall 2027 entry) in

* **A. Statistical / computational genomics** — A1 single-cell CRISPR screens / Perturb-seq
  methods, A2 causal network inference, A3 statistical genetics (GWAS summary
  statistics, Mendelian randomization, polygenic scores)
* **B. Computational protein design & structure** — B4 antibody affinity maturation /
  optimization, B5 de novo protein generation, B6 structure prediction (complexes, PPI
  interfaces)

## Ground rules

* Every fact (faculty, program, deadline, link, requirement) comes from an actual API
  response or fetched page and carries `source_url` + fetch date. Unverifiable → `null`.
  The only exception is the coarse ranking tables (`rankings/`, rows marked `estimate`).
* All HTTP goes through `lib/fetch.py`: on-disk cache (`cache/http/`), robots.txt honoured
  for our UA **and** Anthropic agent tokens (`Claude-User`, `ClaudeBot`, `anthropic-ai`),
  crawl-delay honoured, ≥2 s per host. Blocked/failed URLs → `cache/fetch_log.jsonl`.
* OpenAlex calls (`lib/openalex.py`) send `mailto=boyuan.yang@emory.edu` and the API key
  from `.env` (git-ignored).
* TLS verification is never disabled. `lib/tlsfix.py` adds Mozilla's current root store
  (certifi 2026.10.23) to the proxy bundle and fetches missing intermediates via AIA,
  keeping them only if they verify against a trusted root (many US university servers
  use InCommon/emSign chains without sending intermediates).

## Stage 0 — program discovery (`stage0/`)

| step | script | output |
|---|---|---|
| 0.1 works | `s01_harvest_works.py` (queries in `queries.py`) | `data/stage0/works_{A,B}.jsonl` (local only) |
| 0.1 authors | `s02_authors.py` — US corresponding/last authors, methods-paper flag | `authors_{A,B}.json` |
| 0.2 entities | `s03_entities.py` — OpenAlex author + institution entities | `author_entities.json`, `institutions.json` |
| 0.2 homes | `s04_homes.py` — roll authors up to universities (lineage, overrides in `lineage_overrides.json`) | `homes.json` |
| 0.2 programs | agents following `PROGRAM_BRIEF.md` with `program_tool.py` | `data/stage0/programs/*.json` |
| 0.2 matching | `s06_match.py` — name-match authors on cached faculty pages | `program_matches.json` |
| 0.3 ISCB | `s05_iscb.py` | `iscb_us_phd.json` |
| 0.4 rankings | agents following `rankings/BRIEF.md` | `rankings/*.csv`, `rankings/evidence/*.jsonl` |
| 0.5–0.6 | `s07_candidates.py` | `candidates.csv`, `whitelist.csv`, `unresolved.csv`, `excluded.csv` |

**Relevant author** = US-affiliated last or corresponding author of ≥1 matching work since
2022 whose title/abstract reads as a methods paper. *core* = ≥2 matching works (≥1
methods); *possible* = a single methods paper. Faculty counts in `candidates.csv` only
include authors whose names appear on the program's own faculty page.

### Your decisions (re-run `python3 stage0/s07_candidates.py` afterwards; nothing is lost)

* `whitelist.csv` → `confirm` = 1 to keep an independent institute regardless of rank
* `unresolved.csv` → `user_rank` (a number) or `keep` = 1 / 0
* program types without a ranking table (e.g. 35 Biochemistry programs): instead of row by
  row, copy `user_discipline_map.example.json` to `user_discipline_map.json` and map types
  to tables in bulk
* `candidates.csv` → add `selected` = 1 for programs to pursue in stage 1 (kept on re-runs)

### Known limitations of stage 0 (see `stage0_report.md` for details)

* **Rankings** are approximations: U.S. News blocks Anthropic agents in robots.txt, so the
  tables were assembled from schools' own 2026-edition announcements (`rankings/evidence/`);
  rows without such a page are `estimate`. The 2026 edition ranks **biostatistics
  separately** from statistics; `statistics.csv` covers statistics only, so biostatistics
  programs at schools absent from it are sent to `unresolved.csv` instead of being dropped.
* **Blocked sites**: robots.txt (including rules aimed at Anthropic agents), Cloudflare/
  Incapsula challenges, or unreachable hosts prevented reading several faculty lists
  (notably Harvard umbrella programs, UCSF, JHU, Michigan, Mount Sinai, Einstein,
  Princeton QCB, CSHL, Stowers, City of Hope). Those programs show low or zero faculty
  counts; `school_core_authors_openalex` in `candidates.csv` shows how many relevant
  authors OpenAlex places at the school regardless.
* **ISCB list** lives on `transition.iscb.org`, whose robots.txt disallows all agents; save
  it manually to `data/manual/iscb_displaytable.html` and re-run `s05_iscb.py`.
* Topic coverage comes from title/abstract keyword search; faculty whose recent papers use
  other wording can be missed. Name matching can confuse same-name people (rare; flagged).

## Setup

```
python3 -m pip install requests beautifulsoup4 lxml pandas
echo "OPENALEX_API_KEY=..." > .env      # free key, see help.openalex.org
```
