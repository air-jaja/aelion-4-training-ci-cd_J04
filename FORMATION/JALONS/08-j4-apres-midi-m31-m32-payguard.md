# 08 — J4 apres-midi — M31–M32 PayGuard

> Windows, macOS ou Linux : suivre la section PayGuard du
> [guide multiplateforme](../GUIDE_MULTIPLATEFORME_APPRENANT.md) pour verifier et
> extraire l'archive avec l'outil natif du poste.

Objectif : observer un drift adversarial sur la fraude bancaire sans melanger le
jeu de donnees PayGuard et le fil rouge InduSense.

Depot de travail separe :
`https://github.com/thomasfesq/CISIA_24082026_PayGuard`.

Recu par le jalon : pipeline InduSense stabilise et fiche de bascule PayGuard.
Le present depot ne contient aucun corrige de fraude bancaire.

A faire : reference vs courant, PSI/KS, performance avec labels retardes,
attaque de seuil, alerte et decision humaine.

Preuve : conserver rapport de drift, metriques avant/apres et decision motivee
dans le depot PayGuard, pas dans InduSense.

Rattrapage : calcul sur une feature + decision documentee ; extension
multivariee en reserve.
