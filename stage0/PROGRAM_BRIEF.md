# Program-discovery brief (stage 0.2)

You map relevant faculty (found via OpenAlex) to the **PhD programs they can take
students from**, one institution at a time. Repo: /home/user/phdmap. Work only through
the helper CLI below; write only your own output files.

## Hard rules (the user's)
- Every fact you record (program name, URL, PhD status, faculty membership) must come
  from a page you fetched **with the project fetcher** (cache + robots.txt + delay):
  `python3 stage0/program_tool.py fetch|text|match ...`. Never fill anything from memory.
  If you cannot verify something, write null and say why in `problems`.
- WebSearch (mode "standard") is ONLY for discovering candidate URLs. Search snippets/
  summaries are NOT evidence. Do not use WebFetch or curl.
- If the tool prints `BLOCKED by robots.txt`, respect it: record the URL in `problems`
  and move on (no workarounds).

## Tool
    cd /home/user/phdmap
    python3 stage0/program_tool.py authors "<OpenAlex institution name>"   # who to look for
    python3 stage0/program_tool.py fetch URL [--render]     # status/title + program/faculty links
    python3 stage0/program_tool.py text  URL [--render] [--grep REGEX]
    python3 stage0/program_tool.py match "<OpenAlex institution name>" URL [URL...] [--render]
`--render` = headless Chromium for JS-built pages (slower; use only when the plain fetch
lacks the content). `match` prints which relevant authors' names appear on the page.

## What to find, per institution
1. Run `authors` to see the relevant authors (direction A = statistical/computational
   genomics; B = computational protein design/structure; tier core/peripheral).
2. Find this institution's **PhD** programs of these kinds (only for directions that have
   authors):
   - A: computational biology / bioinformatics / biomedical informatics / biomedical data
     science / quantitative or systems biology; genetics / genomics / human genetics /
     genome sciences; **biostatistics**; statistics (only if relevant authors are its
     faculty); umbrella biomedical programs and their relevant tracks.
   - B: bioengineering / biomedical engineering; biophysics / structural or molecular
     biophysics; chemistry / chemical biology; computational biology; computer science;
     biochemistry; umbrella programs and their relevant tracks.
   Typically 3–8 programs. Skip programs with no plausible relevance (no matched authors
   AND not one of the core types above).
3. For each program record its official page (fetched), a short exact quote proving it
   is a PhD program, and the page(s) listing its faculty / training faculty / participating
   faculty (for a departmental program, the department faculty directory is fine). Run
   `match` on those faculty pages (use --render if the list is JS-loaded; try alternative
   pages such as "faculty interests", "research areas", "labs", graduate-school
   "program faculty" listings if the main list is unreadable).
4. Core authors still unmatched after step 3: for up to 6 of them, find their official
   faculty profile at this institution and check (from the fetched page) which graduate
   program(s) they belong to; then `match` that program's faculty page or record it.
5. Independent institutes (Scripps Research, MSK, St. Jude, Cold Spring Harbor,
   Rockefeller, TTIC, cancer centers, medical centers...): first establish from a fetched
   page whether the institution itself grants PhDs (e.g. its own graduate school), and
   which programs. If it does not grant degrees (e.g. Broad Institute), say so with the
   evidence and stop.

## Classification fields
- discipline: one of comp_bio, genetics_genomics, biostatistics, statistics,
  umbrella_biomedical, biophysics, bioengineering, chemistry, computer_science,
  biochemistry, or "other:<short label>" (e.g. other:molecular_engineering,
  other:epidemiology, other:pharmaceutical_sciences, other:data_science).
- program_type: "biostat" for biostatistics PhDs; "umbrella_track" when students are
  admitted through an umbrella (e.g. a home program / track / subprogram of a
  multi-program biomedical umbrella); "independent" otherwise.
  Put the umbrella's name in umbrella_name.

## Output: data/stage0/programs/<slug>.json  (write it as soon as each institution is done)
slug = institution name lowercased, non-alphanumerics -> "_".
{
  "institution": "<OpenAlex name>",
  "checked_at": "<UTC ISO timestamp>",
  "grants_phd": true | false | null,
  "grants_phd_evidence": {"url": "...", "quote": "..."} | null,
  "programs": [
    {"program_name": "...", "degree": "PhD", "discipline": "...", "program_type": "...",
     "umbrella_name": null, "program_url": "...", "phd_evidence_quote": "...",
     "faculty_list_urls": [{"url": "...", "render": false}],
     "matched_authors": ["<names exactly as printed by match>"],
     "notes": ""}
  ],
  "unmatched_core_authors": [{"name": "...", "program_found": null | "...",
                              "evidence_url": null | "...", "note": ""}],
  "problems": ["..."]
}
Validate with: python3 -c "import json;json.load(open('data/stage0/programs/<slug>.json'))"

Efficiency: ~10–25 tool calls per institution. Prefer official graduate-program pages
over news/third-party pages. Don't paste whole pages into your context — use --grep.
