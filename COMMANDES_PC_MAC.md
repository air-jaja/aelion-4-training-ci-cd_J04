# Commandes de deploiement et de test environnement

Ce fichier sert de check-list formateur et apprenant.

## 1. Preflight Windows PowerShell

```powershell
python --version
py -0p
uv --version
git --version
wsl -l -v
docker --version
```

Notes :

- si `python --version` affiche 3.14, ce n'est pas bloquant ;
- ce qui compte est `uv run python --version` dans le projet ;
- Docker peut etre absent le J1, mais il doit etre pret avant le J3.

Installation minimale si besoin :

```powershell
winget install --id Astral.Uv -e
winget install --id Git.Git -e
winget install --id Microsoft.VisualStudioCode -e
uv python install 3.13
```

Verifier Python 3.13 :

```powershell
uv python list
uv venv --python 3.13
uv run python --version
```

## 2. Preflight macOS Terminal

```bash
python3 --version
uv --version
git --version
docker --version
```

Installation minimale si besoin :

```bash
brew install uv git
uv python install 3.13
```

Si Homebrew n'est pas installe :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. Preflight Linux Terminal

```bash
python3 --version
uv --version
git --version
docker --version
docker compose version
```

Installation minimale de `uv` sans modifier Python systeme :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13
```

Pour Git, Docker Engine et le plugin Compose, utiliser le gestionnaire de
paquets de la distribution avec l'accord du formateur. Ne pas improviser une
commande `sudo` pendant une sequence de cours.

## 4. Installation du package apprenant

### Windows

```powershell
cd "C:\chemin\vers\indusense-sprint3-starter"
uv venv --python 3.13
uv sync --frozen --extra dev
uv run python --version
```

### macOS ou Linux

```bash
cd /chemin/vers/indusense-sprint3-starter
uv venv --python 3.13
uv sync --frozen --extra dev
uv run python --version
```

Attendu : Python 3.13.x.

## 5. Tests de validation du poste

```bash
uv run python -c "import indusense; print(indusense.__file__)"
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run indusense --help
uv run indusense check-data
uv run indusense build-gold
```

Attendu :

- import du package OK ;
- tests verts ;
- ruff propre ;
- black propre ;
- CLI repond ;
- donnees sample chargees.
- dataset gold regenerable.

## 6. Commandes Sprint 3 J1

Matin module 23 :

```text
uv sync --frozen --extra dev
uv run pytest tests/test_temporal.py -q
uv run pytest tests/test_loaders.py -q
uv run ruff check .
uv run indusense --help
```

Apres-midi module 24 :

```text
uv run pre-commit install
uv run pre-commit run --all-files
uv sync --frozen --extra dev --extra mlops
git diff --exit-code -- uv.lock
```

Ne pas lancer `uv add` ni `uv lock` : le verrou fourni est commun aux trois
systemes et doit rester identique.

## 7. Si uv n'est pas trouve

Windows :

```powershell
winget install --id Astral.Uv -e
```

macOS :

```bash
brew install uv
```

Linux, ou macOS sans Homebrew :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Fermer et rouvrir le terminal apres installation.
