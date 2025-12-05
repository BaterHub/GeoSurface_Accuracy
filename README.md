# GeoSurface Accuracy

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Release](https://img.shields.io/badge/version-0.2.0-blue)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/BaterHub/GeoSurface_Accuracy/blob/main/GeoSurface_Accuracy.ipynb)

Notebook and utilities to estimate horizontal confidence of geological surfaces in GOCAD (.ts) format, using wells and sections (shapefiles) with ID weights = 1/(1 + r^p) normalized (IDW) on an evaluation grid. Optional vertical confidence maps are produced when checkpoints carry Z values.

## Features
- Read multi-surface .ts files and build a grid (configurable step, clipped on hull).
- IDW computation by constraint order (wells=1, sections=2, maps=3) and final averaging.
- Constraint mapping per surface via edge list (`surface_checkpoint_edges.csv`) and flags (`surface_data_mapping.csv`).
- Per-surface outputs: grid CSV, heatmap PNG, interactive HTML, distance histogram, `model_dataset_<surface>.png`.
- Project-level output: `model_dataset.png` with model footprint and data.

## Requirements
- Python 3.10+
- pandas, geopandas, numpy, matplotlib, scipy, scikit-learn, pyproj, plotly

Install with:
```bash
pip install -r requirements.txt
```

## Essential structure
- `GeoSurface_Accuracy.ipynb` — main notebook.
- `files_utils.py` — functions (read .ts, IDW, plot).
- `working_files_folder/`
  - `horizons.ts` (all surface geometries)
  - `pozzi_idrocarburi.*` (field `NOME_POZZO`)
  - `linee_sismiche.*` (field `NOME`)
  - `surface_data_mapping.csv` — flags per surface: `surface,use_wells,use_sections,use_maps,use_vertical` (1/0).
  - `surface_checkpoint_edges.csv` — edge list `surface,checkpoint_id,type` (`type`: well/section/map; `checkpoint_id` must match `NOME_POZZO`/`NOME`; use `ALL` to include every item).
  - (Optional, vertical) `surface_checkpoint_depths_wells.csv` — `surface,checkpoint_id,z,unit,datum,method,date`.
  - (Optional, vertical) `surface_checkpoint_depths_sections.csv` — `surface,checkpoint_id,x,y,z,unit,datum,method,date`.
  - `output_results/` — generated PNG/CSV/HTML.

## Local use
```bash
git clone https://github.com/BaterHub/GeoSurface_Accuracy.git
cd GeoSurface_Accuracy
pip install -r requirements.txt
jupyter notebook GeoSurface_Accuracy.ipynb
```
Populate `working_files_folder` with the .ts file, shapefiles, and mapping CSVs, then run the notebook (skip the Colab cloning cell).

## Use on Colab
1. Open the Colab badge.
2. Run the “LOAD WORKSPACE” cell (clones the repo).
3. Upload data and CSVs to `working_files_folder`.
4. Run starting from the “RUN THE SCRIPT” cell. Outputs go to `output_results`.

## Mapping notes
- `surface_data_mapping.csv`: per-surface toggles for wells/sections/maps and vertical processing (1/0). `use_vertical` enables vertical confidence when checkpoints have Z values (via geometry or the depth CSVs).
- `surface_checkpoint_edges.csv`: many-to-many surface–checkpoint edge list. Columns: `surface,checkpoint_id,type` where `type` is `well`/`section`/`map` and `checkpoint_id` matches `NOME_POZZO` or `NOME`; `ALL` includes all checkpoints of that type.
- Optional depth CSVs let you provide Z per surface and checkpoint (`surface_checkpoint_depths_wells.csv`, `surface_checkpoint_depths_sections.csv`); if present, they are used to build vertical confidence maps.

## Outputs
- Per surface (horizontal confidence): `model_dataset_<surface>.png`, `horizontal_confidence_grid_<surface>.csv`, `horizontal_confidence_idw_<surface>.png` (0–1 scale), `horizontal_confidence_rank_<surface>.png`, `interactive_confidence_<surface>.html`, `distance_histogram_<surface>.png`.
- Per surface (vertical confidence, when checkpoints have Z): `vertical_confidence_grid_<surface>.csv` (includes `abs_delta_z` and `abs_delta_norm`), `vertical_deltaZ_norm_<surface>.png`, `vertical_deltaZ_<surface>.html`.
- Whole model: `model_dataset.png` (global extent includes surfaces + wells + sections).
