"""Write compact, committed snapshots of large intermediate data.

* data/stage0/homes.json.gz              (relevant authors + institution roll-up)
* data/stage0/works_index.csv.gz         (every harvested work: id, doi, year, title,
                                           subtopics, methods flag, PI authors, OpenAlex page URL)
Raw OpenAlex dumps stay in the git-ignored local cache and can be regenerated.
"""
import csv, gzip, json, shutil
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from stage0.s02_authors import abstract, methods_flag  # noqa

D = ROOT / "data" / "stage0"
with open(D / "homes.json", "rb") as f, gzip.open(D / "homes.json.gz", "wb") as g:
    shutil.copyfileobj(f, g)
with gzip.open(D / "works_index.csv.gz", "wt", newline="") as g:
    w = csv.writer(g)
    w.writerow(["direction", "openalex_id", "doi", "year", "type", "title", "subtopics", "methods_flag",
                "last_or_corresponding_us_authors", "cited_by", "source_url", "fetched_at"])
    for d in "AB":
        for line in open(D / f"works_{d}.jsonl"):
            x = json.loads(line)
            pis = []
            for a in x["authorships"]:
                if (a.get("author_position") == "last" or a.get("is_corresponding")) and \
                        any(i.get("country_code") == "US" for i in a.get("institutions", [])):
                    pis.append(a["author"]["display_name"])
            w.writerow([d, x["id"], x.get("doi"), x["publication_year"], x["type"], x.get("title"),
                        ";".join(sorted({m.split("#")[0] for m in x["matched"]})),
                        int(methods_flag((x.get("title") or "") + ". " + abstract(x))),
                        "; ".join(pis), x.get("cited_by_count"), x["source_urls"][0], x["fetched_at"]])
print("ok")
