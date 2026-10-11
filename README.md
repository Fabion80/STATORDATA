# STATORDATA

Dépôt public de distribution des données utilisées par **STATOR49**.

Ce dépôt ne contient **aucune donnée personnelle** et aucun code privé de l'application. Il sert uniquement à publier une archive normalisée des tirages **Loto** et **Super Loto** modernes à partir des historiques mis à disposition par FDJ.

## Fichiers distribués

La dernière Release expose deux fichiers stables :

- `manifest.json` : version, dernier tirage, nombre de tirages et empreinte SHA-256 ;
- `loto_draws.json` : archive complète normalisée consommée par STATOR49.

URL de distribution utilisée par l'application :

`https://github.com/Fabion80/STATORDATA/releases/latest/download/`

## Mise à jour

La GitHub Action `Publish STATOR49 data` :

1. télécharge les archives FDJ Loto et Super Loto ;
2. vérifie les dates, identités, 5 numéros et numéro Chance ;
3. reconstruit l'archive complète ;
4. calcule le SHA-256 ;
5. compare avec la version publiée et refuse toute disparition ou modification d'un résultat connu ;
6. publie une nouvelle Release complète uniquement si les tirages ont changé ;
7. vérifie que l'URL publique `releases/latest/download` fonctionne et distribue les fichiers attendus.

Une exécution automatique est programmée **chaque jour à 18 h, heure de Paris**, avec une seconde tentative à **20 h**. Le fuseau `Europe/Paris` suit le passage à l'heure d'été et d'hiver. Le déclenchement peut être retardé par la file d'attente GitHub Actions.

L'archive contient les tirages datés au plus tard de la veille : mise à jour à **J+1**, dès que FDJ a alimenté ses ZIP. Les tirages plus récents encore absents de l'archive sont récupérés directement sur les pages officielles par l'application. Le workflow peut également être lancé manuellement depuis l'onglet **Actions**.

Une archive inchangée garde sa version et son empreinte : les téléphones ne retéléchargent pas toute la base à chaque ouverture. En cas d'échec ou d'archive incomplète, la dernière Release valide reste disponible. Les nouvelles Releases sont préparées en brouillon avec leurs deux fichiers avant de devenir publiques.

## Important

STATORDATA est un dépôt technique du projet STATOR49. Il n'est pas un dépôt officiel FDJ et n'implique aucune affiliation avec FDJ.

