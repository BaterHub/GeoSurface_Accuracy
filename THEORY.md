# Theory Overview: Horizontal & Vertical Confidence for GOCAD Surfaces

## Goal
Estimate per-surface confidence maps for a GOCAD `.ts` model:
- **Horizontal confidence**: proxy from control density (wells/sections) via nearest-distance IDW.
- **Vertical confidence**: absolute residual maps when checkpoints carry Z (|dZ| between checkpoints and surface) with a normalized version.

## Inputs
- Multi-surface GOCAD `.ts` file (vertices/triangles).
- Well shapefiles (points) and section shapefiles (lines), with per-surface toggles (`surface_data_mapping.csv`) and edge lists (`surface_checkpoint_edges.csv`) to include/exclude controls.
- Optional depth CSVs for vertical: `surface_checkpoint_depths_wells.csv`, `surface_checkpoint_depths_sections.csv`.
- Config params: grid spacing (m), line sampling step (m), IDW exponents (horizontal) and IDW power for vertical residuals. CRS is optional; without CRS, outputs stay in X/Y and HTML maps are skipped.

## Method
1. **Grid + hull**: Build a 2D evaluation grid (user spacing) clipped to the convex hull of the surface footprint.
2. **Sample controls**: Use well coordinates directly; resample sections along lines at a fixed step to get dense points.
3. **Horizontal confidence (IDW)**: For each grid node, compute nearest distance to wells/sections. Convert distance `r` (km) to `ID = 1/(1 + r^p)`, min–max normalize per type (defaults: wells `p=1`, sections `p=2`), and average available weights. A ranking plot sorts grid nodes by descending confidence.
4. **Vertical confidence (|dZ|)**: When checkpoints have Z, interpolate surface Z at checkpoint XY (triangulation), compute residuals `delta_z = z_cp - z_surface`, use `|delta_z|`, then IDW over the grid. Also compute a normalized map: `1 - (|dZ| - min)/(max - min)` (1 = best).
5. **Combined confidence (H+V)**: When both layers exist, compute arithmetic (α*H+(1-α)*V), geometric (H^α * V^(1-α)), and min(H,V) variants to summarize horizontal+vertical agreement.

## Outputs (per surface)
- Horizontal confidence: CSV (X/Y, distances, weights; lon/lat if CRS set), heatmap PNG (0–1), ranking plot PNG, distance histogram, interactive HTML (basemap, isolines every 0.1, legend toggle when CRS is set), footprint PNG.
- Vertical confidence (if Z available): CSV (`x,y,abs_delta_z,abs_delta_norm`, lon/lat if CRS set), heatmaps (`|dZ|`, normalized |dZ|), interactive HTML with the same basemap/isolines/legend; footprint PNG shared.
- Combined confidence (if both H and V): CSV with arithmetic/geometric/min, PNG/HTML for the selected mode.

## Whole model
- Combined footprint PNG `model_dataset.png` showing overall extent and controls.

## Assumptions and limitations
- Nearest-distance IDW is a simple proxy; it does not model anisotropy, structural trends, or vertical accuracy.
- Quality depends on correct CRS, complete control data, sensible grid spacing and line step.
- Mapping CSVs must reflect actual IDs in shapefiles (`NOME_POZZO`, `NOME`) or use `ALL` to include everything; depth CSVs must use the same IDs/surface names.

## Parameter guidance
- **Grid spacing**: coarse enough for speed, fine enough to capture control density (e.g., 500–2000 m depending on model scale).
- **Line sampling step**: similar to desired resolution of section influence (e.g., 1000–2000 m).
- **IDW exponents**: lower `p` spreads influence farther; higher `p` localizes it. Defaults (wells `p=1`, sections `p=2`) prioritize point control decay. For vertical, `idw_power=2` by default.
- **Combined alpha/mode**: tweak `alpha` and choose `geometric`/`arithmetic`/`min` to reflect how strictly you want horizontal and vertical to agree.
