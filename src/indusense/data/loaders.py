# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/data/loaders.py
# [PÉDAGOGIE] MODULE  — M23 — ingestion hétérogène, normalisation et jointure temporelle
# [PÉDAGOGIE] RÔLE    — Transformer plusieurs formats sources en un contrat tabulaire commun et
# [PÉDAGOGIE]           fabriquer la cible sans mélange de machines.
# [PÉDAGOGIE] THÉORIE — la normalisation d'identifiant rend les jointures explicites
# [PÉDAGOGIE]           • merge_asof rapproche des mesures temporelles dans une tolérance
# [PÉDAGOGIE]             contrôlée
# [PÉDAGOGIE]           • la clé machine et l'ordre chronologique empêchent une association
# [PÉDAGOGIE]             inter-équipements
# [PÉDAGOGIE] À VOIR  — Contrôler schéma, nombre de lignes perdues, ordre des dates et
# [PÉDAGOGIE]           distribution de la cible.
# [PÉDAGOGIE] PIÈGE   — Dans les fichiers SQL, ne jamais ajouter en commentaire un faux tuple
# [PÉDAGOGIE]           ressemblant aux données chargées.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

import pandas as pd
from loguru import logger

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
_DIGITS = re.compile(r"(\d+)")
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
_MACHINE_ROW = re.compile(
    r"\('([^']+)',\s*'([^']+)',\s*(\d+),\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\)"
)

# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
CRITICALITY_ORDER: dict[str, int] = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


# [PÉDAGOGIE] BLOC `normalize_machine_id` — unité de responsabilité : isoler un comportement
# [PÉDAGOGIE] nommable, testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : raw ; preuve : l'appelant doit pouvoir vérifier la sortie ou
# [PÉDAGOGIE] l'effet de bord annoncé.
def normalize_machine_id(raw: str) -> str:
    """Normalize raw machine identifiers to MACH-0N."""
    match = _DIGITS.search(str(raw))
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if not match:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise ValueError(f"machine_id sans numero : {raw!r}")
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return f"MACH-{int(match.group(1)):02d}"


# [PÉDAGOGIE] BLOC `load_temperature` — frontière d'entrée : convertir une représentation externe
# [PÉDAGOGIE] en structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : path ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def load_temperature(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["machine"] = df["machine_id"].map(normalize_machine_id)
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return df[["machine", "timestamp", "temperature"]]


# [PÉDAGOGIE] BLOC `load_pressure` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : path ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def load_pressure(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True).dt.tz_localize(None)
    df["machine"] = df["machine_id"].map(normalize_machine_id)
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return df[["machine", "timestamp", "pressure_bar"]]


# [PÉDAGOGIE] BLOC `load_incidents` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : path ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def load_incidents(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["machine"] = df["machine_id"].map(normalize_machine_id)
    df["incident_ts"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return df[["machine", "incident_ts"]]


# [PÉDAGOGIE] BLOC `load_machines` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : path ; preuve : vérifier schéma, types, ordre et erreurs
# [PÉDAGOGIE] explicites avant tout calcul aval.
def load_machines(path: Path) -> pd.DataFrame:
    text = Path(path).read_text(encoding="utf-8")
    rows = [
        {
            "machine": normalize_machine_id(match.group(1)),
            "commissioning_date": pd.to_datetime(match.group(2)),
            "max_daily_capacity": int(match.group(3)),
            "model": match.group(4),
            "production_line": match.group(5),
            "location": match.group(6),
            "criticality": match.group(7),
        }
        for match in _MACHINE_ROW.finditer(text)
    ]
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if not rows:
        # [PÉDAGOGIE] FAIL FAST — refuser ici empêche un état invalide de contaminer les étapes
        # [PÉDAGOGIE] suivantes.
        raise ValueError(f"Aucune machine trouvee dans {path}")
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return pd.DataFrame(rows)


# [PÉDAGOGIE] BLOC `build_dataset` — construction déterministe : produire la même sortie pour les
# [PÉDAGOGIE] mêmes entrées et paramètres.
# [PÉDAGOGIE] CONTRAT — entrées : temp, pres, inc, window_hours, tolerance_minutes ; preuve :
# [PÉDAGOGIE] vérifier forme, taille, empreinte ou invariants de la sortie.
def build_dataset(
    temp: pd.DataFrame,
    pres: pd.DataFrame,
    inc: pd.DataFrame,
    window_hours: int = 24,
    tolerance_minutes: int = 90,
) -> pd.DataFrame:
    """Join sensors and derive binary target `panne`.

    The `by="machine"` parameter is critical: without it, one machine can inherit
    the pressure value of another machine.
    """
    temp = temp.sort_values("timestamp")
    pres = pres.sort_values("timestamp")
    sensors = pd.merge_asof(
        temp,
        pres,
        on="timestamp",
        by="machine",
        direction="nearest",
        # `datetime.timedelta` de la bibliotheque standard, PAS pd.Timedelta :
        # avec numpy >= 2.5, `pd.Timedelta(minutes=n)` comme `pd.Timedelta("90min")`
        # passent par un timedelta64 d'unite « generic », deprecie et bientot
        # erreur. La stdlib n'emprunte jamais ce chemin, et pandas l'accepte
        # partout ou il attend un Timedelta.
        tolerance=timedelta(minutes=tolerance_minutes),
    )
    before = len(sensors)
    sensors = sensors.dropna(subset=["pressure_bar"])
    dropped = before - len(sensors)
    # [PÉDAGOGIE] DÉCISION — cette condition matérialise une règle testable ; lire séparément le
    # [PÉDAGOGIE] cas vrai et le cas faux.
    if dropped:
        logger.info(
            "merge_asof: {} rows without pressure under +/-{} min dropped ({:.2%})",
            dropped,
            tolerance_minutes,
            dropped / before,
        )

    sensors = sensors.sort_values(["machine", "timestamp"]).reset_index(drop=True)
    sensors["panne"] = 0
    # Meme raison que ci-dessus : stdlib, pas pd.Timedelta.
    window = timedelta(hours=window_hours)
    # [PÉDAGOGIE] ITÉRATION — appliquer la même règle à chaque élément permet de raisonner sur un
    # [PÉDAGOGIE] invariant stable.
    for row in inc.itertuples():
        mask = (
            (sensors["machine"] == row.machine)
            & (sensors["timestamp"] >= row.incident_ts - window)
            & (sensors["timestamp"] <= row.incident_ts)
        )
        sensors.loc[mask, "panne"] = 1
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return sensors


# [PÉDAGOGIE] BLOC `add_machine_criticality` — unité de responsabilité : isoler un comportement
# [PÉDAGOGIE] nommable, testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : df, machines ; preuve : l'appelant doit pouvoir vérifier la
# [PÉDAGOGIE] sortie ou l'effet de bord annoncé.
def add_machine_criticality(df: pd.DataFrame, machines: pd.DataFrame) -> pd.DataFrame:
    """Add static criticality for monitoring or segmentation, not baseline training."""
    levels = df["machine"].map(machines.set_index("machine")["criticality"].map(CRITICALITY_ORDER))
    out = df.copy()
    out["criticality_level"] = levels.fillna(CRITICALITY_ORDER["MEDIUM"]).astype("int64")
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return out
