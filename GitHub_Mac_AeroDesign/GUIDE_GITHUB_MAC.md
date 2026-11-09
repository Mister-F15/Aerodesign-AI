# Fabriquer AeroDesign AI pour Mac

Ce kit correspond à l'application du 9 novembre 2026 : Explorer, Optimiser,
modèle ML figé, visualisation potentielle et dernières exclusions qualifiées.
Il n'embarque ni XFOIL, ni Ansys, ni anciennes simulations, ni identifiants.

## 1. Déposer les fichiers depuis Windows

1. Décompresser `AeroDesign_AI_Kit_GitHub_Mac.zip`.
2. Ouvrir le dossier `GitHub_Mac_AeroDesign` extrait. Il contient notamment
   `.github` et `mac_build`.
3. Ouvrir https://github.com/Mister-F15/Aerodesign-AI puis l'onglet **Code**.
4. Cliquer **Add file > Upload files**.
5. Glisser le CONTENU du dossier extrait : `.github`, `mac_build`,
   `.gitignore`, `GUIDE_GITHUB_MAC.md` et `MANIFEST_SHA256.json`.
   Ne pas déposer le ZIP lui-même, ni le dossier parent entier.
6. En bas, saisir « Préparer les versions Mac », conserver le dépôt sur la
   branche par défaut (normalement `main`) et cliquer **Commit changes**.
7. Vérifier que le dépôt affiche `mac_build` et le fichier
   `.github/workflows/fabriquer-mac.yml` à partir de sa racine.

Le kit ne remplace pas le README déjà présent sur GitHub. Si le dépôt est
public, le code et le modèle déposés sont accessibles au public.

Si le navigateur ne dépose pas `.github`, déposer d'abord `mac_build` et les
autres fichiers. Puis utiliser **Add file > Create new file** ; donner
exactement le nom `.github/workflows/fabriquer-mac.yml`, copier le contenu
du fichier local homonyme, et valider sur la branche par défaut.

## 2. Lancer la fabrication

1. Cliquer **Actions** dans le dépôt. Si GitHub demande d'activer les workflows,
   accepter leur activation pour ce dépôt.
2. À gauche, sélectionner **Fabriquer les versions Mac**.
3. Cliquer **Run workflow**, choisir la branche par défaut, puis le bouton
   vert **Run workflow**.
4. Ouvrir l'exécution apparue. Deux fabrications distinctes démarrent :
   **Mac Intel** et **Mac AppleSilicon**. Patienter jusqu'à leur fin.

Le lancement est manuel : un simple dépôt de fichiers ne lance rien.
Les machines standard sont gratuites dans un dépôt public. Dans un dépôt
privé, elles utilisent le quota du compte, puis éventuellement sa facturation.
Le workflow n'utilise aucun secret, ne publie aucune release et ne demande
qu'un accès en lecture au contenu. Les fichiers téléchargeables sont gardés
14 jours : les télécharger pour les conserver.

## 3. Récupérer les applications

En bas du résumé de l'exécution, dans **Artifacts**, télécharger :

- `AeroDesign_AI_Mac_Intel` : pour les Mac Intel.
- `AeroDesign_AI_Mac_AppleSilicon` : pour les Mac à puce Apple M1/M2/M3/M4/etc.

Le téléchargement de GitHub est une archive contenant trois fichiers :
l'archive ZIP de l'application, `LIRE_SUR_MAC.txt` et `VERIFICATION.json`.
Décompresser ce premier téléchargement, puis partager ces trois fichiers
avec le testeur. Le testeur doit décompresser le ZIP de l'application sur
son Mac. Ne pas décompresser puis recompresser la `.app` sous Windows :
ses permissions et ses liens internes doivent être préservés.

## 4. Ce qui est contrôlé automatiquement

- Architecture native x86_64 (Intel) ou arm64 (Apple Silicon).
- Empreinte du modèle d'origine et versions fixes des bibliothèques.
- 27 cas ML de référence et champ potentiel.
- Trois objectifs d'optimisation et cinq propositions par objectif.
- Exclusion du cas NACA 6715 / 0° / Re=1 million, sans exclure les autres
  conditions autorisées du même profil.
- Fichiers de l'interface, service HTTP local et absence de route XFOIL.
- Contrôles de la petite fenêtre de lancement.
- Exécutable sans Python accessible dans PATH ; démarrage depuis un autre
  répertoire ; fermeture propre du serveur.
- Signature ad hoc et ouverture de la copie extraite de l'archive livrée.

Les bibliothèques sont installées sur le Mac de fabrication de GitHub,
puis intégrées dans l'application : le destinataire n'installe rien de cela.
La fabrication utilise macOS 15. Cette première édition cible macOS 15 et
ultérieur ; les autres versions restent à qualifier. Le fonctionnement sur
un Mac personnel, l'ouverture via le Finder et le rendu dans Safari restent
à essayer réellement. Le succès de la fabrication n'est pas une certification
de compatibilité universelle.

## 5. Si un contrôle échoue

Ouvrir la ligne rouge de l'exécution, puis l'étape en échec. Copier le message
et son contexte ou transmettre le lien de cette exécution. Un éventuel
fichier `Diagnostic_Mac_...` est conservé 7 jours. Ne pas partager de mot de
passe ou de jeton GitHub. Chaque architecture indépendante peut réussir
même si l'autre échoue.

L'application est signée localement par PyInstaller mais n'est pas notariée
par Apple : macOS peut bloquer son ouverture après téléchargement. Conserver
alors le message exact ; ne pas désactiver globalement les protections.
La signature de distribution et la notarisation sont une étape ultérieure.

## Documentation officielle

- [Machines GitHub Actions](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Lancement manuel](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
- [Télécharger les fichiers fabriqués](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
- [Construction avec PyInstaller](https://pyinstaller.org/en/stable/usage.html)
