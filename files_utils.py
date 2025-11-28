# Importazione delle librerie necessarie
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


# Funzione per leggere il file GOCAD .ts
def read_gocad_ts(file_path):
    """
    Legge un file GOCAD .ts e restituisce i vertici e i triangoli (un'unica superficie).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            print(f"Impossibile decodificare il file {file_path}. Prova altre codifiche.")
            return np.array([]), np.array([])

    print(f"File {file_path} aperto con successo. Lettura di {len(lines)} linee.")
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
                    print(f"Errore nella lettura del vertice: {line}")
        elif line.startswith('TRGL'):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    v1, v2, v3 = id_map.get(int(parts[1])), id_map.get(int(parts[2])), id_map.get(int(parts[3]))
                    if None not in (v1, v2, v3):
                        triangles.append([v1, v2, v3])
                        trgl_count += 1
                except (ValueError, IndexError):
                    print(f"Errore nella lettura del triangolo: {line}")

    print(f"Trovati {vrtx_count} vertici e {trgl_count} triangoli nel file.")
    vertices_array = np.array(vertices)
    triangles_array = np.array(triangles) if triangles else np.array([])

    if len(vertices_array) > 0:
        print(f"Forma dell'array vertices: {vertices_array.shape}")
        if len(vertices_array.shape) == 1:
            print("Avviso: l'array vertices e' unidimensionale.")
    else:
        print("Nessun vertice trovato nel file.")

    return vertices_array, triangles_array


def read_gocad_ts_multi(file_path):
    """
    Legge un file GOCAD .ts con più superfici e restituisce un dict
    {surface_name: {'vertices': np.array, 'triangles': np.array}}
    """
    surfaces = {}
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
            print("Nessun file .ts trovato nella cartella di lavoro.")
            return None, None

        ts_file = ts_files[0]
        ts_path = os.path.join(working_dir, ts_file)
        print(f"Lettura del file GOCAD .ts: {ts_file}")

        vertices, triangles = read_gocad_ts(ts_path)

        if vertices is not None:
            if len(vertices) == 0:
                print("Nessun vertice trovato nel file GOCAD .ts.")
                return None, None

            if not isinstance(vertices, np.ndarray):
                vertices = np.array(vertices)

            if len(vertices.shape) == 1:
                print("Avviso: l'array vertices e' unidimensionale. Tentativo di rimodellarlo...")
                if len(vertices) % 3 == 0:
                    vertices = vertices.reshape(-1, 3)
                    print(f"Array vertices rimodellato con successo: {vertices.shape}")
                else:
                    print(f"Impossibile rimodellare l'array vertices. Dimensione non compatibile: {len(vertices)}")

            print(f"Letti {len(vertices)} vertici e {len(triangles) if triangles is not None else 0} triangoli.")
            print(f"Forma dell'array vertices: {vertices.shape}")

        return vertices, triangles

    except Exception as e:
        print(f"Errore durante la lettura del file GOCAD .ts: {e}")
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
                print(f"Lettura dello shapefile dei pozzi: {shp_file}")
                wells_shp = gpd.read_file(wells_path)

                if wells_shp.geom_type.isin(['Point', 'MultiPoint']).any():
                    print("Confermato: lo shapefile contiene punti (pozzi).")
                else:
                    print(f"Avviso: lo shapefile {shp_file} e' stato identificato come pozzi ma non contiene punti.")
                    print(f"Tipi di geometria presenti: {wells_shp.geom_type.unique()}")
                break

        if wells_shp is None and shp_files:
            for shp_file in shp_files:
                try:
                    temp_shp = gpd.read_file(os.path.join(working_dir, shp_file))
                    if temp_shp.geom_type.isin(['Point', 'MultiPoint']).any():
                        wells_path = os.path.join(working_dir, shp_file)
                        print(f"Trovato shapefile con punti: {shp_file}")
                        wells_shp = temp_shp
                        break
                except Exception as e:
                    print(f"Errore durante la lettura di {shp_file}: {e}")

        if wells_shp is None:
            print("Nessun shapefile trovato per i pozzi.")
            return None

        print(f"Colonne disponibili nello shapefile dei pozzi: {wells_shp.columns.tolist()}")
        print(f"Letto shapefile dei pozzi con {len(wells_shp)} punti.")
        return wells_shp

    except Exception as e:
        print(f"Errore durante la lettura dello shapefile dei pozzi: {e}")
        return None


def read_sections_shapefile(working_dir):
    try:
        shp_files = [f for f in os.listdir(working_dir) if f.endswith('.shp')]
        section_keywords = ['sez', 'section', 'trac', 'sezione', 'sezioni', 'linea', 'linee', 'sismica', 'sismiche']

        sections_shp = None
        for shp_file in shp_files:
            filename_lower = shp_file.lower()
            if any(keyword in filename_lower for keyword in section_keywords):
                sections_path = os.path.join(working_dir, shp_file)
                print(f"Lettura dello shapefile delle sezioni: {shp_file}")
                sections_shp = gpd.read_file(sections_path)

                if sections_shp.geom_type.isin(['LineString', 'MultiLineString']).any():
                    print("Confermato: lo shapefile contiene linee (tracce di sezioni).")
                else:
                    print(f"Avviso: lo shapefile {shp_file} e' stato identificato come sezioni ma non contiene linee.")
                    print(f"Tipi di geometria presenti: {sections_shp.geom_type.unique()}")
                break

        if sections_shp is None and len(shp_files) >= 2:
            for shp_file in shp_files:
                try:
                    temp_shp = gpd.read_file(os.path.join(working_dir, shp_file))
                    if temp_shp.geom_type.isin(['LineString', 'MultiLineString']).any():
                        sections_path = os.path.join(working_dir, shp_file)
                        print(f"Trovato shapefile con linee: {shp_file}")
                        sections_shp = temp_shp
                        break
                except Exception as e:
                    print(f"Errore durante la lettura di {shp_file}: {e}")

        if sections_shp is None:
            print("Nessun shapefile trovato per le sezioni.")
            return None

        print(f"Colonne disponibili nello shapefile delle sezioni: {sections_shp.columns.tolist()}")
        print(f"Letto shapefile delle sezioni con {len(sections_shp)} elementi.")
        return sections_shp

    except Exception as e:
        print(f"Errore durante la lettura dello shapefile delle sezioni: {e}")
        return None


# Utilità per accuratezza orizzontale su griglia
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
    Garantisce un file di mapping surface->dati (pozzi/sezioni/mappe).
    Se assente, crea un template con tutti i dati abilitati eccetto mappe.
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
        print(f"Creato file di mapping: {map_path}")
    try:
        df = pd.read_csv(map_path)
    except Exception as e:
        print(f"Impossibile leggere {map_path}: {e}. Uso impostazioni di default.")
        return {'use_wells': True, 'use_sections': True, 'use_maps': False}
    row = df[df['surface'] == surface_name]
    if row.empty:
        print(f"Nessuna riga per la superficie {surface_name} in mapping. Uso default.")
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
    Garantisce un file edge list surface-checkpoint-type.
    Colonne: surface, checkpoint_id, type (well|section|map).
    Template: una riga 'ALL' per wells e sections per ogni superficie.
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
    print(f"Creato file edge list checkpoints: {path}")
    return df


def filter_checkpoints_by_edges(edges_df, surface, wells_gdf, sections_gdf):
    wells_out = wells_gdf
    sections_out = sections_gdf
    subset = edges_df[edges_df['surface'] == surface] if edges_df is not None else pd.DataFrame()
    if subset.empty:
        return wells_out, sections_out
    # pozzi
    wells_edges = subset[subset['type'].str.lower() == 'well']
    if wells_gdf is not None and not wells_edges.empty:
        ids = wells_edges['checkpoint_id'].astype(str).tolist()
        if 'ALL' not in ids:
            ids = [i for i in ids if i and i != 'NONE']
            if 'NOME_POZZO' in wells_gdf.columns:
                wells_out = wells_gdf[wells_gdf['NOME_POZZO'].astype(str).isin(ids)]
            else:
                wells_out = wells_gdf[wells_gdf.index.astype(str).isin(ids)]
    # sezioni
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


def build_grid(vertices, spacing=5000):
    xs, ys = vertices[:, 0], vertices[:, 1]
    min_x, max_x = xs.min(), xs.max()
    min_y, max_y = ys.min(), ys.max()
    gx = np.arange(min_x, max_x + spacing, spacing)
    gy = np.arange(min_y, max_y + spacing, spacing)
    GX, GY = np.meshgrid(gx, gy)
    grid_points = np.c_[GX.ravel(), GY.ravel()]
    return GX, GY, grid_points


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
    GX, GY, grid_points = build_grid(vertices, spacing=grid_spacing)

    wells_points = None
    sections_points = None
    if use_wells and wells_shp is not None and not wells_shp.empty:
        wx, wy = extract_points_from_wells(wells_shp)
        wells_points = np.c_[wx, wy]
    if use_sections and sections_shp is not None and not sections_shp.empty:
        lx, ly = sample_lines_gdf(sections_shp, step=line_step)
        if len(lx) > 0:
            sections_points = np.c_[lx, ly]

    combined, wells_w, sections_w = compute_horizontal_weights(
        grid_points, wells_points, sections_points
    )

    df = pd.DataFrame({'x': grid_points[:, 0], 'y': grid_points[:, 1]})
    if wells_points is not None:
        d_w, _ = nearest_distance(grid_points, wells_points)
        df['dist_wells'] = d_w
        if wells_w is not None:
            df['weight_wells'] = wells_w
    if sections_points is not None:
        d_s, _ = nearest_distance(grid_points, sections_points)
        df['dist_sections'] = d_s
        if sections_w is not None:
            df['weight_sections'] = sections_w
    if combined is not None:
        df['weight_combined'] = combined

    df.to_csv(os.path.join(output_dir, f'horizontal_accuracy_grid_{surface_name}.csv'), index=False)

    # Heatmap
    if combined is not None:
        try:
            grid_weights = combined.reshape(GX.shape)
            fig_w = plt.figure(figsize=(10, 8))
            plt.pcolormesh(GX, GY, grid_weights, cmap='viridis', shading='auto')
            plt.colorbar(label='Peso (accuratezza orizzontale)')
            if wells_points is not None:
                plt.scatter(wells_points[:, 0], wells_points[:, 1], s=8, color='red', label='Pozzi')
            if sections_points is not None:
                plt.scatter(sections_points[:, 0], sections_points[:, 1], s=4, color='orange', label='Sezioni (campionate)')
            if (wells_points is not None) or (sections_points is not None):
                plt.legend(loc='lower left', fontsize=8)
            plt.title('Accuratezza orizzontale (IDW vincoli)')
            plt.savefig(os.path.join(output_dir, f'horizontal_accuracy_idw_{surface_name}.png'), dpi=300, bbox_inches='tight')
            plt.close(fig_w)
        except Exception as e:
            warnings.warn(f"Impossibile salvare heatmap pesi: {e}")

    # Istogrammi distanze
    try:
        fig_h = plt.figure(figsize=(8, 6))
        if wells_points is not None:
            plt.hist(df['dist_wells'], bins=40, alpha=0.6, label='Pozzi')
        if sections_points is not None:
            plt.hist(df['dist_sections'], bins=40, alpha=0.6, label='Sezioni')
        plt.xlabel('Distanza dal vincolo (m)')
        plt.ylabel('Occorrenze')
        plt.title('Distribuzione delle distanze ai vincoli')
        if (wells_points is not None) or (sections_points is not None):
            plt.legend()
        plt.savefig(os.path.join(output_dir, f'distance_histogram_{surface_name}.png'), dpi=300, bbox_inches='tight')
        plt.close(fig_h)
    except Exception as e:
        warnings.warn(f"Impossibile salvare istogramma distanze: {e}")

    return {
        'grid_points': grid_points,
        'weights': combined,
        'weights_wells': wells_w,
        'weights_sections': sections_w
    }


def visualize_data(vertices, triangles, wells_shp, sections_shp, apply_smoothing=False,
                   smoothing_iterations=3, smoothing_factor=0.2, crs='EPSG:6708',
                   output_filename='model_dataset.png'):
    """
    Visualizzazione avanzata e stilizzata dei dati della superficie GOCAD (solo ingombro),
    pozzi e sezioni con miglioramenti estetici per una presentazione professionale.
    Versione ottimizzata per prestazioni migliori usando un poligono di contorno.
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

    start_time = time.time()
    output_dir = "output_results"
    os.makedirs(output_dir, exist_ok=True)

    # Imposta uno stile; fallback se il tema seaborn recente non e' disponibile
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
            print(f"Smoothing applicato alle superfici (iterazioni: {smoothing_iterations}, fattore: {smoothing_factor})")

    if vertices is not None and len(vertices) > 0:
        if len(vertices.shape) == 2 and vertices.shape[1] >= 2:
            try:
                points_2d = vertices[:, :2]
                min_x, min_y = np.min(points_2d, axis=0)
                max_x, max_y = np.max(points_2d, axis=0)
                rect_coords = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
                rect_polygon = Polygon(rect_coords)
                x, y = rect_polygon.exterior.xy
                ax_2d.fill(x, y, color='steelblue', alpha=0.1, label='Ingombro superfici')
                ax_2d.plot(x, y, color='steelblue', linewidth=1.5, alpha=0.7)
                print("Ingombro superfici visualizzato come rettangolo (super-ottimizzato)")
            except Exception as e:
                print(f"Errore nella visualizzazione dell'ingombro ottimizzato: {e}")
                try:
                    points_2d = vertices[:, :2]
                    min_x, min_y = np.min(points_2d, axis=0)
                    max_x, max_y = np.max(points_2d, axis=0)
                    ax_2d.plot([min_x, max_x, max_x, min_x, min_x],
                               [min_y, min_y, max_y, max_y, min_y],
                               color='steelblue', linewidth=1.5, alpha=0.7,
                               label='Ingombro superfici (box)')
                except Exception as e2:
                    print(f"Fallback a visualizzazione punti: {e2}")
                    if len(vertices) > 500:
                        sampling_rate = max(1, len(vertices) // 500)
                        sampled_vertices = vertices[::sampling_rate]
                        ax_2d.scatter(sampled_vertices[:, 0], sampled_vertices[:, 1], s=2, alpha=0.6,
                                      c='steelblue', label='Vertici GOCAD (campionati)', edgecolors='none')
                    else:
                        ax_2d.scatter(vertices[:, 0], vertices[:, 1], s=2, alpha=0.6,
                                      c='steelblue', label='Vertici GOCAD', edgecolors='none')
        else:
            print(f"Avviso: vertices ha una forma non valida per la visualizzazione: {vertices.shape}")

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
                                      markersize=10, label='Pozzi', markeredgecolor='white')]

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
            print(f"Errore durante la visualizzazione avanzata dei pozzi: {e}")
            wells_shp.plot(ax=ax_2d, color='blue', markersize=50, label='Pozzi')

    if sections_shp is not None and not sections_shp.empty:
        try:
            sections_shp.plot(ax=ax_2d, alpha=0, label='_nolegend_')

            section_legend = Line2D([0], [0], color='crimson', lw=2, label='Sezioni')
            if 'legend_elements' in locals():
                legend_elements.append(section_legend)
            else:
                legend_elements = [section_legend]

            for idx, row in sections_shp.iterrows():
                if isinstance(row.geometry, (LineString, MultiLineString)):
                    sections_shp.iloc[[idx]].plot(ax=ax_2d, color='salmon', linewidth=6,
                                                  alpha=0.3, zorder=7)
                    sections_shp.iloc[[idx]].plot(ax=ax_2d, color='crimson', linewidth=2.5,
                                                  alpha=0.9, zorder=8)

                    if isinstance(row.geometry, LineString):
                        x, y = row.geometry.xy
                        ax_2d.plot(x, y, color='white', linewidth=1, linestyle=(0, (5, 5)),
                                   alpha=0.7, zorder=9)
                    else:
                        for geom in row.geometry.geoms:
                            x, y = geom.xy
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
            print(f"Errore durante la visualizzazione avanzata delle sezioni: {e}")
            sections_shp.plot(ax=ax_2d, color='red', linewidth=2, label='Sezioni')

    stats_info = []

    if triangles is not None and len(triangles) > 0:
        num_triangles = len(triangles)
        num_vertices = len(vertices) if vertices is not None else 0
        stats_info.append(f"Triangoli: {num_triangles:,}")

        if vertices is not None and len(vertices.shape) == 2 and vertices.shape[1] >= 3:
            z_min, z_max = np.min(vertices[:, 2]), np.max(vertices[:, 2])
            z_mean = np.mean(vertices[:, 2])
            stats_info.append(f"Elevazione min: {z_min:.2f} m")
            stats_info.append(f"Elevazione max: {z_max:.2f} m")

    if wells_shp is not None and not wells_shp.empty:
        num_wells = len(wells_shp)
        stats_info.append(f"Pozzi: {num_wells}")

    if sections_shp is not None and not sections_shp.empty:
        num_sections = len(sections_shp)
        stats_info.append(f"Sezioni: {num_sections}")

    ax_2d.set_xlabel('X (m)', fontsize=12, fontweight='bold')
    ax_2d.set_ylabel('Y (m)', fontsize=12, fontweight='bold')
    ax_2d.set_title('Ingombro Modello Geologico, Pozzi e Sezioni',
                    fontsize=16, fontweight='bold', pad=20)

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

        ax_2d.text(0.98, 1.02, "STATISTICHE DEL MODELLO",
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
        ax_2d.legend(handles=legend_elements, loc='upper left',
                     frameon=True, framealpha=0.9, edgecolor='lightgray')

    ax_2d.text(0.02, 0.02, f"Sistema di coordinate: {crs}",
               transform=ax_2d.transAxes,
               fontsize=8,
               verticalalignment='bottom',
               horizontalalignment='left',
               bbox=dict(boxstyle='round,pad=0.3',
                         facecolor='white',
                         edgecolor='lightgray',
                         alpha=0.8))

    fig.text(0.99, 0.01, f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
             fontsize=7, color='gray', ha='right', va='bottom')

    plt.tight_layout()

    execution_time = time.time() - start_time
    print(f"Tempo di esecuzione: {execution_time:.2f} secondi")

    output_path = os.path.join(output_dir, output_filename)
    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Figura salvata in: {output_path}")

    plt.show()
    plt.close(fig)
    return fig


def smooth_surface(vertices, triangles, iterations=3, factor=0.2):
    """
    Applica smoothing laplaciano alla superficie
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
