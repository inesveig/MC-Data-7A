# Mini-rapport — Assistant radiologue virtuel responsable (V1)

> **Filière Data — EFREI — 2025-2026**
> Prototype pédagogique, **non clinique**. Aucune sortie ne doit servir à diagnostiquer, trier ou orienter un patient.

Ce rapport documente la **première version livrable** du projet : périmètre, données,
méthode, garde-fous, résultats mesurés, analyse d'erreurs et limites. Il couvre le
niveau **MUST** (baseline reproductible, JSON valide, warning, logs, métriques) et
amorce le niveau **SHOULD** (prompt amélioré, règle d'incertitude, comparaison).

---

## 1. Contrat et périmètre

| Élément | Cadrage retenu |
|---|---|
| Entrée | Une radiographie thoracique frontale (PNG ou DICOM) |
| Sorties | `normal`, `suspected_opacity`, `uncertain` |
| Preuve | JSON valide, warning non clinique, logs SQLite, métriques CSV/JSON |
| Données | RSNA (public) + cas synthétiques fournis (validation logicielle) |
| Finalité | Prototype éducatif — **pas** une aide au diagnostic réelle |

La V1 ne cherche pas la performance médicale. Elle démontre une **méthode** :
périmètre limité, chaîne reproductible, garde-fous explicites, évaluation traçable.

## 2. Données

- **RSNA Pneumonia Detection Challenge** (Kaggle, 2018) : 26 684 radios DICOM
  1024×1024, indexées localement dans `data/rsna_index.csv` (dataset non redistribué,
  voir `.gitignore`). Mapping vers le contrat : `Normal → normal`,
  `Lung Opacity → suspected_opacity`, `No Lung Opacity / Not Normal → uncertain`.
- **Cas synthétiques** (`data/synthetic_cases.csv`, `data/sample_images/`) : 30 images
  jouet (10 par classe) servant **uniquement** à valider le pipeline logiciel. Un score
  parfait sur ce jeu ne mesure aucune capacité clinique.

## 3. Méthode et chaîne

1. **Prétraitement** (`src/preprocessing.py`) : décodage DICOM/PNG, normalisation,
   redimensionnement.
2. **Inférence baseline** (`src/inference.py`, `src/medgemma_baseline.py`) : prompt
   structuré (`prompts/baseline_prompt.txt`) demandant un JSON conforme au schéma
   (`prompts/json_schema.md`). Un backend `toy` déterministe permet de tester la chaîne
   sans modèle lourd.
3. **Garde-fous** (`src/guardrails.py`) : validation du JSON, ajout systématique du
   **warning non clinique**, bascule vers `uncertain` quand la confiance est faible ou
   la sortie douteuse.
4. **Métriques et traçabilité** (`src/metrics.py`, `src/database.py`) : accuracy,
   macro-F1, taux de JSON valide, taux de warning, taux d'incertitude, journalisés en
   SQLite.
5. **Évaluation** (`eval/run_evaluation.py`) : compare `baseline` vs `improved`
   (prompt amélioré) et écrit prédictions, matrices de confusion et résumé.

Reproduction :

```bash
python eval/run_evaluation.py --mode toy \
  --out-dir /tmp/arvi-eval --db-path /tmp/arvi-evidence.sqlite
```

## 4. Garde-fous

- **Warning obligatoire** sur chaque sortie (position non clinique).
- **Classe `uncertain` conservée** : c'est un garde-fou, pas un échec. Elle capte les
  signes faibles, les images de qualité limitée et les cas ambigus.
- **JSON strict** : toute sortie non parsable est traitée comme une erreur (`JF`), pas
  masquée.

## 5. Résultats mesurés (jeu synthétique, n = 30)

| Mode | n | Accuracy | Macro-F1 | JSON valide | Warning | Taux incertitude |
|---|---|---|---|---|---|---|
| baseline | 30 | 1.00 | 1.00 | 100 % | 100 % | 33 % |
| improved | 30 | 1.00 | 1.00 | 100 % | 100 % | 33 % |

Matrice de confusion (baseline) : diagonale parfaite (10/10 par classe).

> **Lecture honnête.** Ces scores parfaits sont **attendus** et **sans valeur
> médicale** : le jeu synthétique est construit pour être séparable et sert seulement à
> prouver que la chaîne logicielle (chargement → JSON → warning → métriques → logs)
> fonctionne de bout en bout. La comparaison baseline/improved est neutre sur ce jeu
> trivial ; elle prendra son sens sur un sous-ensemble RSNA annoté (étape suivante).

## 6. Analyse d'erreurs (taxonomie)

La taxonomie est en place (`eval/error_register_template.csv`,
`eval/build_error_register.py`) : `FN` faux négatif, `FP` faux positif, `UA` incertitude
acceptable, `JF` erreur de format JSON, `HT` hallucination textuelle. Sur le jeu
synthétique, aucun cas n'est déclenché (jeu séparable). Le registre est destiné à être
rempli manuellement sur un échantillon RSNA `final` de 20 à 30 cas commentés pour la
soutenance — en montrant explicitement les échecs, pas seulement les réussites.

## 7. Extension : plateforme web (hors contrat noté)

Une plateforme démontre la chaîne en interactif — vérifiée de bout en bout en mode mock :

`Streamlit (8501) → Django DRF/JWT (8000) → service IA FastAPI (8001, MedGemma)`

- **`ai/`** : `POST /analyze` renvoie anomalie, région, cercle normalisé, gravité 0-10,
  explication. `AI_MOCK=1` développe sans télécharger le modèle.
- **`backend/`** : source de vérité unique (auth JWT, historique, avis médecin, KPI).
  Mappe la sortie riche vers les 3 classes UI Sain/Malade/Incertain
  (`backend/analyses/mapping.py`) : Sain si pas d'anomalie ; Incertain si gravité 1-3 ;
  Malade si ≥ 4.
- **`frontend/streamlit-app/`** : login, upload, résultat cerclé, historique, KPI de
  concordance IA/médecin. Consomme **uniquement** l'API Django.

> La localisation par cercle est **approximative** : MedGemma est un VLM, pas un
> détecteur. Cette couche reste, comme le reste du dépôt, un prototype non clinique.

## 8. Limites et suite

- Résultats mesurés uniquement sur données synthétiques → **aucune conclusion
  clinique**. Prochaine étape : évaluer sur un sous-ensemble RSNA réel annoté.
- Pas de calibration de probabilité : la « confiance » est dérivée heuristiquement de
  la gravité.
- Comparaison baseline/improved à re-mesurer sur un jeu non trivial.
- **COULD** non traité : détection de bounding boxes (mAP/IoU), Grad-CAM, LoRA/QLoRA
  (stubs présents dans `finetuning/`).

## 9. Vérification (smoke test)

```bash
pip install -r requirements-test.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q      # 8 passed
python -m compileall -q src api app eval finetuning tests
python eval/run_evaluation.py --mode toy \
  --out-dir /tmp/arvi-eval --db-path /tmp/arvi-evidence.sqlite
```

État V1 : smoke test **8/8 vert**, évaluation jouet produisant tous les artefacts MUST,
plateforme web **fonctionnelle de bout en bout** en mode mock.
