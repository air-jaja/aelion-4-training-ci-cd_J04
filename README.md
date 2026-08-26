# InduSense — parcours progressif Sprint 3 CISIA

Ce depot part d'une **reconstruction operationnelle de la frontiere Sprint 2**.
Le checkout stagiaire exact de fin M22 n'ayant pas ete retrouve localement, ce
socle ne doit pas etre presente comme sa copie exacte. Il ne contient pas
d'avance les solutions du Sprint 3 : le formateur revele un jalon cumulatif au
debut de chaque demi-journee.

Pour demarrer et se mettre a niveau sans perdre son travail, lire
[`FORMATION/README.md`](FORMATION/README.md). Le calendrier des douze jalons est
dans [`FORMATION/PLAN_JALONS.md`](FORMATION/PLAN_JALONS.md).

Les apprenants Windows, macOS et Linux utilisent les memes jalons et les memes
preuves. Les commandes propres a chaque systeme sont regroupees dans
[`FORMATION/GUIDE_MULTIPLATEFORME_APPRENANT.md`](FORMATION/GUIDE_MULTIPLATEFORME_APPRENANT.md).

> Regle de securite : travailler sur une branche personnelle, commiter avant
> chaque mise a niveau et ne jamais recopier de cle, jeton ou mot de passe dans
> le depot.

## Socle technique fourni

Point de depart propre pour demarrer le Sprint 3 CISIA.

Objectif : repartir tous du meme etat, meme si les sprints precedents ont ete
heterogenes. Ce package fournit :

- un vrai package Python en layout `src/` ;
- des donnees brutes InduSense dans `data/raw/` ;
- un dataset gold dans `data/gold/gold_dataset.csv` ;
- des fonctions de chargement et de normalisation ;
- des features temporelles sans fuite de donnees ;
- une CLI `indusense` ;
- des tests `pytest` ;
- une configuration `ruff`, `black`, `pre-commit`.

## Verification rapide

### Windows PowerShell

```powershell
cd "C:\chemin\vers\indusense-sprint3-starter"
uv venv --python 3.13
uv sync --frozen --extra dev
uv run python --version
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run indusense --help
```

### macOS / Linux

```bash
cd /chemin/vers/indusense-sprint3-starter
uv venv --python 3.13
uv sync --frozen --extra dev
uv run python --version
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run indusense --help
```

La commande `uv run python --version` doit afficher Python 3.13.x. C'est cette
version qui fait foi, pas le `python --version` global de la machine.

## Commandes utiles

```bash
uv run indusense check-data
uv run indusense build-gold
uv run indusense train
uv run indusense predict
```

## Structure

```text
src/indusense/
  config.py
  cli.py
  data/loaders.py
  features/temporal.py
  models/tabular.py
tests/
data/sample/
data/raw/
data/gold/
artifacts/models/
```

## Ce que les apprenants doivent retenir

Le notebook sert a explorer. Le package sert a industrialiser.

Le Sprint 3 commence quand le code est :

- importable ;
- testable ;
- reproductible ;
- lanceable par une CLI ;
- protege contre les fuites de donnees temporelles.
