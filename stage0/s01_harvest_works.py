"""0.1a  Harvest OpenAlex works for each subtopic (A and B harvested separately).

Output: data/stage0/works_A.jsonl, data/stage0/works_B.jsonl
Each line = one work with the subtopics/queries that matched it plus the
OpenAlex page URL it came from and the fetch timestamp.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import openalex as oa  # noqa: E402
from stage0.queries import SUBTOPICS, BASE_FILTER  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "stage0"
OUT.mkdir(parents=True, exist_ok=True)
SELECT = ("id,doi,title,publication_year,publication_date,type,authorships,"
          "primary_location,abstract_inverted_index,cited_by_count,corresponding_author_ids")


def main():
    for direction in ("A", "B"):
        works = {}
        for sub, cfg in SUBTOPICS.items():
            if cfg["direction"] != direction:
                continue
            for qi, q in enumerate(cfg["queries"]):
                n = 0
                for w, url, at in oa.paginate("/works", select=SELECT,
                                              filter=BASE_FILTER + ",title_and_abstract.search:" + q):
                    rec = works.setdefault(w["id"], {**w, "matched": [], "source_urls": []})
                    tag = f"{sub}#{qi}"
                    if tag not in rec["matched"]:
                        rec["matched"].append(tag)
                    rec.setdefault("fetched_at", at)
                    if url not in rec["source_urls"]:
                        rec["source_urls"].append(url)
                    n += 1
                print(direction, sub, qi, n, flush=True)
        path = OUT / f"works_{direction}.jsonl"
        with open(path, "w") as f:
            for w in works.values():
                f.write(json.dumps(w) + "\n")
        print("wrote", path, len(works), flush=True)


if __name__ == "__main__":
    main()
