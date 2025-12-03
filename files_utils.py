# Required libraries
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPoint, MultiLineString
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.tri import Triangulation
import matplotlib.colors as mcolors
import networkx as nx
from scipy.spatial import cKDTree
from scipy import ndimage
import warnings
import pandas as pd


# Read a single-surface GOCAD .ts file
def read_gocad_ts(file_path):
    """
    Read a GOCAD .ts file and return vertices and triangles (single surface).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            print(f"Cannot decode file {file_path}. Try another encoding.")
            return np.array([]), np.array([])

    print(f"Opened file {file_path} successfully. Reading {len(lines)} lines.")
    vrtx_count = 0
    trgl_count = 0
    vertices = []
    triangles = []
    id_map = {}

    for line in lines:
        line = line.strip()
        if line.startswith('PVRTX') or line.startswith('VRTX'):
            parts = line.split()
            if len(parts) >= 5:
                try:
                    idx = int(parts[1])
                    x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
                    id_map[idx] = len(vertices)
                    vertices.append([x, y, z])
                    vrtx_count += 1
                except (ValueError, IndexError):
                    print(f"Error reading vertex: {line}")
        elif line.startswith('TRGL'):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    v1, v2, v3 = id_map.get(int(parts[1])), id_map.get(int(parts[2])), id_map.get(int(parts[3]))
                    if None not in (v1, v2, v3):
                        triangles.append([v1, v2, v3])
                        trgl_count += 1
                except (ValueError, IndexError):
                    print(f"Error reading triangle: {line}")

    print(f"Found {vrtx_count} vertices and {trgl_count} triangles in the file.")
    vertices_array = np.array(vertices)
    triangles_array = np.array(triangles) if triangles else np.array([])

    if len(vertices_array) > 0:
        print(f"Vertices array shape: {vertices_array.shape}")
        if len(vertices_array.shape) == 1:
            print("Warning: vertices array is 1D.")
    else:
        print("No vertices found in the file.")

    return vertices_array, triangles_array


def read_gocad_ts_multi(file_path):
def read_gocad_ts_multi(file_path):
    """
    Read a GOCAD .ts file with multiple surfaces and return a dict:
    {surface_name: {'vertices': np.array, 'triangles': np.array}}
    """
    current = None
    vertices = []
    triangles = []
    id_map = {}
    surface_name = None
    def commit():
        nonlocal vertices, triangles, id_map, surface_name
        if surface_name and vertices:
            surfaces[surface_name] = {
                'vertices': np.array(vertices),
                'triangles': np.array(triangles) if triangles else np.array([])
            }
        vertices = []
        triangles = []
        id_map = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()

    for line in lines:
        s = line.strip()
        if s.lower().startswith('gocad tsurf'):
            if vertices:
                commit()
            surface_name = None
        elif s.lower().startswith('name:'):
            surface_name = s.split(':', 1)[1].strip()
        elif s.startswith('PVRTX') or s.startswith('VRTX'):
            parts = s.split()
            if len(parts) >= 5:
                try:
                    idx = int(parts[1])
                    x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
                    id_map[idx] = len(vertices)
                    vertices.append([x, y, z])
                except Exception:
                    continue
        elif s.startswith('TRGL'):
            parts = s.split()
            if len(parts) >= 4:
                try:
                    v1, v2, v3 = id_map.get(int(parts[1])), id_map.get(int(parts[2])), id_map.get(int(parts[3]))
                    if None not in (v1, v2, v3):
                        triangles.append([v1, v2, v3])
                except Exception:
                    continue
    if vertices:
        commit()
    return surfaces


def process_gocad_file(working_dir):
    try:
        ts_files = [f for f in os.listdir(working_dir) if f.endswith('.ts')]

        if not ts_files:
            print("No .ts file found in the working folder.")
            return None, None

        ts_file = ts_files[0]
        ts_path = os.path.join(working_dir, ts_file)
        print(f"Reading GOCAD .ts file: {ts_file}")

        vertices, triangles = read_gocad_ts(ts_path)

        if vertices is not None:
            if len(vertices) == 0:
                print("No vertices found in the GOCAD .ts file.")
                return None, None

            if not isinstance(vertices, np.ndarray):
                vertices = np.array(vertices)

            if len(vertices.shape) == 1:
                print("Warning: vertices array is 1D. Trying to reshape...")
                if len(vertices) % 3 == 0:
                    vertices = vertices.reshape(-1, 3)
                    print(f"Reshaped vertices array: {vertices.shape}")
                else:
                    print(f"Could not reshape vertices array. Size not compatible: {len(vertices)}")

            print(f"Read {len(vertices)} vertices and {len(triangles) if triangles is not None else 0} triangles.")
            print(f"Forma dell'array vertices: {vertices.shape}")

        return vertices, triangles

    except Exception as e:
        print(f"Error while reading GOCAD .ts file: {e}")
        return None, None


def read_wells_shapefile(working_dir):
    try:
        shp_files = [f for f in os.listdir(working_dir) if f.endswith('.shp')]
        well_keywords = ['pozz', 'well', 'pozzo', 'pozzi', 'sondaggio', 'sondaggi', 'borehole', 'boreholes']

        wells_shp = None
        for shp_file in shp_files:
            filename_lower = shp_file.lower()
            if any(keyword in filename_lower for keyword in well_keywords):
                wells_path = os.path.join(working_dir, shp_file)
                print(f"Reading well shapefile: {shp_file}")
                wells_shp = gpd.read_file(wells_path)

                if wells_shp.geom_type.isin(['Point', 'MultiPoint']).any():
                    print("Confirmed: shapefile contains points (wells).")
                else:
                    print(f"Warning: shapefile {shp_file} was identified as wells but has no points.")
                    print(f"Geometry types present: {wells_shp.geom_type.unique()}")
                break

        if wells_shp is None and shp_files:
            for shp_file in shp_files:
                try:
                    temp_shp = gpd.read_file(os.path.join(working_dir, shp_file))
                    if temp_shp.geom_type.isin(['Point', 'MultiPoint']).any():
                        wells_path = os.path.join(working_dir, shp_file)
                        print(f"Found shapefile with points: {shp_file}")
                        wells_shp = temp_shp
                        break
                except Exception as e:
                    print(f"Error reading {shp_file}: {e}")

        if wells_shp is None:
            print("No shapefile found for wells.")
            return None

        print(f"Columns available in wells shapefile: {wells_shp.columns.tolist()}")
        print(f"Letto shapefile dei Wells con {len(wells_shp)} punti.")
        return wells_shp

    except Exception as e:
        print(f"Error reading wells shapefile: {e}")
        return None


def read_sections_shapefile(working_dir):
    try:
        shp_files = [f for f in os.listdir(working_dir) if f.endswith('.shp')]
        section_keywords = ['sez', 'section', 'trac', 'sezione', 'sezioni', 'linea', 'linee', 'sismica', 'sismiche', 'line']

        sections_shp = None
        for shp_file in shp_files:
            filename_lower = shp_file.lower()
            if any(keyword in filename_lower for keyword in section_keywords):
                sections_path = os.path.join(working_dir, shp_file)
                print(f"Reading section shapefile: {shp_file}")
                sections_shp = gpd.read_file(sections_path)

                if sections_shp.geom_type.isin(['LineString', 'MultiLineString']).any():
                    print("Confirmed: shapefile contains lines (section traces).")
                else:
                    print(f"Warning: shapefile {shp_file} was identified as sections but has no lines.")
                    print(f"Geometry types present: {sections_shp.geom_type.unique()}")
                break

        if sections_shp is None and len(shp_files) >= 2:
            for shp_file in shp_files:
                try:
                    temp_shp = gpd.read_file(os.path.join(working_dir, shp_file))
                    if temp_shp.geom_type.isin(['LineString', 'MultiLineString']).any():
                        sections_path = os.path.join(working_dir, shp_file)
                        print(f"Found shapefile with lines: {shp_file}")
                        sections_shp = temp_shp
                        break
                except Exception as e:
                    print(f"Error reading {shp_file}: {e}")

        if sections_shp is None:
            print("No shapefile found for sections.")
            return None

        print(f"Columns available in sections shapefile: {sections_shp.columns.tolist()}")
        print(f"Loaded sections shapefile with {len(sections_shp)} features.")
        return sections_shp

    except Exception as e:
        print(f"Error reading sections shapefile: {e}")
        return None


# UtilitÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â  per accuratezza orizzontale su griglia
def get_surface_name(working_dir):
    ts_files = [f for f in os.listdir(working_dir) if f.endswith('.ts')]
    if not ts_files:
        return "surface_1"
    ts_path = os.path.join(working_dir, ts_files[0])
    try:
        with open(ts_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().lower().startswith('name:'):
                    return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return "surface_1"


def ensure_mapping_file(working_dir, surface_name):
    """
    Ensure a surface->data mapping file (wells/sections/maps).
    If missing, create a template with wells/sections enabled and maps disabled.
    """
    import pandas as pd
    map_path = os.path.join(working_dir, 'surface_data_mapping.csv')
    if not os.path.exists(map_path):
        df = pd.DataFrame([{
            'surface': surface_name,
            'use_wells': 1,
            'use_sections': 1,
            'use_maps': 0
        }])
        df.to_csv(map_path, index=False)
        print(f"Created mapping file: {map_path}")
    try:
        df = pd.read_csv(map_path)
    except Exception as e:
        print(f"Could not read {map_path}: {e}. Using default settings.")
        return {'use_wells': True, 'use_sections': True, 'use_maps': False}
    row = df[df['surface'] == surface_name]
    if row.empty:
        print(f"No row for surface {surface_name} in mapping. Using defaults.")
        return {'use_wells': True, 'use_sections': True, 'use_maps': False}
    def bool_val(col):
        return bool(row.iloc[0].get(col, 1))
    return {
        'use_wells': bool_val('use_wells'),
        'use_sections': bool_val('use_sections'),
        'use_maps': bool_val('use_maps')
    }


def ensure_checkpoint_edges_file(working_dir, surface_names, wells_gdf=None, sections_gdf=None):
    """
    Ensure a surface-checkpoint-type edge list.
    Columns: surface, checkpoint_id, type (well|section|map).
    Template: one 'ALL' row for wells and sections per surface.
    """
    path = os.path.join(working_dir, 'surface_checkpoint_edges.csv')
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    rows = []
    for s in surface_names:
        rows.append({'surface': s, 'checkpoint_id': 'ALL', 'type': 'well'})
        rows.append({'surface': s, 'checkpoint_id': 'ALL', 'type': 'section'})
        rows.append({'surface': s, 'checkpoint_id': 'NONE', 'type': 'map'})
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    print(f"Created checkpoint edge list: {path}")
    return df


def filter_checkpoints_by_edges(edges_df, surface, wells_gdf, sections_gdf):
    wells_out = wells_gdf
    sections_out = sections_gdf
    subset = edges_df[edges_df['surface'] == surface] if edges_df is not None else pd.DataFrame()
    if subset.empty:
        return wells_out, sections_out
    def norm_series(s):
        return s.fillna('').astype(str).str.strip().str.lower()
    # normalizza edges
    subset_ids = norm_series(subset['checkpoint_id'])
    subset_types = norm_series(subset['type'])
    # Wells
    if wells_gdf is not None:
        wells_ids = norm_series(wells_gdf['NOME_POZZO']) if 'NOME_POZZO' in wells_gdf.columns else norm_series(wells_gdf.index.to_series())
        wells_sel = subset[(subset_types == 'well')]
        if not wells_sel.empty and 'all' not in subset_ids[wells_sel.index].unique():
            ids = subset_ids[wells_sel.index].tolist()
            wells_out = wells_gdf[wells_ids.isin(ids)]
    # Sections
    if sections_gdf is not None:
        sec_ids = norm_series(sections_gdf['NOME']) if 'NOME' in sections_gdf.columns else norm_series(sections_gdf.index.to_series())
        sec_sel = subset[(subset_types == 'section')]
        if not sec_sel.empty and 'all' not in subset_ids[sec_sel.index].unique():
            ids = subset_ids[sec_sel.index].tolist()
            sections_out = sections_gdf[sec_ids.isin(ids)]
    return wells_out, sections_out
    # Wells
    wells_edges = subset[subset['type'].str.lower() == 'well']
    if wells_gdf is not None and not wells_edges.empty:
        ids = wells_edges['checkpoint_id'].astype(str).tolist()
        if 'ALL' not in ids:
            ids = [i for i in ids if i and i != 'NONE']
            if 'NOME_POZZO' in wells_gdf.columns:
                wells_out = wells_gdf[wells_gdf['NOME_POZZO'].astype(str).isin(ids)]
            else:
                wells_out = wells_gdf[wells_gdf.index.astype(str).isin(ids)]
    # Sections
    sec_edges = subset[subset['type'].str.lower() == 'section']
    if sections_gdf is not None and not sec_edges.empty:
        ids = sec_edges['checkpoint_id'].astype(str).tolist()
        if 'ALL' not in ids:
            ids = [i for i in ids if i and i != 'NONE']
            if 'NOME' in sections_gdf.columns:
                sections_out = sections_gdf[sections_gdf['NOME'].astype(str).isin(ids)]
            else:
                sections_out = sections_gdf[sections_gdf.index.astype(str).isin(ids)]
    return wells_out, sections_out


def build_grid(vertices, spacing=5000, clip_to_hull=True):
    xs, ys = vertices[:, 0], vertices[:, 1]
    min_x, max_x = xs.min(), xs.max()
    min_y, max_y = ys.min(), ys.max()
    gx = np.arange(min_x, max_x + spacing, spacing)
    gy = np.arange(min_y, max_y + spacing, spacing)
    GX, GY = np.meshgrid(gx, gy)
    grid_points = np.c_[GX.ravel(), GY.ravel()]
    if clip_to_hull:
        try:
            from shapely.geometry import Polygon, Point as ShPoint
            hull = Polygon(np.c_[xs, ys]).convex_hull
            mask = np.array([hull.contains(ShPoint(p[0], p[1])) for p in grid_points])
        except Exception:
            mask = np.ones(len(grid_points), dtype=bool)
            hull = None
    else:
        mask = np.ones(len(grid_points), dtype=bool)
        hull = None
    return GX, GY, grid_points, mask, hull


def nearest_distance(points, targets):
    tree = cKDTree(targets)
    dist, idx = tree.query(points, k=1)
    return dist, idx


def extract_points_from_wells(wells_gdf):
    xs = wells_gdf.geometry.x.values
    ys = wells_gdf.geometry.y.values
    return xs, ys


def sample_lines_gdf(lines_gdf, step=2000):
    pts_x, pts_y = [], []
    for geom in lines_gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        geoms = [geom] if geom.geom_type == 'LineString' else list(geom.geoms)
        for g in geoms:
            num = max(2, int(max(g.length, step) // step))
            for f in np.linspace(0, 1, num):
                p = g.interpolate(f, normalized=True)
                pts_x.append(p.x)
                pts_y.append(p.y)
    return np.array(pts_x), np.array(pts_y)


def compute_order_weight(distances_m, order_p):
    # r in km
    r = distances_m / 1000.0
    ID = 1 / (1 + np.power(r, order_p))
    ID_min = ID.min()
    ID_max = ID.max()
    if ID_max == ID_min:
        return np.ones_like(ID)
    return (ID - ID_min) / (ID_max - ID_min)


def compute_horizontal_weights(grid_points, wells_points=None, sections_points=None):
    weights_list = []
    wells_w = None
    sections_w = None
    if wells_points is not None and wells_points.shape[0] > 0:
        dists, _ = nearest_distance(grid_points, wells_points)
        wells_w = compute_order_weight(dists, order_p=1)
        weights_list.append(wells_w)
    if sections_points is not None and sections_points.shape[0] > 0:
        dists, _ = nearest_distance(grid_points, sections_points)
        sections_w = compute_order_weight(dists, order_p=2)
        weights_list.append(sections_w)
    if not weights_list:
        return None, None, None
    stack = np.vstack(weights_list)
    combined = stack.mean(axis=0)
    return combined, wells_w, sections_w


def generate_accuracy_outputs(vertices, wells_shp, sections_shp, output_dir,
                              use_wells=True, use_sections=True,
                              grid_spacing=5000, line_step=2000, surface_name='surface'):
    """
    Calcola pesi orizzontali (IDW) e distribuzioni delle distanze.
    Salva CSV e PNG in output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    GX, GY, grid_points, mask, hull = build_grid(vertices, spacing=grid_spacing, clip_to_hull=True)

    wells_points = None
    sections_points = None
    if use_wells and wells_shp is not None and not wells_shp.empty:
        wx, wy = extract_points_from_wells(wells_shp)
        wells_points = np.c_[wx, wy]
    if use_sections and sections_shp is not None and not sections_shp.empty:
        lx, ly = sample_lines_gdf(sections_shp, step=line_step)
        if len(lx) > 0:
            sections_points = np.c_[lx, ly]

    grid_points_use = grid_points[mask]
    combined, wells_w, sections_w = compute_horizontal_weights(
        grid_points_use, wells_points, sections_points
    )

    df = pd.DataFrame({'x': grid_points_use[:, 0], 'y': grid_points_use[:, 1]})
    if wells_points is not None:
        d_w, _ = nearest_distance(grid_points_use, wells_points)
        df['dist_wells'] = d_w
        df['dist_wells_km'] = d_w / 1000.0
        if wells_w is not None:
            df['weight_wells'] = wells_w
    if sections_points is not None:
        d_s, _ = nearest_distance(grid_points_use, sections_points)
        df['dist_sections'] = d_s
        df['dist_sections_km'] = d_s / 1000.0
        if sections_w is not None:
            df['weight_sections'] = sections_w
    if combined is not None:
        df['weight_combined'] = combined

    df.to_csv(os.path.join(output_dir, f'horizontal_accuracy_grid_{surface_name}.csv'), index=False)

    # Heatmap
    if combined is not None:
        try:
            grid_weights = np.full(GX.shape, np.nan, dtype=float)
            mask2d = mask.reshape(GX.shape)
            grid_weights[mask2d] = combined
            fig_w = plt.figure(figsize=(10, 8))
            plt.pcolormesh(GX, GY, grid_weights, cmap='viridis', shading='auto')
            plt.colorbar(label='Peso (accuratezza orizzontale)')
            plt.title(f'Accuratezza orizzontale (IDW) - {surface_name}')
            plt.savefig(os.path.join(output_dir, f'horizontal_accuracy_idw_{surface_name}.png'), dpi=300, bbox_inches='tight')
            plt.close(fig_w)
        except Exception as e:
            warnings.warn(f"Could not save weight heatmap: {e}")

    # Istogrammi distanze (km)
    try:
        fig_h = plt.figure(figsize=(8, 6))
        max_km = 0
        if wells_points is not None:
            max_km = max(max_km, df['dist_wells_km'].max())
            bins_w = np.arange(df['dist_wells_km'].min(), df['dist_wells_km'].max() + 0.1, 5)
            plt.hist(df['dist_wells_km'], bins=bins_w, alpha=0.6, label='Wells', histtype='step', linewidth=2)
        if sections_points is not None:
            max_km = max(max_km, df['dist_sections_km'].max())
            bins_s = np.arange(df['dist_sections_km'].min(), df['dist_sections_km'].max() + 0.1, 5)
            plt.hist(df['dist_sections_km'], bins=bins_s, alpha=0.6, label='Sections', histtype='step', linewidth=2)
        plt.xlabel(f'distance from nearest checkpoint (km) - {surface_name}')
        plt.ylabel('occurrences')
        if max_km > 0:
            plt.xlim([0, max_km * 1.05])
        if (wells_points is not None) or (sections_points is not None):
            plt.legend()
        plt.savefig(os.path.join(output_dir, f'distance_histogram_{surface_name}.png'), dpi=300, bbox_inches='tight')
        plt.close(fig_h)
    except Exception as e:
        warnings.warn(f"Could not save distance histogram: {e}")

    # Interattivo IDW
    try:
        import plotly.express as px
        if combined is not None:
            df_plot = df.copy()
            df_plot['weight_plot'] = df_plot['weight_combined'].fillna(0)
            fig = px.scatter(df_plot, x='x', y='y', color='weight_plot',
                             color_continuous_scale='viridis', range_color=[0, 1],
                             title=f'IDW {surface_name}', width=900, height=750)
            fig.update_layout(xaxis_title='X', yaxis_title='Y')
            fig.write_html(os.path.join(output_dir, f'interactive_idw_{surface_name}.html'))
    except Exception as e:
        warnings.warn(f"Could not save interactive map: {e}")

    return {
        'grid_points': grid_points_use,
        'weights': combined,
        'weights_wells': wells_w,
        'weights_sections': sections_w,
        'GX': GX,
        'GY': GY,
        'dist_wells': df.get('dist_wells_km') if 'dist_wells_km' in df else None,
        'dist_sections': df.get('dist_sections_km') if 'dist_sections_km' in df else None
    }


def visualize_data(vertices, triangles, wells_shp, sections_shp, apply_smoothing=False,
                   smoothing_iterations=3, smoothing_factor=0.2, crs='EPSG:6708',
                   output_filename='model_dataset.png', grid_points=None, show_plot=False, surface_name=None):
    """
    Styled visualization of the GOCAD surface footprint (only extent), wells, and sections
    with presentation-friendly styling. Optimized version using a bounding polygon for better performance.
    """
    import matplotlib.pyplot as plt
    from matplotlib.tri import Triangulation
    from matplotlib.colors import LinearSegmentedColormap
    from shapely.geometry import Point, MultiPoint, LineString, MultiLineString, Polygon
    import numpy as np
    import matplotlib.patheffects as PathEffects
    from matplotlib.lines import Line2D
    from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
    import matplotlib.font_manager as fm
    from datetime import datetime
    import os
    from scipy.spatial import ConvexHull
    import time
    from shapely.geometry import Polygon

    start_time = time.time()
    output_dir = "output_results"
    os.makedirs(output_dir, exist_ok=True)
    grid_label_added = False

    # Set a style; fallback if the seaborn theme is unavailable
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except OSError:
        try:
            plt.style.use('seaborn-whitegrid')
        except OSError:
            pass

    fig = plt.figure(figsize=(14, 12), dpi=100)
    ax_2d = fig.add_subplot(111)

    if vertices is not None and triangles is not None and len(vertices) > 0 and len(triangles) > 0:
        if apply_smoothing:
            original_vertices = vertices.copy()
            vertices = smooth_surface(vertices, triangles,
                                     iterations=smoothing_iterations,
                                     factor=smoothing_factor)
            print(f"Smoothing applied to surfaces (iterations: {smoothing_iterations}, factor: {smoothing_factor})")

    if vertices is not None and len(vertices) > 0:
        if len(vertices.shape) == 2 and vertices.shape[1] >= 2:
            try:
                points_2d = vertices[:, :2]
                min_x, min_y = np.min(points_2d, axis=0)
                max_x, max_y = np.max(points_2d, axis=0)
                rect_coords = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
                rect_polygon = Polygon(rect_coords)
                x, y = rect_polygon.exterior.xy
                ax_2d.fill(x, y, color='steelblue', alpha=0.1, label='Model and data footprint')
                ax_2d.plot(x, y, color='steelblue', linewidth=1.5, alpha=0.7)
                print("Surface footprint shown as rectangle (fast mode)")
            except Exception as e:
                print(f"Error drawing optimized footprint: {e}")
                try:
                    points_2d = vertices[:, :2]
                    min_x, min_y = np.min(points_2d, axis=0)
                    max_x, max_y = np.max(points_2d, axis=0)
                    ax_2d.plot([min_x, max_x, max_x, min_x, min_x],
                               [min_y, min_y, max_y, max_y, min_y],
                               color='steelblue', linewidth=1.5, alpha=0.7,
                               label='Surface footprint (box)')
                except Exception as e2:
                    print(f"Fallback to point visualization: {e2}")
                    if len(vertices) > 500:
                        sampling_rate = max(1, len(vertices) // 500)
                        sampled_vertices = vertices[::sampling_rate]
                        ax_2d.scatter(sampled_vertices[:, 0], sampled_vertices[:, 1], s=2, alpha=0.6,
                                      c='steelblue', label='GOCAD vertices (sampled)', edgecolors='none')
                    else:
                        ax_2d.scatter(vertices[:, 0], vertices[:, 1], s=2, alpha=0.6,
                                      c='steelblue', label='GOCAD vertices', edgecolors='none')
        else:
            print(f"Warning: vertices has an invalid shape for visualization: {vertices.shape}")

    if wells_shp is not None and not wells_shp.empty:
        try:
            wells_shp.plot(ax=ax_2d, color='none', markersize=0, label='_nolegend_')
            for idx, row in wells_shp.iterrows():
                if isinstance(row.geometry, (Point, MultiPoint)):
                    x = row.geometry.x if hasattr(row.geometry, 'x') else row.geometry.geoms[0].x
                    y = row.geometry.y if hasattr(row.geometry, 'y') else row.geometry.geoms[0].y
                    ax_2d.scatter(x, y, s=180, color='lightskyblue', alpha=0.3,
                                  edgecolors='none', zorder=10)
                    ax_2d.scatter(x, y, s=100, color='royalblue', alpha=0.5,
                                  edgecolors='none', zorder=11)
                    ax_2d.scatter(x, y, s=40, color='darkblue', alpha=0.9,
                                  edgecolors='white', linewidths=1, zorder=12)

            legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor='darkblue',
                                      markersize=10, label='Wells', markeredgecolor='white')]

            name_columns = [col for col in wells_shp.columns if any(
                keyword in col.lower() for keyword in ['name', 'nome', 'id', 'cod', 'ident', 'label', 'num'])]

            if name_columns:
                label_col = name_columns[0]
                for idx, row in wells_shp.iterrows():
                    if isinstance(row.geometry, (Point, MultiPoint)):
                        x = row.geometry.x if hasattr(row.geometry, 'x') else row.geometry.geoms[0].x
                        y = row.geometry.y if hasattr(row.geometry, 'y') else row.geometry.geoms[0].y

                        txt = ax_2d.annotate(str(row[label_col]), xy=(x, y),
                                             xytext=(7, 7), textcoords='offset points',
                                             fontsize=9, fontweight='bold', color='white',
                                             bbox=dict(boxstyle="round,pad=0.3", fc='royalblue', ec="none", alpha=0.7))
                        txt.set_path_effects([PathEffects.withStroke(linewidth=2, foreground='navy')])
        except Exception as e:
            print(f"Error during advanced well visualization: {e}")
            wells_shp.plot(ax=ax_2d, color='blue', markersize=50, label='Wells')

    if sections_shp is not None and not sections_shp.empty:
        try:
            section_legend = Line2D([0], [0], color='crimson', lw=2, label='Sections')
            if 'legend_elements' in locals():
                legend_elements.append(section_legend)
            else:
                legend_elements = [section_legend]

            for geom in sections_shp.geometry:
                if geom is None or geom.is_empty:
                    continue
                geoms = [geom] if isinstance(geom, LineString) else list(geom.geoms)
                for g in geoms:
                    x, y = g.xy
                    ax_2d.plot(x, y, color='salmon', linewidth=6, alpha=0.3, zorder=7)
                    ax_2d.plot(x, y, color='crimson', linewidth=2.5, alpha=0.9, zorder=8)
                    ax_2d.plot(x, y, color='white', linewidth=1, linestyle=(0, (5, 5)),
                               alpha=0.7, zorder=9)

            name_columns = [col for col in sections_shp.columns if any(
                keyword in col.lower() for keyword in ['name', 'nome', 'id', 'cod', 'ident', 'label', 'num', 'linea', 'line'])]

            if name_columns:
                label_col = name_columns[0]
                for idx, row in sections_shp.iterrows():
                    if isinstance(row.geometry, (LineString, MultiLineString)):
                        if isinstance(row.geometry, LineString):
                            midpoint = row.geometry.interpolate(0.5, normalized=True)
                        else:
                            midpoint = row.geometry.geoms[0].interpolate(0.5, normalized=True)

                        txt = ax_2d.annotate(str(row[label_col]), xy=(midpoint.x, midpoint.y),
                                             xytext=(7, 7), textcoords='offset points',
                                             fontsize=9, fontweight='bold', color='white',
                                             bbox=dict(boxstyle="round,pad=0.3", fc='crimson', ec="none", alpha=0.7))
                        txt.set_path_effects([PathEffects.withStroke(linewidth=2, foreground='darkred')])
        except Exception as e:
            print(f"Errore durante la visualizzazione avanzata delle Sections: {e}")
            sections_shp.plot(ax=ax_2d, color='red', linewidth=2, label='Sections')

    stats_info = []

    if triangles is not None and len(triangles) > 0:
        num_triangles = len(triangles)
        num_vertices = len(vertices) if vertices is not None else 0
        stats_info.append(f"Triangles: {num_triangles:,}")

        if vertices is not None and len(vertices.shape) == 2 and vertices.shape[1] >= 3:
            z_min, z_max = np.min(vertices[:, 2]), np.max(vertices[:, 2])
            z_mean = np.mean(vertices[:, 2])
            stats_info.append(f"Min elevation: {z_min:.2f} m")
            stats_info.append(f"Max elevation: {z_max:.2f} m")

    if wells_shp is not None and not wells_shp.empty:
        num_wells = len(wells_shp)
        stats_info.append(f"Wells: {num_wells}")

    if sections_shp is not None and not sections_shp.empty:
        num_sections = len(sections_shp)
        stats_info.append(f"Sections: {num_sections}")

    ax_2d.set_xlabel('X (m)', fontsize=12, fontweight='bold')
    ax_2d.set_ylabel('Y (m)', fontsize=12, fontweight='bold')
    lower_name = str(surface_name).lower() if surface_name else ''
    is_model = lower_name.startswith('modello') or lower_name.startswith('model')
    if is_model:
        title_txt = "Model and data footprint"
        stats_title = "MODEL STATS"
    else:
        title_txt = f"Surface footprint {surface_name}" if surface_name else "Surface footprint"
        stats_title = "SURFACE STATS"
    ax_2d.set_title(title_txt, fontsize=16, fontweight='bold', pad=20)

    if stats_info:
        stats_text = '\n'.join(stats_info)
        ax_2d.text(0.98, 0.98, stats_text,
                   transform=ax_2d.transAxes,
                   fontsize=10,
                   verticalalignment='top',
                   horizontalalignment='right',
                   bbox=dict(boxstyle='round,pad=0.7',
                             facecolor='white',
                             edgecolor='lightgray',
                             alpha=0.9))

        ax_2d.text(0.98, 1.02, stats_title,
                   transform=ax_2d.transAxes,
                   fontsize=11,
                   fontweight='bold',
                   verticalalignment='bottom',
                   horizontalalignment='right',
                   bbox=dict(boxstyle='round,pad=0.3',
                             facecolor='royalblue',
                             edgecolor='none',
                             alpha=0.9),
                   color='white')

    x_min, x_max = ax_2d.get_xlim()
    plot_width = x_max - x_min
    scale_options = [10, 50, 100, 500, 1000, 2000, 5000, 10000]
    scale_size = next((x for x in scale_options if x > plot_width / 10), scale_options[-1])

    fontprops = fm.FontProperties(size=9, weight='bold')
    scalebar = AnchoredSizeBar(ax_2d.transData,
                               scale_size,
                               f'{scale_size} m',
                               'lower left',
                               pad=0.5,
                               color='black',
                               frameon=True,
                               size_vertical=1,
                               fontproperties=fontprops,
                               bbox_to_anchor=(0.05, 0.05),
                               bbox_transform=ax_2d.transAxes,
                               sep=5)

    scalebar.patch.set_facecolor('white')
    scalebar.patch.set_alpha(0.8)
    scalebar.patch.set_edgecolor('lightgray')
    ax_2d.add_artist(scalebar)

    if 'legend_elements' in locals() and legend_elements:
        if grid_label_added:
            legend_elements.append(Line2D([0], [0], marker='s', color='w', markerfacecolor='gray',
                                          markersize=6, alpha=0.5, label='Griglia valutazione'))
        ax_2d.legend(handles=legend_elements, loc='upper left', frameon=True, framealpha=0.9, edgecolor='lightgray')

    ax_2d.text(0.02, 0.02, f"Coordinate system: {crs}",
               transform=ax_2d.transAxes,
               fontsize=8,
               verticalalignment='bottom',
               horizontalalignment='left',
               bbox=dict(boxstyle='round,pad=0.3',
                         facecolor='white',
                         edgecolor='lightgray',
                         alpha=0.8))

    fig.text(0.99, 0.01, f"{datetime.now().strftime('%d/%m/%Y %H:%M')} - {surface_name or ''}",
             fontsize=7, color='gray', ha='right', va='bottom')

    # Griglia di valutazione
    grid_label_added = False
    if grid_points is not None:
        try:
            ax_2d.scatter(grid_points[:, 0], grid_points[:, 1], s=3, color='gray', alpha=0.3, label='Griglia valutazione')
            grid_label_added = True
        except Exception:
            grid_label_added = False

    plt.tight_layout()

    execution_time = time.time() - start_time
    print(f"Execution time: {execution_time:.2f} secondi")

    output_path = os.path.join(output_dir, output_filename)
    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Figure saved to: {output_path}")

    if show_plot:
        plt.show()
    plt.close(fig)
    return fig


def smooth_surface(vertices, triangles, iterations=3, factor=0.2):
    """
    Apply Laplacian smoothing to the surface
    """
    import numpy as np

    smoothed_vertices = vertices.copy()
    neighbors = [[] for _ in range(len(vertices))]

    for tri in triangles:
        for i in range(3):
            v1 = tri[i]
            v2 = tri[(i + 1) % 3]
            v3 = tri[(i + 2) % 3]

            if v2 not in neighbors[v1]:
                neighbors[v1].append(v2)
            if v3 not in neighbors[v1]:
                neighbors[v1].append(v3)

    for _ in range(iterations):
        new_vertices = smoothed_vertices.copy()

        for i in range(len(smoothed_vertices)):
            if not neighbors[i]:
                continue

            neighbor_sum = np.zeros(3)
            for n in neighbors[i]:
                neighbor_sum += smoothed_vertices[n]

            neighbor_avg = neighbor_sum / len(neighbors[i])
            new_vertices[i] = smoothed_vertices[i] + factor * (neighbor_avg - smoothed_vertices[i])

        smoothed_vertices = new_vertices

    return smoothed_vertices

