# Assistant Radiologue Virtuel Responsable

> **Filière Data — EFREI Mastercamp 2025-2026**

Prototype pédagogique d'IA médicale multimodale pour l'analyse prudente de radiographies thoraciques.

---

> **⚠️ Position non clinique.** Ce dépôt n'est pas un dispositif médical. Il ne doit jamais être utilisé pour diagnostiquer, trier ou orienter un patient. Toute sortie est un résultat expérimental à vérifier par un professionnel qualifié.

---

## Contrat du projet

| Élément | Cadrage |
|---|---|
| Entrée | Une radiographie thoracique frontale |
| Sorties | `normal`, `suspected_opacity`, `uncertain` |
| Modèle | MedGemma 4B (baseline par prompting) |
| Données | RSNA Pneumonia — publiques, dé-identifiées |
| Finalité | Prototype éducatif, pas d'aide au diagnostic réelle |

## Démarrage rapide

```bash
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# Lancer l'API
uvicorn api.main:app --reload

# Lancer l'interface
streamlit run app/streamlit_app.py
```

## Smoke test

```bash
pip install -r requirements-test.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/ -q
```

## Organisation

```
assistant-radiologue-virtuel/
├── README.md
├── docs/          # architecture, éthique, évaluation
├── data/          # images synthétiques et smoke test (non commitées)
├── prompts/       # prompt baseline, prompt amélioré, schéma JSON
├── src/           # inférence, garde-fous, métriques, SQLite
├── api/           # FastAPI /predict
├── app/           # Interface Streamlit
├── eval/          # évaluation, CSV, registre d'erreurs
├── tests/         # smoke tests
├── notebooks/     # notebooks baseline et comparaison
└── finetuning/    # stubs expérimentaux (non obligatoires)
```

## Données

Dataset : **RSNA Pneumonia Detection Challenge** (Kaggle)  
Licence : CC BY-NC-SA 4.0  
Source : https://www.kaggle.com/c/rsna-pneumonia-detection-challenge  
Traitement : images dé-identifiées, aucune donnée patient réelle commitée.

## Points de vigilance

- Ne pas inventer d'information clinique absente de l'image.
- Ne jamais supprimer la classe `uncertain` — c'est un garde-fou.
- Ne jamais commiter d'images patient réelles.
- Ne pas présenter ce prototype comme validé médicalement.
