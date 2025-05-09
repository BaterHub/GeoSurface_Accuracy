# GOCAD Surface Accuracy Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Questo progetto implementa un flusso di lavoro per l'analisi dell'accuratezza di superfici geologiche in formato GOCAD (.ts). Il sistema valuta la qualità del modello geologico calcolando indici di accuratezza orizzontale e verticale su una griglia definita dall'estensione delle superfici.

## Funzionalità principali

- Lettura di superfici in formato GOCAD .ts
- Definizione automatica della griglia di valutazione basata sull'estensione del modello
- Calcolo dell'accuratezza orizzontale basata sulla distanza dai punti di controllo
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
├── notebook.ipynb            # Notebook principale
├── requirements.txt          # Requisiti Python
├── input_surfaces/           # Directory per i file GOCAD .ts
│   ├── surface1.ts
│   ├── surface2.ts
│   └── ...
└── output_results/           # Directory per i risultati
    ├── accuracy_output.csv
    ├── horizontal_accuracy.ts
    ├── vertical_accuracy.ts
    ├── delta_depth.ts
    ├── horizontal_accuracy.jpg
    ├── vertical_accuracy.jpg
    └── delta_depth.jpg
```

## Utilizzo

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

## Classificazione delle superfici

Per consentire una corretta classificazione delle superfici, assicurati che i nomi dei file o delle superfici GOCAD contengano una delle seguenti indicazioni:

- **Pozzi/Boreholes**: Nomi contenenti "borehole", "well", "pozzo"
- **Sezioni**: Nomi contenenti "section", "sezione"
- **Mappe**: Nomi contenenti "map", "mappa"

## Dettagli sull'algoritmo

### Accuratezza orizzontale
L'accuratezza orizzontale è calcolata utilizzando la distanza dai punti..... DA TERMINARE