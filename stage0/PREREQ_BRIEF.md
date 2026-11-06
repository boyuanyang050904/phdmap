# Brief: official math / quantitative prerequisites of PhD programs

For each program assigned to you, find what the program's OFFICIAL pages say about
mathematics (and statistics/probability/programming) coursework expected of applicants:
admission requirements, "prerequisites", "preparation", "who should apply", FAQ, or the
graduate catalog entry. Repo: /home/user/phdmap. Fetch only with the project tool:

    python3 stage0/program_tool.py fetch URL            # status + useful links
    python3 stage0/program_tool.py text  URL --grep "calculus|linear algebra|analysis|probability|mathemat|statistic|prerequisite|quantitative|background|programming"
    python3 stage0/program_tool.py find  START_URL "admission|apply|requirement|prerequisite|faq|prospective" --depth 2 --max 25

Rules (same as the rest of the project):
- Quotes must be EXACT contiguous text (10-400 chars) from a page you fetched with the tool;
  a validator re-checks them. Never from memory. Nothing found -> say so (not_stated).
- If the tool says BLOCKED / UNREACHABLE / BOT-PROTECTED, do not work around it; record it.
- WebSearch only to find URLs; at most ~15 searches in total for your whole batch.
- Program pages first; if the program states nothing, check the graduate school / umbrella
  admission requirements that apply to it, and record the scope.

Output: data/stage0/prereqs/<key>.json   (key given in your task)
{
 "key": "...", "school": "...", "program": "...", "program_url": "...", "checked_at": "<UTC>",
 "requirements": [
   {"quote": "...", "source_url": "...", "fetched_at": "...", "scope": "program|umbrella|graduate_school",
    "kind": "required|strongly_recommended|recommended|typical_background|none_stated",
    "topics": ["calculus","multivariable_calculus","linear_algebra","real_analysis",
               "probability","mathematical_statistics","statistics","differential_equations",
               "programming","other:<x>"]}
 ],
 "not_stated": true|false,          # true if no accessible official page states math expectations
 "problems": ["..."]
}
Validate: python3 stage0/validate_prereq.py data/stage0/prereqs/<key>.json
