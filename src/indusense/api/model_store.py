# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/api/model_store.py
# [PÉDAGOGIE] MODULE  — M25 — contrat d'API, validation et preuve de readiness
# [PÉDAGOGIE] RÔLE    — Exposer le modèle derrière un contrat HTTP explicite, testable et
# [PÉDAGOGIE]           observable.
# [PÉDAGOGIE] THÉORIE — Pydantic valide la forme et les invariants avant l'appel au modèle
# [PÉDAGOGIE]           • liveness et readiness répondent à deux questions opérationnelles
# [PÉDAGOGIE]             différentes
# [PÉDAGOGIE]           • l'injection de dépendances permet d'isoler le chargement du modèle dans
# [PÉDAGOGIE]             les tests
# [PÉDAGOGIE] À VOIR  — Swagger/TestClient doivent rendre visibles les entrées, sorties et codes
# [PÉDAGOGIE]           2xx/4xx/5xx attendus.
# [PÉDAGOGIE] PIÈGE   — Une réponse 200 ne suffit pas si le schéma, la version du modèle ou la
# [PÉDAGOGIE]           normalisation sont faux.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
#  src/indusense/api/model_store.py  —  STOCKAGE du modèle de ML en mémoire
# -----------------------------------------------------------------------------
#  Place dans le projet : Sprint 3, module API (n°25).
#
#  RÔLE DU FICHIER
#  Charger le modèle de Machine Learning UNE SEULE FOIS (au démarrage de l'API)
#  et le garder en mémoire pour que chaque prédiction soit RAPIDE.
#
#  POURQUOI « UNE SEULE FOIS » ?
#  Lire un modèle entraîné depuis le disque (le fichier `rf.joblib`) est une
#  opération LENTE (plusieurs dizaines de Mo à désérialiser). Si on le rechargeait
#  à chaque requête /predict, l'API serait inutilisable. On le charge donc au
#  démarrage, on le range dans une variable globale, et toutes les requêtes
#  réutilisent ce même objet déjà prêt. C'est un patron classique en MLOps :
#  séparer le COÛT du chargement (payé une fois) du COÛT de l'inférence.
#
#  NOTION DE « BUNDLE »
#  Un modèle seul ne suffit pas pour décider : il faut aussi savoir sa VERSION,
#  le SEUIL de décision à appliquer, et le nom de la colonne CIBLE. On regroupe
#  donc tout cela dans un petit objet appelé « bundle » (= paquet). Ainsi, une
#  prédiction dispose en un seul endroit de tout ce dont elle a besoin.
#
#  INJECTION DE DÉPENDANCES
#  La fonction `get_model_bundle()` est faite pour être branchée dans FastAPI
#  via `Depends(get_model_bundle)` (voir main.py). FastAPI l'appellera tout seul
#  et « injectera » le résultat dans les routes qui en ont besoin. Ce mécanisme
#  (« injection de dépendances ») évite que chaque route aille chercher le modèle
#  elle-même : elle le reçoit en argument, proprement.
# =============================================================================

# Annotations de type modernes (voir explication dans les autres fichiers).
# [PÉDAGOGIE] DÉPENDANCE — __future__ : apporte une dépendance explicitement visible au lecteur.
from __future__ import annotations

# On importe la fonction `load_model` du module « tabular » du projet. C'est elle
# qui sait désérialiser le fichier `rf.joblib` (via joblib) et reconstruire
# l'objet modèle utilisable. On réutilise cette fonction plutôt que de recoder
# la lecture ici : chaque responsabilité reste à sa place.
import hashlib

# `json` : module standard pour lire/écrire du JSON. Ici on l'utilise pour lire
# le fichier de métadonnées du modèle (`model_metadata.json`).
import json

# `dataclass` : un décorateur qui transforme une classe en simple « structure de
# données ». Il génère automatiquement le constructeur `__init__`, l'affichage,
# l'égalité, etc. Idéal pour regrouper quelques champs sans écrire de code répétitif.
from dataclasses import dataclass

# `Path` : représentation portable d'un chemin de fichier (Windows/macOS/Linux).
# Permet d'écrire `model_dir / "rf.joblib"` au lieu de bricoler des chaînes.
from pathlib import Path

# `Any` : type « n'importe quoi ». On l'emploie pour le modèle car son type exact
# (un RandomForest scikit-learn) n'a pas besoin d'être connu/contraint ici ; ce
# qui compte, c'est qu'il sache faire `.predict_proba(...)`.
from typing import Any

from loguru import logger

from indusense.config import settings
from indusense.models.tabular import load_model


# CONTROLE 2 (STRIDE: Tampering) — joblib.load deserialise du pickle : lire un
# fichier revient a EXECUTER du code. On verifie donc l'empreinte AVANT de lire.
class ModelIntegrityError(RuntimeError):
    """Le fichier modele ne correspond pas a l'empreinte declaree."""


def sha256_of(path: Path) -> str:
    """Empreinte SHA-256 d'un fichier, lue par blocs (le modele peut etre gros)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for bloc in iter(lambda: handle.read(65536), b""):
            digest.update(bloc)
    return digest.hexdigest()


# OLD CODE def verify_artifact(path: Path, expected_sha256: str | None) -> None:
def verify_artifact(path: Path, expected_sha256: str | None, require: bool = True) -> None:
    """Refuse tout artefact sans empreinte declaree ou dont l'empreinte differe."""
    if not expected_sha256:
        if not require:
            logger.warning("Aucune empreinte pour {} : verification desactivee", path.name)
            return
        raise ModelIntegrityError(
            f"Aucune empreinte declaree pour {path.name} : chargement refuse. "
            "Ajouter 'rf_sha256' dans model_metadata.json."
        )
    obtenu = sha256_of(path)
    if obtenu != expected_sha256:
        raise ModelIntegrityError(
            f"Empreinte invalide pour {path.name} : "
            f"attendu {expected_sha256[:12]}..., obtenu {obtenu[:12]}..."
        )


# -----------------------------------------------------------------------------
#  La structure « ModelBundle » : le modèle + ses informations indispensables.
# -----------------------------------------------------------------------------
# [PÉDAGOGIE] TYPE `ModelBundle` — regroupe un état cohérent et le contrat des opérations
# [PÉDAGOGIE] associées.
# [PÉDAGOGIE] THÉORIE — nommer ce type rend les invariants visibles et facilite les tests à la
# [PÉDAGOGIE] frontière.
@dataclass
class ModelBundle:
    # `@dataclass` ci-dessus génère automatiquement le constructeur. On déclare
    # juste les CHAMPS (nom + type) ; on pourra ensuite créer un bundle avec
    # ModelBundle(model=..., version=..., threshold=..., target_col=...).

    # `model` : l'objet modèle entraîné lui-même (le RandomForest). Type `Any`
    # car on ne veut pas se contraindre ici (cf. explication de l'import `Any`).
    model: Any

    # `version` : la version du modèle (texte), tirée des métadonnées. Sert à la
    # TRAÇABILITÉ : on saura toujours quel modèle a produit telle prédiction.
    version: str

    # `threshold` : le SEUIL de décision (nombre entre 0 et 1). Si la probabilité
    # de panne dépasse ce seuil -> décision "alerte", sinon "ok". On le stocke
    # avec le modèle pour que la règle de décision soit cohérente et centralisée.
    threshold: float

    # `target_col` : le nom de la colonne CIBLE (ce que le modèle prédit, ex.
    # "panne"). Utile au moment de préparer les features : on doit retirer cette
    # colonne des entrées du modèle (on ne donne pas la réponse en question !).
    target_col: str


# -----------------------------------------------------------------------------
#  L'état global : LE bundle chargé, partagé par toute l'application.
# -----------------------------------------------------------------------------
# `_BUNDLE` contiendra le modèle une fois chargé. Au démarrage du module, il vaut
# `None` (« rien pour l'instant ») : le modèle n'est pas encore chargé. C'est le
# fichier main.py qui, au démarrage de l'API (via `lifespan`), appellera
# `load_bundle(...)` et rangera le résultat dans `store._BUNDLE`.
#   - Type `ModelBundle | None` : soit un bundle, soit rien.
#   - Le préfixe « _ » indique un détail interne au module.
#   - Tant que `_BUNDLE` vaut None, la route /ready renverra 503 (pas prêt) : on
#     refuse de prédire tant que le modèle n'est pas réellement disponible.
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
_BUNDLE: ModelBundle | None = None


# -----------------------------------------------------------------------------
#  Fonction de CHARGEMENT : lit le modèle + ses métadonnées depuis le disque.
# -----------------------------------------------------------------------------
# [PÉDAGOGIE] BLOC `load_bundle` — frontière d'entrée : convertir une représentation externe en
# [PÉDAGOGIE] structure interne validée.
# [PÉDAGOGIE] CONTRAT — entrées : model_dir, threshold ; preuve : vérifier schéma, types, ordre et
# [PÉDAGOGIE] erreurs explicites avant tout calcul aval.
def load_bundle(model_dir: Path, threshold: float) -> ModelBundle:
    # Paramètres :
    #   - `model_dir` : le DOSSIER qui contient les fichiers du modèle.
    #   - `threshold` : le seuil de décision à mémoriser dans le bundle (il vient
    #     de la configuration du projet, pas du fichier modèle).
    # Renvoie : un `ModelBundle` tout prêt à l'emploi.

    # On lit le fichier de MÉTADONNÉES JSON situé dans le dossier du modèle.
    #   - `model_dir / "model_metadata.json"` construit le chemin complet.
    #   - `.read_text()` lit tout le fichier sous forme de texte.
    #   - `json.loads(...)` transforme ce texte JSON en dictionnaire Python.
    # Ce fichier contient des infos écrites au moment de l'entraînement
    # (version du package, nom de la colonne cible, etc.).
    meta = json.loads((model_dir / "model_metadata.json").read_text())

    # CONTROLE 2 — verification AVANT toute deserialisation. L'ordre est le
    # controle : verifier apres load_model ne servirait a rien, le code
    # malveillant se serait deja execute.
    # OLD CODE verify_artifact(model_dir / "rf.joblib", meta.get("rf_sha256"))
    verify_artifact(model_dir / "rf.joblib", meta.get("rf_sha256"), settings.require_model_hash)

    # On construit et on RENVOIE le bundle, en remplissant ses quatre champs :
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return ModelBundle(
        # On charge le modèle entraîné depuis `rf.joblib` (rf = random forest).
        # `load_model` gère la désérialisation ; on lui passe le chemin du fichier.
        model=load_model(model_dir / "rf.joblib"),
        # Version du modèle, lue dans les métadonnées. `meta.get("clé", défaut)`
        # renvoie la valeur si la clé existe, sinon la valeur par défaut ("0").
        # On entoure de `str(...)` pour être SÛR d'avoir bien du texte.
        version=str(meta.get("package_version", "0")),
        # Seuil de décision : on prend simplement celui reçu en paramètre.
        threshold=threshold,
        # Nom de la colonne cible : lu dans les métadonnées, défaut "panne".
        target_col=str(meta.get("target_col", "panne")),
    )


# -----------------------------------------------------------------------------
#  Accès au bundle : la fonction « injectée » dans les routes via Depends.
# -----------------------------------------------------------------------------
# [PÉDAGOGIE] BLOC `get_model_bundle` — unité de responsabilité : isoler un comportement nommable,
# [PÉDAGOGIE] testable et réutilisable.
# [PÉDAGOGIE] CONTRAT — entrées : aucun argument explicite ; preuve : l'appelant doit pouvoir
# [PÉDAGOGIE] vérifier la sortie ou l'effet de bord annoncé.
def get_model_bundle() -> ModelBundle | None:
    # Cette fonction se contente de RENVOYER l'état global `_BUNDLE`.
    #   - Si le modèle est chargé -> elle renvoie le bundle.
    #   - Sinon -> elle renvoie None, et les routes sauront répondre « pas prêt »
    #     (code 503) plutôt que de planter.
    # C'est volontairement une fonction (et non un simple accès à la variable) :
    # cela permet à FastAPI de l'appeler via `Depends(get_model_bundle)` et
    # d'« injecter » proprement le bundle dans chaque route qui le demande.
    # Astuce : on relit `_BUNDLE` à chaque appel (et non une copie capturée),
    # donc dès que main.py l'a rempli au démarrage, toutes les routes le voient.
    # [PÉDAGOGIE] SORTIE — cette valeur constitue le contrat remis à l'appelant ; son type et son
    # [PÉDAGOGIE] sens doivent rester stables.
    return _BUNDLE
