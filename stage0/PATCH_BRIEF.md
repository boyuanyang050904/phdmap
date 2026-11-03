# Patch brief: re-check sites that were blocked under the old robots policy

The fetcher's robots policy changed (user-authorised): it now honours robots.txt for our
UA, "Claude-User"/"Claude-Web" and "*", and treats a 4xx robots.txt as no restriction
(RFC 9309). Rules aimed only at the ClaudeBot training crawler no longer block us. Hosts
that are NOW ALLOWED include (relevant ones per institution are listed in your task).

For each institution assigned to you:
1. Open its existing file data/stage0/programs/<slug>.json and read `problems` and
   `unmatched_core_authors`.
2. For problems that were "BLOCKED by robots.txt" on a host that is now allowed, redo that
   step following /home/user/phdmap/stage0/PROGRAM_BRIEF.md (same hard rules: facts only
   from pages fetched with stage0/program_tool.py; quotes exact; null when unverifiable).
   Typical gains: faculty-list pages of programs that had none, missing programs, PhD
   evidence from the program's own site instead of a catalogue, profile pages for
   unmatched core authors (step 4).
3. Update the file IN PLACE: keep existing correct entries, add/replace programs,
   `faculty_list_urls`, `matched_authors`, `unmatched_core_authors`; delete problem lines
   you resolved; append one line "rechecked 2026-11-03 under Claude-User robots policy:
   <what changed>". If the host is still blocked/unreachable (the tool says BLOCKED or
   UNREACHABLE), leave the problem line.
4. Validate: python3 -c "import json;json.load(open('data/stage0/programs/<slug>.json'))"

WebSearch: at most ~5 searches per institution (budget shared by several agents);
prefer navigating from now-allowed official pages with `fetch` and `find`.
Tool tip: put `--grep REGEX` last; it is already case-insensitive (don't pass -i).
