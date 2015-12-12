# -*- coding: utf-8 -*-
import webapp2
import json
import time

from dbClass import *


class ListeVilleHandler(webapp2.RequestHandler):
    def get(self):
        q = (self.request.GET['q']).lower()
        villes = Commune.query(ndb.AND(Commune.nom_lower >= q, Commune.nom_lower <= q + "z"))
        self.response.headers['Content-Type'] = 'text/json'
        results = villes.fetch(20)
        data = {}
        for ville in results:
            data[ville.nom + ", " + ville.departement] = {
                                "key": ville.key.urlsafe(),
                                "lat": ville.coordonnees.lat,
                                "lon": ville.coordonnees.lon}
        self.response.write(json.dumps(data))


class ListeImageHandler(webapp2.RequestHandler):
    def get(self):
        indice = self.request.GET['q']
        query_photos = Photo.query(Photo.indice_aireDeJeux == indice)
        liste_images = query_photos.fetch(10)
        data = []
        for image in liste_images:
            data.append(image.photo_url)
        self.response.write(json.dumps(data))


class ListeAireDeJeuxHandler(webapp2.RequestHandler):
    def get(self):
        def byName(aire_de_jeux):
            test = "éèçàûüÛÜîëêËÊÎôÔ"
            reference = [(u"é", u"e"), (u"è", u"e"), (u"ê", u"e")]
            resultat = aire_de_jeux["nom"].lower()
            for item1, item2 in reference:
                resultat = resultat.replace(item1, item2)
            return resultat

        urlsafe_key_ville = self.request.get("keyVille")
        key_ville = ndb.Key(urlsafe=urlsafe_key_ville)
        query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville == key_ville)
        liste_aire_de_jeux = query_aire_de_jeux.fetch(100)
        data = []
        for aireDeJeux in liste_aire_de_jeux:
            next_aire_de_jeux = {"nom": aireDeJeux.nom,
                                 "indiceAireDeJeux": aireDeJeux.indice,
                                 "url": aireDeJeux.url,
                                 "coordonnees": ""}
            detail = aireDeJeux.detail.get()
            if detail.coordonnees:
                next_aire_de_jeux["coordonnees"] = {
                    "lat": detail.coordonnees.lat,
                    "lng": detail.coordonnees.lon
                }
            data.append(next_aire_de_jeux)
        data.sort(key=byName)
        self.response.write(json.dumps(data))


class ListeCommentaireHandler(webapp2.RequestHandler):
    def get(self):
        time.sleep(0.2)
        urlsafe_key_aire_de_jeux = self.request.get("q")
        key_aire_de_jeux = ndb.Key(urlsafe=urlsafe_key_aire_de_jeux)
        query_commentaire = Commentaire.query(Commentaire.aireDeJeux == key_aire_de_jeux)
        liste_commentaire = query_commentaire.fetch(30)
        data = []
        for commentaire in liste_commentaire:
            data.append(commentaire.commentaire)
        self.response.headers['Content-Type'] = 'text/json'
        self.response.write(json.dumps(data))


app = webapp2.WSGIApplication([
    ('/liste/Ville', ListeVilleHandler),
    ('/liste/AireDeJeux', ListeAireDeJeuxHandler),
    ('/liste/Commentaire', ListeCommentaireHandler),
    ('/liste/Image', ListeImageHandler)
    ], debug=True)
