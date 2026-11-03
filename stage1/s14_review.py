"""Human-readable stage-1 review sheet (stage1_review.md) generated from data.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"program_url": "项目主页", "deadline": "申请截止", "priority_deadline": "奖学金/优先截止",
         "application_fee": "申请费", "fee_waiver": "申请费减免", "gre_policy": "GRE", "letters_required": "推荐信数",
         "application_system_url": "网申系统", "admissions_mode": "招生模式", "contact_faculty_advice": "是否建议提前联系老师",
         "stipend": "Stipend", "guaranteed_years": "保证资助", "pr_domestic": "永久居民按 domestic",
         "t32_citizen_pr_only": "T32 等仅限公民/PR 的训练基金"}
TLABEL = {"waiver_conditions": "豁免条件", "waiver_basis": "豁免依据", "us_degree_waives": "美国学位可豁免",
          "pr_exempt": "PR 身份可豁免", "min_total": "总分要求", "min_subscores": "单项要求", "validity_rule": "有效期",
          "di_code": "DI code", "self_report_accepted": "接受自报分数"}


def cell(f):
    if not f:
        return "—", ""
    if f.get("value") is None:
        return "**null**", (f.get("note") or "")[:160]
    v = str(f["value"]).replace("|", "/")
    src = f"[来源]({f['source_url']})" + (f" ({f.get('scope')})" if f.get("scope") else "")
    if f.get("cycle"):
        src += f" · cycle: {f['cycle']}"
    return v[:180], src


def main():
    d = json.load(open(ROOT / "data.json"))
    L = ["# 第 1 阶段试点：人工核对表", "",
         f"生成于 {d['generated_at']}。每个值都来自实际抓取的页面（validator 已逐条核对引文在页面中存在）；"
         "null 表示官网可访问页面上没找到，或页面拒绝自动访问（见说明）。", ""]
    for p in d["programs"]:
        s = d["schools"][p["school_id"]]
        L += [f"## {p['school']} — {p['name']}", "",
              f"* 方向 {'+'.join(p['directions'])} · 类型 {p['program_type']} · 排名 {p['ranking']['subject']} "
              f"#{p['ranking']['rank']}（{'估计' if p['ranking']['source'] == 'estimate' else '有来源'}）"
              f" · 坐标 {s['lat']}, {s['lng']}（OpenAlex geo）"
              + (" · **直接进组：需提前联系老师**" if p["direct_admission"] else ""), "",
              "| 字段 | 值 | 来源 / 说明 |", "|---|---|---|"]
        for k, lab in LABEL.items():
            v, src = cell(p["fields"].get(k))
            L.append(f"| {lab} | {v} | {src} |")
        for k, lab in TLABEL.items():
            v, src = cell((p.get("toefl") or {}).get(k))
            L.append(f"| 托福·{lab} | {v} | {src} |")
        L += ["", f"推荐老师（{len(p['faculty'])} 位，从 {p['n_faculty_scored']} 位项目老师中按近 3 年论文相关度筛出并人工复核）：", ""]
        for x in p["faculty"]:
            tags = []
            if x["affiliation"]["status"] == "possibly_moved":
                tags.append("⚠️可能已换单位")
            if (x.get("new_assistant_professor") or {}).get("value"):
                tags.append("🆕新开组助理教授")
            title = (x.get("title") or {}).get("value") or "职称未在官网找到"
            lab = (x.get("lab_url") or {}).get("value")
            L.append(f"* **{x['name']}**（{x['direction']}）— {title}" + (f" · [实验室]({lab})" if lab else "")
                     + (" · " + " ".join(tags) if tags else ""))
            L.append(f"  * 为什么相关：{(x.get('why') or {}).get('text')}")
            for w in x["papers"]:
                L.append(f"  * {w['year']} · [{w['title']}]({w['url']})")
            if x["affiliation"]["status"] == "possibly_moved":
                rw = x["affiliation"].get("recent_works") or []
                L.append("  * 最近论文署名机构：" + "; ".join(f"{w['date']} {', '.join(w['institutions']) or '无'}" for w in rw))
        if p.get("problems"):
            L += ["", "<details><summary>抓取问题</summary>", ""] + [f"* {q}" for q in p["problems"]] + ["", "</details>"]
        L.append("")
    (ROOT / "stage1_review.md").write_text("\n".join(L) + "\n")
    print("wrote stage1_review.md")


if __name__ == "__main__":
    main()
