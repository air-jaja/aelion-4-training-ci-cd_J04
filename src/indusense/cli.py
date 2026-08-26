# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/cli.py
# [PÉDAGOGIE] MODULE  — M23–M24 — interface en ligne de commande et orchestration locale
# [PÉDAGOGIE] RÔLE    — Transformer les fonctions métier en commandes répétables et documentées.
# [PÉDAGOGIE] THÉORIE — la CLI valide les arguments puis délègue au code métier
# [PÉDAGOGIE]           • un code de sortie non nul rend l'échec visible aux scripts et à la CI
# [PÉDAGOGIE]           • une commande idempotente peut être relancée sans état incohérent
# [PÉDAGOGIE] À VOIR  — --help, les logs et le code de sortie doivent suffire à comprendre
# [PÉDAGOGIE]           l'action réalisée.
# [PÉDAGOGIE] PIÈGE   — Mettre toute la logique dans la CLI rend les fonctions difficiles à tester
# [PÉDAGOGIE]           et à réutiliser.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import typer
from loguru import logger

from indusense import __version__
from indusense.config import settings
from indusense.data.loaders import build_dataset, load_incidents, load_pressure, load_temperature
from indusense.features.temporal import add_temporal_features
from indusense.models.tabular import (
    load_model,
    predict_proba,
    save_model,
    select_features,
    train_model,
)

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
app = typer.Typer(help="InduSense Sprint 3 starter CLI")


# [PÉDAGOGIE] BLOC `_load_gold` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : data_dir ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def _load_gold(data_dir: Path) -> pd.DataFrame:
    temp = load_temperature(data_dir / "capteurs_temperature.csv")
    pres = load_pressure(data_dir / "capteurs_pression.tsv")
    inc = load_incidents(data_dir / "releves_incidents.csv")
    dataset = build_dataset(temp, pres, inc, window_hours=settings.incident_window_hours)
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return add_temporal_features(dataset).dropna().reset_index(drop=True)


# [PÉDAGOGIE] BLOC `check_data` — garde-fou : refuser tôt un état incomplet plutôt que propager
# [PÉDAGOGIE] une erreur ambiguë.
# [PÉDAGOGIE] CONTRAT — entrées : data_dir ; preuve : le message et le code d'échec doivent
# [PÉDAGOGIE] permettre de corriger la cause.
@app.command()
def check_data(data_dir: Path | None = None) -> None:
    """Load sample sources and print a short health summary."""
    data_dir = data_dir or settings.data_dir
    dataset = _load_gold(data_dir)
    typer.echo(f"rows={len(dataset)}")
    typer.echo(f"machines={dataset['machine'].nunique()}")
    typer.echo(f"panne_rate={dataset[settings.target_col].mean():.4f}")


# [PÉDAGOGIE] BLOC `build_gold` — construction déterministe : produire la même sortie pour les
# [PÉDAGOGIE] mêmes entrées et paramètres.
# [PÉDAGOGIE] CONTRAT — entrées : data_dir, out ; preuve : vérifier forme, taille, empreinte ou
# [PÉDAGOGIE] invariants de la sortie.
@app.command()
def build_gold(data_dir: Path | None = None, out: Path | None = None) -> None:
    """Build and save the gold dataset from raw InduSense sources."""
    data_dir = data_dir or settings.data_dir
    out = out or settings.gold_dir / "gold_dataset.csv"
    dataset = _load_gold(data_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(out, index=False)
    logger.info("Gold dataset written: {} rows -> {}", len(dataset), out)


# [PÉDAGOGIE] BLOC `train` — phase d'apprentissage : relier données, paramètres et modèle
# [PÉDAGOGIE] reproductible.
# [PÉDAGOGIE] CONTRAT — entrées : data_dir, out ; preuve : conserver graine, split, métriques et
# [PÉDAGOGIE] artefact afin de pouvoir refaire l'expérience.
@app.command()
def train(data_dir: Path | None = None, out: Path | None = None) -> None:
    """Train the baseline RandomForest model on sample data."""
    data_dir = data_dir or settings.data_dir
    out = out or settings.model_dir / "rf.joblib"
    dataset = _load_gold(data_dir)
    x = select_features(dataset, settings.target_col)
    y = dataset[settings.target_col]
    model = train_model(x, y, random_state=settings.random_seed)
    save_model(model, out)

    metadata = {
        "created_at": datetime.now(UTC).isoformat(),
        "package_version": __version__,
        "random_seed": settings.random_seed,
        "target_col": settings.target_col,
        "features": list(x.columns),
        "n_train_rows": int(len(dataset)),
        "panne_rate": round(float(y.mean()), 4),
        "dataset": str(data_dir),
    }
    metadata_path = out.parent / "model_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Model trained on {} rows -> {}", len(dataset), out)
    logger.info("Metadata -> {}", metadata_path)


# [PÉDAGOGIE] BLOC `predict` — phase d'inférence ou d'évaluation : appliquer un contrat gelé à des
# [PÉDAGOGIE] observations nouvelles.
# [PÉDAGOGIE] CONTRAT — entrées : data_dir, model_path ; preuve : contrôler ordre des features,
# [PÉDAGOGIE] seuil, métriques et provenance du modèle.
@app.command()
def predict(data_dir: Path | None = None, model_path: Path | None = None) -> None:
    """Score the latest observation per machine."""
    data_dir = data_dir or settings.data_dir
    model_path = model_path or settings.model_dir / "rf.joblib"
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if not model_path.exists():
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise typer.BadParameter(f"Model not found: {model_path}. Run `indusense train` first.")

    dataset = _load_gold(data_dir).groupby("machine").tail(1)
    model = load_model(model_path)
    scores = predict_proba(model, select_features(dataset, settings.target_col))
    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for machine, score in zip(dataset["machine"], scores, strict=False):
        typer.echo(f"{machine}: P(panne)={score:.3f}")


# [PÉDAGOGIE] BLOC `main` — orchestration : rendre l'ordre, les dépendances et les points d'échec
# [PÉDAGOGIE] visibles.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : chaque étape doit annoncer
# [PÉDAGOGIE] sa preuve avant que la suivante ne commence.
def main() -> None:
    app()


# [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le cas
# [PÉDAGOGIE] vrai et le cas faux.
if __name__ == "__main__":
    main()
