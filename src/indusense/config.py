# [PÉDAGOGIE] ============================================================================
# [PÉDAGOGIE] FICHIER — src/indusense/config.py
# [PÉDAGOGIE] MODULE  — M23–M26 — configuration typée et séparation code/environnement
# [PÉDAGOGIE] RÔLE    — Rassembler les paramètres variables, leurs valeurs par défaut et leur
# [PÉDAGOGIE]           validation.
# [PÉDAGOGIE] THÉORIE — une configuration typée échoue tôt plutôt que loin de la cause
# [PÉDAGOGIE]           • les chemins sont résolus depuis une racine stable
# [PÉDAGOGIE]           • secrets et réglages d'environnement ne doivent pas être codés en dur
# [PÉDAGOGIE] À VOIR  — Afficher les valeurs non sensibles effectivement chargées et tester les
# [PÉDAGOGIE]           valeurs invalides.
# [PÉDAGOGIE] PIÈGE   — Ne jamais journaliser une clé API, un mot de passe ou un jeton complet.
# [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
# [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
# [PÉDAGOGIE] ============================================================================

# =============================================================================
#  src/indusense/config.py  —  CONFIGURATION CENTRALE du projet
# -----------------------------------------------------------------------------
#  But : rassembler au même endroit tous les RÉGLAGES (chemins de données,
#  graine aléatoire, nom de la cible…) au lieu de les écrire « en dur » un peu
#  partout dans le code.
#
#  Astuce clé : on utilise `pydantic-settings`. Chaque réglage peut être
#  SURCHARGÉ sans toucher au code, via une variable d'environnement ou un
#  fichier `.env`. Exemple : poser `INDUSENSE_RANDOM_SEED=7` change la graine.
#  C'est la bonne pratique « 12-factor app » : la config vit hors du code.
# =============================================================================
# [PÉDAGOGIE] DÉPENDANCE — pathlib : manipule les chemins sans dépendre du séparateur
# [PÉDAGOGIE] Windows/Linux/macOS.
from pathlib import Path  # objet « chemin de fichier » portable Windows/macOS/Linux

# BaseSettings : une classe spéciale qui lit automatiquement les variables
# d'environnement ; SettingsConfigDict : pour configurer son comportement.
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valeur de developpement, publique par construction : jamais acceptable en production.
DEFAULT_API_KEY = "dev-key"


# [PÉDAGOGIE] TYPE `Settings` — regroupe un état cohérent et le contrat des opérations associées.
# [PÉDAGOGIE] THÉORIE — nommer ce type rend les invariants visibles et facilite les tests à la
# [PÉDAGOGIE] frontière.
class Settings(BaseSettings):
    """Tous les réglages du projet, typés et surchargeables par l'environnement."""

    # --- Comportement de lecture de la configuration -------------------------
    model_config = SettingsConfigDict(
        env_prefix="INDUSENSE_",  # ne lit que les variables qui commencent par INDUSENSE_
        env_file=".env",  # lit aussi un fichier `.env` à la racine s'il existe
        extra="ignore",  # ignore les variables inconnues au lieu de planter
    )

    # --- Les réglages eux-mêmes (avec leur valeur par défaut) ----------------
    # Type annoté = garde-fou : si on passe "abc" à random_seed, pydantic refuse.
    data_dir: Path = Path("data/raw")  # dossier des données BRUTES (capteurs, incidents)
    gold_dir: Path = Path("data/gold")  # dossier du dataset « gold » (prêt à entraîner)
    model_dir: Path = Path("artifacts/models")  # dossier où l'on sauvegarde le modèle entraîné
    random_seed: int = 42  # graine aléatoire = résultats REPRODUCTIBLES
    target_col: str = "panne"  # nom de la colonne à prédire (0 = OK, 1 = panne)
    incident_window_hours: int = 24  # fenêtre : on étiquette « panne » les 24 h AVANT un incident
    # --- Réglages de l'API (modules 25-26) ---
    # Clé attendue dans X-API-Key ; surcharger en prod via INDUSENSE_API_KEY.
    # CONTROLE 1 (STRIDE: Spoofing) — la cle par defaut est ecrite dans le depot,
    # donc connue de tous. On refuse le demarrage si elle survit en production.
    environment: str = "dev"
    api_key: str = "dev-key"
    # Permet de desactiver la verification d'empreinte pour les premiers
    # jalons, ou l'artefact n'a pas encore de metadonnees completes.
    require_model_hash: bool = True

    @model_validator(mode="after")
    def _refuser_cle_par_defaut_en_production(self) -> "Settings":
        if self.environment == "production" and self.api_key == DEFAULT_API_KEY:
            raise ValueError(
                "INDUSENSE_API_KEY vaut encore la valeur par defaut alors que "
                "INDUSENSE_ENVIRONMENT=production. Definir une vraie cle."
            )
        return self

    decision_threshold: float = (
        0.5  # seuil proba → décision « alerte »/« ok » (INDUSENSE_DECISION_THRESHOLD)
    )


# On crée UNE instance partagée, importable partout via `from indusense.config import settings`.
# (Au moment de cette ligne, pydantic lit l'environnement / le .env et remplit les valeurs.)
# [PÉDAGOGIE] CONSTANTE / CONTRAT — cette valeur nommée centralise un choix partagé au lieu de le
# [PÉDAGOGIE] disperser.
settings = Settings()
