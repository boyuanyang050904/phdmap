# Stage-1 brief: program requirements, admissions, funding, faculty list

One JSON file per program: data/stage1/programs/<program_id>.json (program_id given to you).
Repo: /home/user/phdmap. Fetch ONLY with the project tool (cache + robots.txt + delay):

    python3 stage0/program_tool.py fetch URL [--render]        # status + useful links
    python3 stage0/program_tool.py text  URL [--render] [--grep REGEX]   (put --grep LAST; regex is case-insensitive already)
    python3 stage0/program_tool.py find  START_URL "REGEX" --depth 2 --max 30

## Hard rules
- Every non-null value must come from a page you fetched with the tool and carry
  `source_url`, `fetched_at` (printed by the tool) and `quote`: an EXACT, contiguous
  snippet (10–300 chars) copied from that page's visible text that states the fact.
  A validator re-reads the cached page and rejects any quote not found verbatim
  (whitespace-insensitive). Never fill anything from memory. Unknown -> value null with a
  `note` saying what you looked for and where.
- WebSearch only to discover URLs (budget is shared: max ~8 searches per program).
  Prefer navigating official pages. robots.txt blocks: record in `problems`, no workaround.
- Requirements often live at the GRADUATE-SCHOOL level (application fee, TOEFL rules,
  DI code, transcripts). Use the most specific official page that applies to this program
  and say in `scope` whether the fact is "program" or "graduate_school" level.
- Deadlines: this cycle = applications for Fall 2027 entry (deadlines ~Dec 2026). If the
  page shows an older cycle's date, record it anyway with `cycle` (e.g. "Fall 2026") so it
  can be flagged as possibly outdated.

## Field object
    {"value": <string|number|bool|null>, "source_url": "...", "fetched_at": "...",
     "quote": "...", "scope": "program|graduate_school", "cycle": null, "note": null}

## File schema
{
 "program_id": "...", "school": "...", "program": "...", "checked_at": "<UTC ISO>",
 "program_url": FIELD,
 "deadline": FIELD,                       # official application deadline (date string)
 "priority_deadline": FIELD,              # fellowship/priority deadline if different, else null
 "application_fee": FIELD,                # e.g. "$105"
 "fee_waiver": FIELD,                     # conditions, if stated
 "gre_policy": FIELD,                     # "not accepted" | "optional" | "required" (+ quote)
 "letters_required": FIELD,               # integer
 "application_system_url": FIELD,         # the online application portal link
 "toefl": {
   "waiver_conditions": FIELD,            # verbatim summary of who is exempt
   "waiver_basis": FIELD,                 # "native_language" | "degree" | "citizenship_status" | combos
   "us_degree_waives": FIELD,             # bool: does a degree from a US institution waive it?
   "pr_exempt": FIELD,                    # bool: are US permanent residents exempt?
   "min_total": FIELD, "min_subscores": FIELD,
   "validity_rule": FIELD,                # e.g. "within 2 years of application deadline" / "of enrollment"
   "di_code": FIELD,                      # ETS institution code
   "self_report_accepted": FIELD          # bool/description: unofficial/self-reported scores at application stage
 },
 "admissions_mode": FIELD,                # "rotation" | "direct" | "both"
 "contact_faculty_advice": FIELD,         # what the official site says about contacting PIs before applying
 "stipend": FIELD,                        # amount + year
 "guaranteed_years": FIELD,               # e.g. "5 years" / "full funding for duration in good standing"
 "pr_domestic": FIELD,                    # bool: permanent residents treated as domestic applicants
 "t32_citizen_pr_only": FIELD,            # NIH T32 (or similar) training grants limited to citizens/PRs
 "faculty_list": {
   "source_urls": ["..."],                # the official program faculty page(s) (render flag if needed)
   "render": false,
   "faculty": [{"name": "...", "title": "...|null", "department": "...|null",
                "profile_url": "...|null", "lab_url": "...|null", "source_url": "..."}]
 },
 "problems": ["..."]
}

For faculty_list.faculty: list EVERY faculty member on the program faculty page(s) (names
exactly as printed). Titles / lab URLs only if shown on the page or on a fetched profile
page (then use that profile as source_url). Don't open hundreds of profiles: titles and
lab links for the top candidates will be completed in a later step.

Validate:  python3 stage1/validate.py data/stage1/programs/<program_id>.json
