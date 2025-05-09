# GOCAD Surface Accuracy Analysis

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Release](https://img.shields.io/badge/version-0.1.0-blue)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/BaterHub/GeoSurface_Accuracy/blob/main/GeoSurface_Accuracy.ipynb)

Questo progetto implementa un flusso di lavoro per l'analisi dell'accuratezza di superfici geologiche in formato GOCAD (.ts). Il sistema valuta la qualità del modello geologico calcolando indici di accuratezza orizzontale e verticale su una griglia definita dall'estensione delle superfici e rispetto all'andamento delle sezioni sismiche e delle localizzazioni dei pozzi utilizzati forniti come shapefile.

## Funzionalità principali

- Lettura di superfici in formato GOCAD .ts
- Definizione automatica della griglia di valutazione basata sull'estensione del modello
- Calcolo dell'accuratezza orizzontale basata sulla distanza dai punti di controllo (linee e punti in formato shapefile)
- Calcolo dell'accuratezza verticale basata sulla variazione di profondità
- Generazione di mappe di accuratezza in formato GOCAD .ts e JPG
- Esportazione dei risultati in formato CSV

## Requisiti

- Python 3.6+
- pandas
- geopandas
- numpy
- matplotlib
- scipy
- scikit-learn
- pyproj

Puoi installare le dipendenze con:

```bash
pip install -r requirements.txt
```

## Struttura del progetto

```
gocad-accuracy-analysis/
├── notebook.ipynb            # Questo notebook
├── input_surfaces/           # Directory per i file GOCAD .ts
│   ├── multi_surface1.ts     # File TS con più superfici
│   └── surface2.ts
├── control_points/           # Directory per gli shapefile di controllo
│   ├── boreholes.shp        # Punti di borehole
│   ├── boreholes.dbf
│   ├── boreholes.shx
│   ├── boreholes.prj
│   ├── sections.shp         # Punti di sezione
│   ├── sections.dbf
│   ├── sections.shx
│   ├── sections.prj
│   ├── maps.shp            # Punti di mappa
│   ├── maps.dbf
│   ├── maps.shx
│   └── maps.prj
└── output_results/          # Directory per i risultati
    ├── accuracy_output.csv
    ├── horizontal_accuracy.ts
    ├── vertical_accuracy.ts
    ├── delta_depth.ts
    ├── horizontal_accuracy.jpg
    ├── vertical_accuracy.jpg
    └── delta_depth.jpg
```

## Utilizzo in locale

1. Clona il repository:

```bash
git clone https://github.com/yourusername/gocad-accuracy-analysis.git
cd gocad-accuracy-analysis
```

2. Installa le dipendenze:

```bash
pip install -r requirements.txt
```

3. Inserisci i file GOCAD .ts nella directory `input_surfaces`

4. Esegui il notebook con Jupyter:

```bash
jupyter notebook notebook.ipynb
```

5. I risultati saranno salvati nella directory `output_results`


## 🚀 Utilizzo su colab

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/BaterHub/GeoSurface_Accuracy/blob/main/GeoSurface_Accuracy.ipynb)

1. **Apertura notebook**:
    Clicca sul badge "Open in Colab" per aprire il notebook
2. **Configurazione iniziale**:
    Carica il workspace eseguendo la prima cella 
3. **Preparazione files**:
    Carica il pacchetto dati delle superfici del modello 3D (file horizon.ts) all'interno della cartella "working_files_folder"
4. **Esecuzione notebook**:
    Posizionati nella seconda cella e lancia lo script con "ctrl + F10" oppure dal menù "Runtime > Run cell and below"
5. **Lettura log file**:
    Al termine del RUN verrà generato un log_file all'interno della cartella_files che conterrà il relativo report.

## Classificazione delle superfici

Per consentire una corretta classificazione delle superfici, assicurati che i nomi dei file contenenti le coordinate delle linee e dei punti di controllo contengano una delle seguenti indicazioni:

- **Pozzi/Boreholes**: Nomi contenenti "borehole", "well", "pozzo"
- **Sezioni**: Nomi contenenti "section", "sezione", "seismic_line", "line"
- **Mappe**: Nomi contenenti "map", "mappa"

## Dettagli sull'algoritmo

### Accuratezza orizzontale
L'accuratezza orizzontale è calcolata utilizzando la distanza dai punti..... DA TERMINARE