# Theory Overview: Horizontal Accuracy Proxy for GOCAD Surfaces

## Goal
Estimate a relative horizontal accuracy (constraint strength) for each surface in a GOCAD `.ts` model by combining proximity to wells (points) and sections (lines). Outputs are per-surface grids/maps plus a model-wide footprint.

## Inputs
- Multi-surface GOCAD `.ts` file (vertices/triangles).
- Well shapefiles (points) and section shapefiles (lines), with optional per-surface toggles (`surface_data_mapping.csv`) and edge lists (`surface_checkpoint_edges.csv`) to include/exclude controls.
- Config params: grid spacing (m), line sampling step (m), IDW exponents.

## Method
1. **Grid + hull**: Build a 2D evaluation grid (user spacing) clipped to the convex hull of the surface footprint to limit computations to the model extent.
2. **Sample controls**: Use well coordinates directly; resample sections along lines at a fixed step to get dense points.
3. **Distance to weights**: For each grid node, compute nearest distance to wells and to sections. Convert distance `r` (km) to inverse-distance weight `ID = 1/(1 + r^p)`, then min–max normalize per control type. Default exponents: wells `p=1` (faster decay), sections `p=2` (slower).
4. **Combine**: Average available normalized weights (wells, sections) to get a combined horizontal-accuracy proxy; if only one control type exists, use that weight alone.

## Outputs (per surface)
- CSV: grid XY, distances to wells/sections, weights per control, combined weight.
- PNG: combined-weight heatmap (IDW).
- Histogram (PNG): distance distributions (km) by control type.
- HTML (Plotly): interactive scatter of combined weight.
- Static PNG: footprint `model_dataset_<surface>.png` with extent, wells, sections.

## Whole model
- Combined footprint PNG `model_dataset.png` showing overall extent and controls.

## Assumptions and limitations
- Nearest-distance IDW is a simple proxy; it does not model anisotropy, structural trends, or vertical accuracy.
- Quality depends on correct CRS, complete control data, sensible grid spacing and line step.
- Mapping CSVs must reflect actual IDs in shapefiles (`NOME_POZZO`, `NOME`) or use `ALL` to include everything.

## Parameter guidance
- **Grid spacing**: coarse enough for speed, fine enough to capture control density (e.g., 500–2000 m depending on model scale).
- **Line sampling step**: set similar to desired resolution of section influence (e.g., 1000–2000 m).
- **IDW exponents**: lower `p` spreads influence farther; higher `p` localizes it. Defaults (wells `p=1`, sections `p=2`) prioritize point control decay.
