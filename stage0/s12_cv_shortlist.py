"""15-school shortlist fitted to the applicant's CV (direction A1/A2 thesis) and math
background (calculus I-II, multivariable calculus, linear algebra; no real analysis /
probability theory / CS sequence).  Programs whose official pages REQUIRE something the
applicant lacks are dropped (data/stage0/math_fit.json); the list is refilled by CV fit.
Writes shortlist_15.md and sets candidates.csv selected=1 (selected_by=claude-cv-math-fit)
for the 15 primary programs, clearing earlier claude-recommended selections.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MF = json.load(open(ROOT / "data" / "stage0" / "math_fit.json"))
LIST = [  # (school, program prefix in candidates.csv, prereq key, anchor faculty, alternatives)
    ("University of Pennsylvania", "Genomics and Computational Biology", "penn-gcb",
     "Hongzhe Li, Brielin Brown (inspre), Eugene Katsevich", "Biostatistics PhD (penn-biostat)"),
    ("University of Wisconsin–Madison", "PhD in Biomedical Data Science", "wisc-bmds",
     "Sündüz Keleş, Qiongshi Lu, Anthony Gitter", "PhD Statistics, Biostatistics Option (wisc-stat)"),
    ("Massachusetts Institute of Technology", "Computational and Systems Biology", "mit-csb",
     "Caroline Uhler, Bonnie Berger", ""),
    ("Stanford University", "Genetics (Stanford Biosciences", "stanford-genetics",
     "Jonathan Pritchard, Livnat Jerby-Arnon, Stephen Montgomery", ""),
    ("Yale University", "Computational Biology and Biomedical Informatics", "yale-cbb",
     "Hongyu Zhao, Smita Krishnaswamy, María Rodríguez Martínez", "Human Genome Sciences track (yale-hgs)"),
    ("Columbia University", "Biomedical Life Sciences PhD - Systems Biology", "columbia-sysbio",
     "David Knowles (inspre), Andrea Califano", "PhD in Biomedical Informatics (columbia-dbmi)"),
    ("Carnegie Mellon University", "Joint Carnegie Mellon-University of Pittsburgh", "cmu-pitt-cpcb",
     "Jian Ma, Kathryn Roeder, Jishnu Das", "Ph.D. Program in Machine Learning (cmu-ml)"),
    ("University of Pittsburgh", "PhD Program in Biomedical Informatics", "pitt-dbmi",
     "Eric Strobl, Xinghua Lu", ""),
    ("University of California San Diego", "Bioinformatics and Systems Biology", "ucsd-bisb",
     "Hannah Carter, Prashant Mali, Melissa Gymrek", ""),
    ("Vanderbilt University", "Human Genetics PhD Program", "vanderbilt-hgen",
     "Eric Gamazon, Nancy Cox, Bingshan Li", "IGP / QCB umbrella (vanderbilt-igp)"),
    ("New York University", "PhD in Biomedical Sciences - Computational", "nyu-compbio",
     "Rahul Satija, Aristotelis Tsirigos", ""),
    ("University of North Carolina at Chapel Hill", "Biostatistics PhD (Gillings", "unc-biostat",
     "Yun Li, Xihao Li, Danyu Lin", "Bioinformatics and Computational Biology (unc-bcb)"),
    ("Emory University", "Biostatistics", "emory-biostat",
     "Chang Su (thesis advisor)", ""),
    ("University of California, Los Angeles", "Human Genetics PhD", "ucla-hg",
     "Sriram Sankararaman, Noah Zaitlen, Harold Pimentel", "Biomathematics PhD (ucla-biomath)"),
    ("University of Chicago", "Committee on Genetics, Genomics", "uchicago-ggsb",
     "Matthew Stephens, Xin He, Hae Kyung Im, Xuanyao Liu", ""),
]
DROPPED = ["stanford-bmds", "uw-biostat", "cornell-tricbm", "duke-cbb"]
TOPIC_ZH = {"real_analysis": "实分析（强烈建议）", "probability": "概率论", "differential_equations": "微分方程",
            "other:data_structures": "数据结构", "other:algorithms": "算法",
            "other:data_structures_and_algorithms": "数据结构与算法", "other:data_structures_algorithms": "数据结构与算法",
            "other:discrete_mathematics": "离散数学", "other:quantitative_science": "偏好有量化学科背景",
            "other:quantitative_undergraduate_degree": "典型背景是量化专业本科",
            "other:mathematics_unspecified": "更多数学课", "other:multilinear_algebra": "多重线性代数",
            "other:numerical_analysis": "数值分析", "other:cs_coursework_one_year": "一年计算机专业课",
            "other:quantitative_degree": "量化专业学位", "mathematical_statistics": "数理统计",
            "other:advanced_mathematics": "进阶数学课"}
ZH = {"met": "满足", "not_stated": "官网未列数学要求", "recommended_unmet": "满足必修；有建议项未满足",
      "uncertain": "需确认", "unverifiable": "官网拒绝访问，无法核实", "required_unmet": "不满足必修"}


def main():
    rows = list(csv.DictReader(open(ROOT / "candidates.csv")))
    for r in rows:
        if (r.get("selected_by") or "").startswith("claude"):
            r["selected"], r["selected_by"] = "", ""
    L = ["# 15 所学校短名单（按 CV 契合度 + 数学先修）", "",
         "数学背景：两门基础微积分、多元微积分、线性代数（无实分析、无概率论、无计算机专业课序列）。"
         "每条要求都引自官网页面（见 data/stage0/prereqs/*.json）。", "",
         "| # | 学校 | 项目 | 数学要求 | 需留意 | 和你论文方向相关的老师 | 备选项目 |", "|---|---|---|---|---|---|---|"]
    for i, (school, pref, key, fac, alt) in enumerate(LIST, 1):
        mf = MF.get(key, {})
        st = mf.get("status", "unverifiable")
        flag = "、".join(dict.fromkeys(TOPIC_ZH.get(t, t) for t in
                                       mf.get("missing_recommended", []) + mf.get("missing_required", [])))
        hit = [r for r in rows if r["school"] == school and r["program"].startswith(pref)]
        prog = hit[0]["program"] if hit else pref
        for r in hit[:1]:
            r["selected"], r["selected_by"] = "1", "claude-cv-math-fit"
        L.append(f"| {i} | {school} | {prog[:60]} | {ZH.get(st, st)} | {flag or '—'} | {fac} | {alt or '—'} |")
    L += ["", "## 剔除（官网写明必修，而你没有）", ""]
    for k in DROPPED:
        mf = MF.get(k, {})
        L.append(f"* {mf.get('school')} — {mf.get('program')}: 缺 "
                 f"{'、'.join(TOPIC_ZH.get(t, t) for t in mf.get('missing_required', []))}")
        for kind, q, src in mf.get("quotes", []):
            if kind == "required":
                L.append(f"  * 原文：“{q[:220]}” ([来源]({src}))")
    cols = list(rows[0].keys())
    with open(ROOT / "candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    (ROOT / "shortlist_15.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("selected rows:", sum(1 for r in rows if r.get("selected") == "1"))


if __name__ == "__main__":
    main()
