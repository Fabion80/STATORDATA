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
5. publie ou actualise une Release GitHub ;
6. vérifie que l'URL publique `releases/latest/download` fonctionne.

Une exécution automatique est programmée le **1er de chaque mois**. Le workflow peut également être lancé manuellement depuis l'onglet **Actions**.

## Important

STATORDATA est un dépôt technique du projet STATOR49. Il n'est pas un dépôt officiel FDJ et n'implique aucune affiliation avec FDJ.
