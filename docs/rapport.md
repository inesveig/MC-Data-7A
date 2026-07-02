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
> fonctionne de bout en bout. La mesure qui compte est celle sur RSNA réel ci-dessous.

### 5bis. Résultats mesurés (RSNA réel, n = 24, mode baseline)

Sous-échantillon équilibré (8 cas/classe) tiré de `data/rsna_index.csv` (labels
officiels du RSNA Pneumonia Detection Challenge), inférence **réelle** MedGemma-4b
(`AI_MOCK=0`, pas de mock) sur DICOM avec fenêtrage VOI LUT
(`src/preprocessing.py::_dicom_to_image`). Reproduction :

```bash
python eval/run_batch.py --cases data/rsna_eval_cases.csv --mode baseline \
  --db-path /tmp/eval.sqlite --out /tmp/baseline_real.jsonl
```

| Mode | n | Accuracy | Macro-F1 | JSON valide | Warning | Taux incertitude |
|---|---|---|---|---|---|---|
| baseline | 24 | **0.625** | **0.57** | 100 % | 100 % | 8 % |

Matrice de confusion (`eval/rsna_real_eval/baseline_confusion.json`) :

|  | pred normal | pred suspected_opacity | pred uncertain |
|---|---|---|---|
| **normal** (n=8) | 7 | 1 | 0 |
| **suspected_opacity** (n=8) | 0 | 7 | 1 |
| **uncertain** (n=8) | 1 | 6 | 1 |

> **Lecture honnête.** Contrairement au jeu synthétique, ces scores sont **imparfaits
> et attendus comme tels** : c'est la première mesure crédible du projet, encore sans
> valeur clinique (prototype pédagogique) mais représentative du comportement réel du
> modèle. Le point marquant : la classe `uncertain` de RSNA (cas ambigus même pour
> l'annotateur humain) est presque systématiquement classée `suspected_opacity` (6/8)
> — le modèle sur-affirme là où l'attendu est l'abstention. Le taux d'incertitude du
> modèle (8 %) est bien plus bas que le taux réel de cas ambigus (33 % dans RSNA),
> signe que le prompt actuel n'est pas assez conservateur. Comparaison avec le prompt
> `improved` non refaite sur ce sous-échantillon (coût de calcul local trop élevé,
> voir §8).

## 6. Analyse d'erreurs (taxonomie)

La taxonomie est en place (`eval/error_register_template.csv`,
`eval/build_error_register.py`) : `FN` faux négatif, `FP` faux positif, `UA` incertitude
acceptable, `JF` erreur de format JSON, `HT` hallucination textuelle. Sur le jeu
synthétique, aucun cas n'est déclenché (jeu séparable).

**Registre rempli sur les 24 cas RSNA réels**
(`eval/rsna_real_eval/baseline_error_register.csv`) : 15 `OK`, 7 `FP`, 1 `FN`, 1 `UA`,
0 `JF`. Aucune hallucination textuelle franche (`HT`) repérée sur cette relecture — les
justifications restent descriptives et cohérentes avec des motifs radiologiques
plausibles, mais une revue par un vrai radiologue serait nécessaire pour trancher
définitivement (hors périmètre du prototype). Deux enseignements qualitatifs :

- **7 FP à confiance moyenne (0.3–0.6) sur des cas `uncertain`** : le modèle décrit des
  opacités avec un langage hésitant (« could be suggestive of », « not definitive »)
  mais ne bascule pas vers `uncertain` malgré une confiance déjà basse — le seuil de
  confiance du garde-fou (< 0.6) n'est pas assez strict pour ce comportement.
- **1 FN à haute sévérité** (`bbe95fb0…`) : confiance 0.95 sur `normal` alors que le
  modèle mentionne lui-même la présence probable de tubes/lignes (patient intubé)
  pouvant masquer une anomalie — sur-confiance sur un facteur de confusion qu'il a
  pourtant identifié. Cas à surveiller en priorité si le projet évolue.

Le détail cas par cas (justification MedGemma incluse) est dans le registre CSV.

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

- Évaluation RSNA réelle faite sur **24 cas** (§5bis), pas 20-30 sur les trois modes :
  taille limitée par le temps de calcul en local (Mac, pas de GPU dédié — chaque
  inférence prend ~35-70s, un process isolé par image pour éviter la saturation
  mémoire). Élargir l'échantillon nécessiterait un GPU cloud (Colab/AWS).
- Comparaison baseline/improved **non refaite sur RSNA réel** : le mode `improved`
  doublerait le temps de calcul (48 inférences) ; seule la comparaison sur jeu
  synthétique (neutre, voir §5) est disponible pour l'instant.
- Pas de calibration de probabilité : la « confiance » vient directement du JSON
  produit par le modèle (baseline) ou est dérivée heuristiquement de la gravité
  (plateforme web) — dans les deux cas, ce n'est pas une probabilité calibrée.
- Registre d'erreurs rempli automatiquement (FN/FP/UA/JF) + commentaires qualitatifs
  rédigés à partir des justifications du modèle, mais **pas de relecture par un
  radiologue** pour confirmer les codes `HT` (hors périmètre du prototype).
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

Suites de la plateforme (extension) :

```bash
cd backend && python manage.py test analyses accounts   # 24 tests (mapping, vue, KPI, avis, compte)
cd ai && AI_MOCK=1 python -m pytest -q                   # 31 tests (DICOM/PNG, parsing, API)
```

Éval RSNA réelle (§5bis, artefacts dans `eval/rsna_real_eval/`) :

```bash
python eval/run_batch.py --cases data/rsna_eval_cases.csv --mode baseline \
  --db-path /tmp/eval.sqlite --out /tmp/baseline_real.jsonl
python eval/build_error_register.py --predictions eval/rsna_real_eval/baseline_predictions.csv \
  --out /tmp/register.csv
```

État V1 : smoke test **8/8 vert**, évaluation jouet produisant tous les artefacts MUST,
**évaluation RSNA réelle faite** (24 cas, accuracy 0.625, registre d'erreurs commenté),
plateforme web **fonctionnelle de bout en bout** en mode mock, couverte par **63 tests**
(pipeline + backend + service IA).
