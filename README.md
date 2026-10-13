# Promoter critical mass and initial energy in an agent-based model of positive and negative word of mouth

Replication package for the article *Promoter critical mass and initial energy in an agent-based model of positive and negative word of mouth* (manuscript under review).

**Authors:** Ever Carpio-Meza (corresponding author, ORCID [0009-0008-3245-0416](https://orcid.org/0009-0008-3245-0416)), Joaquín Tahta and Alejandro Peláez-Arango.

## About the model

A theoretical agent-based model, written in Python with the standard library only, in which 600 agents in six communities buy a product after receiving word-of-mouth messages. Promoters and detractors arise from customer experience, and communication depletes energy and eligible contacts. The model examines whether the minimum number of promoters needed to start sustained diffusion is a fixed share or depends on initial promoter energy and on the weight of negative word of mouth. It is not calibrated to an observed market.

The complete model description, following the ODD protocol, is in `docs/Article_8_Supplementary_S1_ODD.docx` (Supplementary Material S1 of the article).

## Contents

| Folder | Contents |
|---|---|
| `code/stage1_pilot/` | Code for Stage 1: exploratory sweep from 0% to 30% of initial customers (150 runs, seeds 810001–810010) |
| `code/stage2_refined/` | Code for Stage 2: zero to three initial promoters (400 runs, seeds 820001–820100) |
| `code/stage3_energy_wom/` | Code for Stage 3, the main factorial: 1 or 2 promoters × initial energy 0.3, 0.6, 0.9 × negative weight λ 0, 1, 2 (1,800 runs, seeds 830001–830100), including the frozen simulation engine, tests and analysis scripts |
| `docs/specification/` | Model specification, Python addendum and scope notes of modules M2 to M6 |
| `docs/design/` | Experimental design of each stage |
| `docs/verification/` | Verification reports of modules M1 to M6 |
| `docs/reports/` | Analysis reports and indexes of each stage |
| `results/` | Processed results of Stages 1 and 2, and figures of the three stages |

Internal working documents in `docs/` are written in Spanish. The ODD supplement and this README are in English.

The processed results of Stage 3 (`Article_8_Energia_WOM_Resultados_v0.3.0.zip`, 43 MB) are attached to the [v1.0 release](https://github.com/EverCarpio/article8-wom-critical-mass/releases). The complete agent-level traces of all runs (about 4 GB) are not included because of their size; they are available from the corresponding author upon reasonable request.

## Reproducing Stage 3

Requirements: Python 3.11 or later (verified with Python 3.12.14). The engine uses only the standard library; analysis and figures use NumPy and Matplotlib.

From `code/stage3_energy_wom/`:

```bash
python -m pip install -r requirements-analysis.txt
python -m unittest discover -s tests -v
python scripts/run_energy_wom.py --out /tmp/article8_energy_wom_replication --prepare-only
python scripts/run_energy_wom.py --out /tmp/article8_energy_wom_replication --workers 8
python scripts/analyze_energy_wom.py --source /tmp/article8_energy_wom_replication --out /tmp/article8_energy_wom_analysis
python scripts/plot_energy_wom.py --source /tmp/article8_energy_wom_analysis --out /tmp/article8_energy_wom_figures
```

A full run needs about 3–4 GB of free disk space. Do not modify the engine files: `model/SOURCE_SHA256.json` records their checksums. The README inside each `code/` folder gives the complete instructions for its stage.

## License

The code is released under the MIT License. See `LICENSE`.

## Contact

Ever Carpio-Meza, Universidad Nacional de Colombia, Sede De La Paz, ecarpio@unal.edu.co
