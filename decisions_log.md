# Decisions log

Recommended decisions applied by Claude under the user's delegation (“接下来全按你推荐的来”, 2026-11-03). Anything set by hand in whitelist.csv, unresolved.csv (keep / user_rank) or user_discipline_map.json takes precedence; re-run `python3 stage0/s07_candidates.py` after editing.

## Ranking-table mapping for program types without a table (user_discipline_map.json)

* `biochemistry` -> `biological_sciences`
* `other:applied_life_sciences` -> `biological_sciences`
* `other:applied_mathematics` -> `computer_science`
* `other:biological_sciences` -> `biological_sciences`
* `other:biology` -> `biological_sciences`
* `other:cancer_biology` -> `biological_sciences`
* `other:cell_molecular_biology` -> `biological_sciences`
* `other:chemical_biological_engineering` -> `biological_sciences`
* `other:chemical_biomolecular_engineering` -> `chemistry`
* `other:chemical_engineering` -> `chemistry`
* `other:clinical_translational_science` -> `biological_sciences`
* `other:computational_science_engineering` -> `computer_science`
* `other:data_science` -> `computer_science`
* `other:electrical_computer_engineering` -> `computer_science`
* `other:epidemiology` -> `biostatistics`
* `other:health_ai` -> `computer_science`
* `other:immunology` -> `biological_sciences`
* `other:materials_science` -> `chemistry`
* `other:mathematical_sciences` -> `computer_science`
* `other:microbiology` -> `biological_sciences`
* `other:molecular_biology` -> `biological_sciences`
* `other:molecular_cell_biology` -> `biological_sciences`
* `other:molecular_cellular_biology` -> `biological_sciences`
* `other:molecular_engineering` -> `biomedical_engineering`
* `other:neuroscience` -> `biological_sciences`
* `other:pharmaceutical_sciences` -> `biological_sciences`
* `other:pharmacology` -> `biological_sciences`
* `other:physiology` -> `biological_sciences`
* `other:physiology_pharmacology` -> `biological_sciences`

## Biostatistics

* biostatistics programs use rankings/biostatistics.csv (U.S. News 2026 ranks biostatistics separately from statistics)

## Whitelist (independent institutes)

rule: confirm=1 if a PhD program was verified on a fetched page and >=1 core relevant faculty matched

* Cedars-Sinai Medical Center: confirm=1 (4 core relevant faculty)
* City of Hope: confirm=0 (0 core relevant faculty)
* Keck Graduate Institute: confirm=1 (1 core relevant faculty)
* Mayo Clinic: confirm=0 (0 core relevant faculty)
* Memorial Sloan Kettering Cancer Center: confirm=1 (5 core relevant faculty)
* Sanford Burnham Prebys Medical Discovery Institute: confirm=0 (0 core relevant faculty)
* St. Jude Children's Research Hospital: confirm=1 (3 core relevant faculty)
* Stowers Institute for Medical Research: confirm=0 (0 core relevant faculty)
* The University of Texas MD Anderson Cancer Center: confirm=1 (4 core relevant faculty)
* The University of Texas Southwestern Medical Center: confirm=1 (2 core relevant faculty)
* Toyota Technological Institute at Chicago: confirm=1 (1 core relevant faculty)
* University of Nebraska Medical Center: confirm=1 (2 core relevant faculty)

## Unresolved items

rules: program types with no table -> keep if >=2 relevant faculty; unreadable schools -> keep (placeholder row) if >=10 core OpenAlex authors; name-only resemblance -> drop

* Albert Einstein College of Medicine / (no program verified): keep=0  [decided]
* Carnegie Mellon University / Ph.D. in Mechanical Engineering: keep=0  [decided]
* Icahn School of Medicine at Mount Sinai / (no program verified): keep=1  [decided]
* Kansas State University / Grain Science graduate program (Department of Grain and Food Science): keep=0  [decided]
* Massachusetts Institute of Technology / Media Arts and Sciences PhD: keep=0  [decided]
* Massachusetts Institute of Technology / Civil and Environmental Engineering PhD: keep=0  [decided]
* Philadelphia University / (no program verified): keep=0  [decided]
* Purdue University West Lafayette / Animal Sciences PhD: keep=0  [decided]
* The University of Texas at Austin / Ecology, Evolution, and Behavior (EEB) PhD: keep=1  [decided]
* University of California, Berkeley / Computational Precision Health PhD (joint UC Berkeley-UCSF): keep=1  [decided]
* University of California, Santa Barbara / Ecology, Evolution and Marine Biology (EEMB) PhD: keep=0  [decided]
* University of Central Florida / Ph.D. in Computer Engineering: keep=0  [decided]
* University of Michigan / (no program verified): keep=1  [decided]
* University of Nebraska–Lincoln / Agronomy and Horticulture (PHD): keep=0  [decided]
* Miami University / (not enumerated): keep=0  [decided]

## Recommended shortlist (candidates.csv selected=1)

rule: >=5 relevant faculty, or >=4 with subject rank <=25; max 2 programs per school; pilot programs always included

* University of Pennsylvania / Genomics and Computational Biology (GCB) Graduate Group (A+B, biological_sciences #16, 18 relevant faculty) [pilot]
* Yale University / Computational Biology and Biomedical Informatics (CBB) track, BBS (A+B, biological_sciences #10, 10 relevant faculty) [pilot]
* Stanford University / Biophysics (Stanford Biosciences Home Program) (A+B, biological_sciences #3, 10 relevant faculty) [pilot]
* Stanford University / Biomedical Data Science (Stanford Biosciences Home Program) (A+B, biological_sciences #3, 10 relevant faculty)
* University of California San Diego / Bioinformatics and Systems Biology Graduate Program (BISB / BMI tracks (A+B, biological_sciences #13, 9 relevant faculty)
* Vanderbilt University / Interdisciplinary Graduate Pathway / Quantitative and Chemical Biology (A+B, biological_sciences #26, 9 relevant faculty)
* Massachusetts Institute of Technology / Computational and Systems Biology PhD Program (CSB) (A+B, biological_sciences #1, 8 relevant faculty)
* University of California, Berkeley / UC Berkeley-UCSF Graduate Program in Bioengineering (joint PhD) (A+B, biomedical_engineering #8, 8 relevant faculty)
* Vanderbilt University / Human Genetics PhD Program (HGEN) (A+B, biological_sciences #26, 8 relevant faculty)
* University of Chicago / Committee on Genetics, Genomics & Systems Biology (GGSB) - PhD in Gene (A, biological_sciences #16, 7 relevant faculty)
* University of Pennsylvania / Bioengineering PhD (A+B, biomedical_engineering #6, 7 relevant faculty)
* University of California, Berkeley / Computational Biology PhD (Center for Computational Biology) (A+B, biological_sciences #3, 7 relevant faculty)
* University of Pittsburgh / Joint Carnegie Mellon-University of Pittsburgh Ph.D. Program in Comput (A+B, biological_sciences #46, 6 relevant faculty)
* Cornell University / Tri-Institutional PhD Program in Computational Biology & Medicine (CBM (A+B, biological_sciences #16, 6 relevant faculty)
* University of Chicago / Graduate Program in Biophysical Sciences (A+B, biological_sciences #16, 6 relevant faculty)
* Yale University / Human Genome Sciences (HGS) track, BBS (A+B, biological_sciences #10, 6 relevant faculty)
* University of California, Los Angeles / Human Genetics PhD (A, biological_sciences #21, 6 relevant faculty)
* University of Washington / Biological Physics, Structure and Design (BPSD) (B, biological_sciences #16, 6 relevant faculty) [pilot]
* New York University / PhD in Biomedical Sciences - Computational Biology and Bioinformatics  (A+B, biological_sciences #35, 5 relevant faculty)
* California Institute of Technology / Biology (Bi) PhD option (A+B, biological_sciences #7, 5 relevant faculty)
* Columbia University / Biomedical Life Sciences PhD - Systems Biology track (A+B, biological_sciences #13, 5 relevant faculty)
* Memorial Sloan Kettering Cancer Center / Tri-Institutional PhD Program in Computational Biology & Medicine (CBM (A+B, biological_sciences #whitelist, 5 relevant faculty)
* Indiana University / Medical and Molecular Genetics PhD (IU School of Medicine, Indianapoli (A, biological_sciences #50, 5 relevant faculty)
* University of North Carolina at Chapel Hill / Biostatistics PhD (Gillings School of Global Public Health) (A, biostatistics #4, 4 relevant faculty) [pilot]
* Boston University / PhD in Biostatistics (A, biostatistics #17, 4 relevant faculty)
* University of California, Los Angeles / Biomathematics PhD (Department of Computational Medicine) (A, biological_sciences #21, 4 relevant faculty)
* University of Illinois Urbana-Champaign / Biophysics and Quantitative Biology PhD (Center for Biophysics and Qua (B, biological_sciences #12, 4 relevant faculty)
* University of Illinois Urbana-Champaign / Ph.D. in Bioengineering (B, biomedical_engineering #17, 4 relevant faculty)
* Scripps Research Institute / Doctoral Program in Chemical and Biological Sciences (Skaggs Graduate  (A+B, biological_sciences #1, 4 relevant faculty)
* University of California San Diego / Bioengineering PhD (A+B, biomedical_engineering #4, 4 relevant faculty)
* Massachusetts Institute of Technology / Biological Engineering PhD (B, biomedical_engineering #3, 3 relevant faculty)
* Harvard University / Biomedical Informatics PhD - Bioinformatics and Integrative Genomics ( (A+B, biological_sciences #3, 3 relevant faculty)
* Johns Hopkins University / Human Genetics and Genomics, PhD (A, biological_sciences #7, 0 relevant faculty)
* Columbia University / PhD in Biostatistics (Mailman School of Public Health) (A+B, biostatistics #8, 2 relevant faculty)
* University of Washington / Biostatistics PhD (A, biostatistics #3, 1 relevant faculty)
* Duke University / Biomedical Engineering PhD (B, biomedical_engineering #6, 1 relevant faculty)
* University of California, San Francisco / Biological and Medical Informatics (BMI) (A+B, biological_sciences #7, 0 relevant faculty)

## 2026-11-06 — user: 15-school shortlist (shortlist_15.md)

* user declined: University of Pittsburgh — PhD Program in Biomedical Informatics; UNC Chapel Hill — Biostatistics PhD (selected=0, selected_by=user-declined; never re-selected automatically)
* replaced by CV fit among math-checked programs at new schools: Indiana University — Medical and Molecular Genetics PhD; Caltech — Biology (Bi) PhD option (next: UW Genome Sciences)
