import os
import re
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from pyproj import Proj, transform
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from sklearn.preprocessing import MinMaxScaler

# ### Funzioni per Leggere Multi-Superfici TS
def read_gocad_ts_multi(file_path):
    """
    Legge un file GOCAD .ts con più superfici e restituisce una lista di superfici.
    
    Parameters:
    -----------
    file_path : str
        Percorso al file .ts
        
    Returns:
    --------
    surfaces : list
        Lista di dizionari, ognuno rappresentante una superficie con:
        - name: nome della superficie
        - type: tipo della superficie
        - x, y, z: coordinate dei vertici
    """
    surfaces = []
    current_surface = None
    
    with open(file_path, 'r') as f:
        for line in f:
            # Inizio di una nuova superficie
            if line.startswith('GOCAD TSurf'):
                if current_surface is not None:
                    surfaces.append(current_surface)
                
                current_surface = {
                    'name': 'Unnamed Surface',
                    'type': 'unknown',
                    'x': [],
                    'y': [],
                    'z': []
                }
            
            # Nome della superficie
            elif line.startswith('name:'):
                if current_surface is not None:
                    current_surface['name'] = line.strip().split('name:')[1].strip()
                    current_surface['type'] = get_surface_type(current_surface['name'])
            
            # Vertici
            elif line.startswith('VRTX'):
                parts = line.strip().split()
                if len(parts) >= 5 and current_surface is not None:
                    current_surface['x'].append(float(parts[2]))
                    current_surface['y'].append(float(parts[3]))
                    current_surface['z'].append(float(parts[4]))
    
    # Aggiungi l'ultima superficie
    if current_surface is not None and len(current_surface['x']) > 0:
        surfaces.append(current_surface)
    
    # Converti liste in array numpy
    for surface in surfaces:
        surface['x'] = np.array(surface['x'])
        surface['y'] = np.array(surface['y'])
        surface['z'] = np.array(surface['z'])
    
    return surfaces


# ### Funzioni per Leggere Shapefile di Controllo
def read_control_shapefile(file_path, z_field=None, type_field=None):
    """
    Legge uno shapefile di punti di controllo e restituisce un GeoDataFrame.
    
    Parameters:
    -----------
    file_path : str
        Percorso allo shapefile (.shp)
    z_field : str, optional
        Nome del campo contenente i valori z (profondità)
    type_field : str, optional
        Nome del campo contenente il tipo di punto (borehole, section, map)
        
    Returns:
    --------
    gdf : GeoDataFrame
        GeoDataFrame con i punti e le proprietà
    """
    gdf = gpd.read_file(file_path)
    
    # Verifica che ci siano geometrie di punti
    if not all(gdf.geometry.type == 'Point'):
        raise ValueError("Lo shapefile deve contenere solo geometrie di punto")
    
    # Se z_field non è specificato, cerca campi comuni
    if z_field is None:
        possible_z_fields = ['z', 'depth', 'elevation', 'profondita', 'quota']
        for field in possible_z_fields:
            if field in gdf.columns:
                z_field = field
                break
    
    # Se type_field non è specificato, cerca campi comuni
    if type_field is None:
        possible_type_fields = ['type', 'tipo', 'source', 'fonte']
        for field in possible_type_fields:
            if field in gdf.columns:
                type_field = field
                break
    
    # Estrai coordinate x, y
    gdf['Longitude'] = gdf.geometry.x
    gdf['Latitude'] = gdf.geometry.y
    
    # Aggiungi campo z se trovato
    if z_field is not None and z_field in gdf.columns:
        gdf['z'] = gdf[z_field]
    else:
        gdf['z'] = 0  # Valore di default
    
    # Aggiungi tipo se trovato
    if type_field is not None and type_field in gdf.columns:
        gdf['type'] = gdf[type_field].apply(lambda x: get_surface_type(str(x)))
    else:
        # Prova a determinare il tipo dal nome del file
        file_name = os.path.basename(file_path)
        surface_type = get_surface_type(file_name)
        gdf['type'] = surface_type
    
    return gdf

# ### Flusso Principale
def main(input_dir, output_dir, grid_spacing=1000, 
         borehole_shp=None, section_shp=None, map_shp=None):
    """
    Flusso di lavoro principale per l'analisi dell'accuratezza delle superfici GOCAD.
    
    Parameters:
    -----------
    input_dir : str
        Directory contenente i file GOCAD .ts
    output_dir : str
        Directory per i file di output
    grid_spacing : float
        Spaziatura della griglia in metri
    borehole_shp : str, optional
        Percorso allo shapefile dei borehole
    section_shp : str, optional
        Percorso allo shapefile delle sezioni
    map_shp : str, optional
        Percorso allo shapefile delle mappe
    """
    # Crea la directory di output se non esiste
    os.makedirs(output_dir, exist_ok=True)
    
    # Lista tutti i file .ts nella directory di input
    ts_files = [f for f in os.listdir(input_dir) if f.endswith('.ts')]
    
    if not ts_files:
        print("Nessun file .ts trovato nella directory di input.")
        return
    
    # Leggi tutte le superfici
    surfaces_data = []
    for ts_file in ts_files:
        file_path = os.path.join(input_dir, ts_file)
        surfaces = read_gocad_ts_multi(file_path)
        surfaces_data.extend(surfaces)
    
    print(f"Numero di superfici lette: {len(surfaces_data)}")
    
    # Leggi i punti di controllo dagli shapefile
    control_points = {
        'borehole': None,
        'section': None,
        'map': None
    }
    
    # Carica shapefile dei borehole se specificato
    if borehole_shp and os.path.exists(borehole_shp):
        control_points['borehole'] = read_control_shapefile(borehole_shp)
        print(f"Pozzi (boreholes) caricati: {len(control_points['borehole'])}")
    
    # Carica shapefile delle sezioni se specificato
    if section_shp and os.path.exists(section_shp):
        control_points['section'] = read_control_shapefile(section_shp)
        print(f"Sezioni (sections) caricati: {len(control_points['section'])}")
    
    # Carica shapefile delle mappe se specificato
    if map_shp and os.path.exists(map_shp):
        control_points['map'] = read_control_shapefile(map_shp)
        print(f"Mappe (maps) caricati: {len(control_points['map'])}")
    
    # Crea la griglia di valutazione
    grid_x, grid_y = create_evaluation_grid(surfaces_data, grid_spacing)
    print(f"Numero di punti nella griglia: {len(grid_x)}")
    
    # Converti in GeoDataFrame
    df_grid = pd.DataFrame({'Longitude': grid_x, 'Latitude': grid_y})
    gdf_grid = gpd.GeoDataFrame(df_grid, geometry=gpd.points_from_xy(df_grid.Longitude, df_grid.Latitude))
    
    # Prepara i dati per il calcolo dell'accuratezza
    def prepare_control_data(gdf, control_type):
        if gdf is None:
            return np.array([]), np.array([]), np.array([])
        
        # Filtra per tipo se necessario (nel caso lo shapefile contenga tutti i tipi)
        if 'type' in gdf.columns:
            gdf = gdf[gdf['type'] == control_type]
        
        return gdf.Longitude.values, gdf.Latitude.values, gdf.z.values
    
    # Prepara i punti di controllo
    X_boreholes, y_boreholes, Z_boreholes = prepare_control_data(control_points['borehole'], 'borehole')
    X_sections, y_sections, Z_sections = prepare_control_data(control_points['section'], 'section')
    X_maps, y_maps, Z_maps = prepare_control_data(control_points['map'], 'map')
    
    # Crea GeoDataFrames per il calcolo delle distanze
    def create_control_gdf(x, y):
        if len(x) == 0:
            return None
        
        df = pd.DataFrame({'Longitude': x, 'Latitude': y})
        return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude))
    
    gdf_boreholes = create_control_gdf(X_boreholes, y_boreholes)
    gdf_sections = create_control_gdf(X_sections, y_sections)
    gdf_maps = create_control_gdf(X_maps, y_maps)
    
    # Calcola accuratezza orizzontale (solo se ci sono punti di controllo)
    if gdf_boreholes is not None or gdf_sections is not None or gdf_maps is not None:
        df_H = calculate_horizontal_accuracy(
            gdf_grid, 
            gdf_boreholes if gdf_boreholes is not None else gdf_grid.head(0).copy(),
            gdf_sections if gdf_sections is not None else gdf_grid.head(0).copy(),
            gdf_maps if gdf_maps is not None else gdf_grid.head(0).copy()
        )
    else:
        print("Nessun punto di controllo fornito - verrà calcolata solo la griglia")
        df_H = gdf_grid.copy()
        df_H['horizontal accuracy'] = 0.5  # Valore di default
    
    # Calcola accuratezza verticale (solo se ci sono punti di controllo con valori z)
    has_z_data = (len(Z_boreholes) > 0 or len(Z_sections) > 0 or len(Z_maps) > 0)
    
    if has_z_data:
        df_output = calculate_vertical_accuracy(
            grid_x, grid_y,
            (X_boreholes, y_boreholes), Z_boreholes,
            (X_sections, y_sections), Z_sections,
            (X_maps, y_maps), Z_maps,
            df_H
        )
    else:
        print("Nessun dato z fornito - verrà calcolata solo l'accuratezza orizzontale")
        df_output = df_H.copy()
        df_output['vertical accuracy'] = 0.5  # Valore di default
        df_output['delta depth'] = 0
    
    # Salva risultati in formato CSV
    output_csv = os.path.join(output_dir, "accuracy_output.csv")
    df_output.to_csv(output_csv, index=False)
    print(f"Risultati salvati in: {output_csv}")
    
    # Esporta in formato GOCAD .ts
    export_to_gocad_ts(
        df_output, 
        os.path.join(output_dir, "horizontal_accuracy.ts"), 
        "horizontal accuracy",
        z_factor=1000
    )
    
    export_to_gocad_ts(
        df_output, 
        os.path.join(output_dir, "vertical_accuracy.ts"), 
        "vertical accuracy",
        z_factor=1000
    )
    
    export_to_gocad_ts(
        df_output, 
        os.path.join(output_dir, "delta_depth.ts"), 
        "delta depth",
        z_factor=1
    )
    
    # Genera grafici
    plot_horizontal_accuracy(df_output, output_dir)
    plot_vertical_accuracy(df_output, output_dir)
    plot_delta_depth(df_output, output_dir)
    
    print("Analisi completata con successo!")
