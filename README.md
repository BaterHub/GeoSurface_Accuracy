# GeoSurface Accuracy

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Release](https://img.shields.io/badge/version-0.2.0-blue)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/BaterHub/GeoSurface_Accuracy/blob/main/GeoSurface_Accuracy.ipynb)

Notebook e utilità per stimare l'accuratezza orizzontale di superfici geologiche in formato GOCAD (.ts), usando pozzi e sezioni (shapefile) con pesi ID = 1/(1 + r^p) normalizzati (IDW) su una griglia di valutazione.

## Funzionalità
- Lettura di file .ts multi-superficie e creazione griglia (passo configurabile, clip su hull).
- Calcolo IDW per ordine di vincolo (pozzi=1, sezioni=2, mappe=3) e media finale.
- Mapping dei vincoli per superficie via edge list (`surface_checkpoint_edges.csv`) e flag (`surface_data_mapping.csv`).
- Output per superficie: CSV griglia, PNG heatmap, HTML interattivo, istogramma distanze, `model_dataset_<surface>.png`.
- Output complessivo: `model_dataset.png` con ingombro modello e dati.

## Requisiti
- Python 3.10+
- pandas, geopandas, numpy, matplotlib, scipy, scikit-learn, pyproj, plotly

Installa con:
```bash
pip install -r requirements.txt
```

## Struttura essenziale
- `GeoSurface_Accuracy.ipynb` – notebook principale.
- `files_utils.py` – funzioni (lettura .ts, IDW, plot).
- `working_files_folder/`
  - `horizons.ts` (multi-superficie)
  - `pozzi_idrocarburi.*` (campo `NOME_POZZO`)
  - `linee_sismiche.*` (campo `NOME`)
  - `surface_data_mapping.csv` – flag per superficie: `surface,use_wells,use_sections,use_maps`.
  - `surface_checkpoint_edges.csv` – edge list `surface,checkpoint_id,type` (`type`: well/section/map; `checkpoint_id` deve corrispondere a `NOME_POZZO`/`NOME`; usa `ALL` per includere tutti).
  - `output_results/` – PNG/CSV/HTML generati.

## Uso in locale
```bash
git clone https://github.com/BaterHub/GeoSurface_Accuracy.git
cd GeoSurface_Accuracy
pip install -r requirements.txt
jupyter notebook GeoSurface_Accuracy.ipynb
```
Popola `working_files_folder` con .ts, shapefile e i CSV di mapping, poi esegui il notebook (salta la cella di clonazione Colab).

## Uso su Colab
1. Apri il badge Colab.
2. Esegui la cella “CARICA SPAZIO DI LAVORO” (clona repo).
3. Carica dati e CSV in `working_files_folder`.
4. Esegui dalla cella “LANCIA LO SCRIPT”. Gli output vanno in `output_results`.

## Note sul mapping
- `surface_data_mapping.csv`: per ogni superficie attiva/disattiva l’uso di wells/sections/maps (1/0).
- `surface_checkpoint_edges.csv`: edge list many-to-many superficie–checkpoint con tipo; valori `checkpoint_id` devono matchare i campi degli shapefile; `ALL` per includere tutto il dataset.

## Output
- Per superficie: `model_dataset_<surface>.png`, `horizontal_accuracy_grid_<surface>.csv`, `horizontal_accuracy_idw_<surface>.png`, `interactive_idw_<surface>.html`, `distance_histogram_<surface>.png`.
- Modello complessivo: `model_dataset.png`.
