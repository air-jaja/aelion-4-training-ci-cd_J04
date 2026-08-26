# Mode d'emploi du parcours progressif

Avant toute commande, choisissez votre environnement dans
[`GUIDE_MULTIPLATEFORME_APPRENANT.md`](GUIDE_MULTIPLATEFORME_APPRENANT.md) :
Windows PowerShell, macOS zsh ou Linux bash. Les jalons, tests et preuves restent
identiques ; seules certaines commandes de shell et certains chemins changent.

## Une seule fois, au debut du Sprint 3

Dans VS Code, ouvrir **Terminal > Nouveau terminal**, puis saisir dans le
terminal de votre systeme :

```text
git clone https://github.com/thomasfesq/CISIA_24082026_Parcours.git
cd CISIA_24082026_Parcours
git switch -c prenom-nom
uv sync --frozen --extra dev
uv run pytest -q
```

Remplacer `prenom-nom` par un nom de branche personnel, sans espace ni accent.
Ne pas travailler directement sur `main` ou sur une branche `jalon/...`.

## Au debut de chaque demi-journee

1. Enregistrer son travail actuel :

```text
git status
git add -A
git commit -m "travail avant nouveau jalon"
```

2. Lancer le jalon annonce par le formateur, par exemple :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\formation\mettre_a_niveau.ps1 -Jalon 03
```

Le numero correspond exactement a la branche publique `jalon/03`. Le script
effectue un `git pull` de ce jalon officiel. Avant cela, il cree une
branche locale `sauvegarde/...` pointant sur l'etat courant. Il ne supprime ni ne
reecrit aucun commit.

3. Verifier l'etat recu :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\formation\verifier_jalon.ps1 -Jalon 03
```

## Si une fusion entre en conflit

Le script annule la fusion et conserve le travail dans la branche d'origine et
dans la branche `sauvegarde/...`. Pour repartir immediatement du jalon officiel
sans perdre cette copie :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\formation\mettre_a_niveau.ps1 -Jalon 03 -Rattrapage
```

Le mode rattrapage cree une nouvelle branche `rattrapage/...`. Il ne fait aucun
`reset --hard` et ne supprime rien. Le formateur pourra ensuite recuperer un
fichier precis depuis la branche de sauvegarde.

## Sur macOS ou Linux

```bash
bash scripts/formation/mettre_a_niveau.sh 03
bash scripts/formation/verifier_jalon.sh 03
```

En cas de conflit :

```bash
bash scripts/formation/mettre_a_niveau.sh 03 --rattrapage
```

Les anciens slugs complets, par exemple `03-j2-matin-m25`, restent acceptes par
compatibilite. Le format a enseigner et a afficher est toutefois le numero court.

## Regles communes

- Les jalons sont cumulatifs et deja publics ; ne chargez que le numero annonce
  par le formateur, sans explorer ni fusionner un jalon futur.
- Une branche `jalon/...` est une reference en lecture seule ; on travaille sur
  sa branche personnelle.
- Aucun secret ne doit entrer dans Git. Utiliser `.env`, jamais `.env.example`,
  pour une vraie valeur locale.
- En cas de retard important, privilegier le mode rattrapage au bricolage d'un
  historique : le travail precedent reste consultable et recuperable.
