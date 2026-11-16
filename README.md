# STATORDATA

Collecte centralisée des résultats officiels Loto et Super Loto pour Stator49.

- Archives FDJ, catalogue des tirages publiés, pages datées des résultats récents et calendrier collectés ici.
- Contrôle des identités, dates, cinq numéros, Chance, doublons, empreintes et absence de régression avant publication.
- Nouvelle archive immuable uniquement lorsque les tirages changent. Les anciennes applications gardent leurs fichiers de Release.
- `feed/manifest.json` contient la date de vérification, le dernier tirage, la couverture contrôlée, le prochain tirage et l’URL immuable de l’archive. Publication après contrôle des fichiers accessibles.
- L’application lit le petit manifeste une fois par ouverture et télécharge l’archive uniquement si sa version a changé. Aucune donnée personnelle n’est envoyée ici.

Exécutions quotidiennes : 07:17, 18:17, 20:17, 21:17, 22:17 et 23:17 Europe/Paris ; lancement manuel possible. Ces tentatives couvrent aussi les Super Loto exceptionnels. GitHub peut retarder une exécution. Un échec laisse le dernier flux valide intact, avec sa date de vérification.

Tests : `python3 -m unittest -v`. Une pull request vérifie aussi les sources actuelles et la non-régression sans publier. Publication réservée à main.

Dépôt indépendant de FDJ, contenant uniquement des données publiques et le code de collecte.
