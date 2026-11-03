"""OpenAlex title_and_abstract.search queries for the six research interests.

Direction A (statistical / computational genomics) and B (computational protein
design & structure) are harvested separately.  Each subtopic is the union of
several boolean queries.  Works are restricted to publication_year >= 2022,
at least one US-affiliated author, type article|preprint|review.
"""

BASE_FILTER = ("publication_year:>2021,authorships.institutions.country_code:US,"
               "type:article|preprint|review")

COMP = ('("machine learning" OR "deep learning" OR computational OR "language model" '
        'OR "in silico" OR generative OR algorithm OR "neural network")')

SUBTOPICS = {
    # ---------------------------------------------------------------- A
    "A1_perturbseq": {
        "direction": "A",
        "label": "Single-cell CRISPR screens / Perturb-seq computational methods",
        "queries": [
            '"Perturb-seq" OR "Perturbseq" OR "CROP-seq" OR "CRISP-seq" OR "Mosaic-seq" '
            'OR "TAP-seq" OR "ECCITE-seq" OR "Perturb-ATAC" OR "Perturb-CITE-seq"',
            '"single-cell CRISPR screen" OR "single-cell CRISPR screens" OR '
            '"single cell CRISPR screen" OR "single cell CRISPR screens" OR '
            '"single-cell perturbation screen" OR "single-cell perturbation screens" OR '
            '"single-cell genetic screen" OR "single-cell genetic screens"',
            '("perturbation response" OR "perturbation effects" OR "perturbation prediction" '
            'OR "genetic perturbation" OR "genetic perturbations") AND ("single-cell" OR "single cell") '
            'AND (predict OR prediction OR model OR "deep learning" OR "machine learning" OR computational)',
        ],
    },
    "A2_causal_network": {
        "direction": "A",
        "label": "Causal network inference (gene or trait level)",
        "queries": [
            '("causal network" OR "causal networks" OR "causal discovery" OR "causal graph" '
            'OR "causal graphs" OR "structural causal model" OR "directed acyclic graph") AND '
            '(gene OR genes OR genetic OR genomic OR transcriptomic OR "gene expression" OR trait OR traits)',
            '"gene regulatory network inference" OR "regulatory network inference" OR '
            '"inferring gene regulatory networks" OR "causal gene regulatory network" OR '
            '"causal gene network"',
            '("Mendelian randomization" OR "genetic instruments") AND (network OR "causal graph" '
            'OR "causal structure" OR multivariable) AND (traits OR phenotypes)',
        ],
    },
    "A3_statgen": {
        "direction": "A",
        "label": "Statistical genetics: GWAS summary statistics, MR, polygenic scores",
        "queries": [
            '"GWAS summary statistics" OR "summary statistics from genome-wide" OR '
            '"summary-level GWAS" OR "summary-level data" OR "summary statistics-based"',
            '"Mendelian randomization" AND ("we propose" OR "we develop" OR "we introduce" OR '
            '"we present" OR estimator OR "novel method" OR "new method" OR "statistical method" '
            'OR robust OR pleiotropy)',
            '("polygenic score" OR "polygenic scores" OR "polygenic risk score" OR '
            '"polygenic risk scores" OR "polygenic prediction") AND ("we propose" OR "we develop" '
            'OR "we introduce" OR "we present" OR method OR methods OR "cross-ancestry" OR '
            '"multi-ancestry" OR portability OR Bayesian)',
            '("fine-mapping" OR "fine mapping" OR "genetic correlation" OR "SNP heritability" OR '
            '"transcriptome-wide association" OR "colocalization") AND (GWAS OR "genome-wide") '
            'AND (method OR methods OR statistical OR "we propose" OR "we develop")',
        ],
    },
    # ---------------------------------------------------------------- B
    "B4_antibody": {
        "direction": "B",
        "label": "Computational antibody affinity maturation / optimization",
        "queries": [
            '(antibody OR antibodies OR nanobody OR nanobodies OR VHH) AND ("affinity maturation" '
            'OR "affinity optimization" OR "antibody optimization" OR "antibody design" OR '
            '"antibody engineering" OR "binding affinity") AND ' + COMP,
            '"antibody language model" OR "antibody language models" OR "antibody design" '
            'OR "de novo antibody" OR "computational antibody" OR "antibody structure prediction"',
        ],
    },
    "B5_denovo_design": {
        "direction": "B",
        "label": "De novo protein generation (diffusion, PLMs, sequence-structure co-design)",
        "queries": [
            '("protein design" OR "protein generation" OR "protein engineering" OR '
            '"de novo protein" OR "de novo proteins" OR "binder design") AND (diffusion OR '
            'generative OR "language model" OR "deep learning" OR "flow matching")',
            '"protein language model" OR "protein language models" OR "inverse folding" OR '
            '"de novo designed proteins" OR "de novo protein design" OR "de novo binder" OR '
            '"de novo binders"',
            '("sequence-structure co-design" OR "sequence and structure co-design" OR '
            '"joint sequence-structure" OR "co-design") AND protein',
        ],
    },
    "B6_structure_pred": {
        "direction": "B",
        "label": "Protein structure prediction incl. complexes / PPI interfaces",
        "queries": [
            '"protein structure prediction" OR "structure prediction of protein" OR '
            '"protein complex structure prediction" OR "complex structure prediction" OR '
            '"multimer prediction"',
            '("protein-protein interaction" OR "protein-protein interactions" OR '
            '"protein–protein interaction" OR "protein interface" OR "binding interface" OR '
            '"protein docking" OR "protein complex" OR "protein complexes") AND '
            '("structure prediction" OR AlphaFold OR "deep learning" OR docking)',
            '(AlphaFold OR AlphaFold2 OR AlphaFold3 OR RoseTTAFold OR ESMFold) AND '
            '("we propose" OR "we develop" OR "we introduce" OR "we present" OR benchmark OR '
            'improve OR accuracy)',
        ],
    },
}
