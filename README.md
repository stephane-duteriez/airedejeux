# aire-de-jeux
Bibliothèque d'aire de jeux public en France
Hébergé sur Google-app-engine développé en Python, j'ulise la base de données nosql de Google.

## Améliorations envisagées:
Lors de la création du projet, j'avais imaginé que le recherche se ferait par ville. 
Les places de jeux sont donc regroupé par ville, après avoir étudié les API google-map, il me semble qu'une recherche par adresse,
et troveur les places de jeux à proximitées serait plus pratiques.
Début 2016, Google application engine ne proposé pas une API en python pour faire des recherches sur des coordonnées dans le datastore 
(mais elle existe en Java).
