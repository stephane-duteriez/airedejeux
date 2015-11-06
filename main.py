#TODO permettre la modification depuis la page Detail
#TODO avoir l'option de s'enregistrer avec un compt gmail
import webapp2
import jinja2
import os
import json
import logging
import hashlib

from dbClass import *

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


def hash_str(s):
        return hashlib.md5(s.encode('utf-8')).hexdigest()


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @staticmethod
    def render_str(template, **params):
        t = jinja_env.get_template(template)
        return t.render(params).encode(encoding="utf-8")

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw).decode(encoding="utf-8"))


class AireDeJeuxHandler(Handler):
    def render_main(self, aire_de_jeux, ville, listCommentaires):
        self.render("detail.html", aireDeJeux=aire_de_jeux, ville=ville, listCommentaires=listCommentaires)

    def get(self, indice):
        dbAireDeJeux = AireDeJeux.query(ndb.AND(AireDeJeux.indice == indice, AireDeJeux.archive == False)).get()
        ville = dbAireDeJeux.ville.get()
        queryCommentaire = Commentaire.query(Commentaire.aireDeJeux == dbAireDeJeux.indice)
        listCommentaires = queryCommentaire.fetch(10)
        logging.info(listCommentaires)
        self.render_main(dbAireDeJeux, ville.nom, listCommentaires)


class CreerAireDeJeuxHandler(Handler):
    #TODO mettre de filtre pour valider les donnee avant de les envoyer vers la base de donnee
    #TODO permettre l'ajout de photos
    def render_main(self):
        self.render("nouvelleAireDeJeux.html")

    def get(self):
        self.render_main()


class AjouterHandler(webapp2.RequestHandler):
    def get(self):
        q = (self.request.GET['q']).title()
        villes = Commune.query(ndb.AND(Commune.nom >= q, Commune.nom <= q + "z"))
        self.response.headers['Content-Type'] = 'text/json'
        results = villes.fetch(10)
        data = {"ville": []}
        for ville in results:
            data["ville"].append({"name": ville.nom, "CP": ville.CP, "key": ville.key.urlsafe(),
                                  "lat": ville.coordonnees.lat, "lon": ville.coordonnees.lon})
        self.response.write(json.dumps(data))

    def post(self):
        nomAireDeJeux = self.request.get('nom_aire_de_jeux')
        keyVille = self.request.get('key_ville')
        latitude = self.request.get('lat')
        longitude = self.request.get('lng')
        score = self.request.get('score')
        horaire = self.request.get('horaire')
        accessibilite = self.request.get('acces')
        textActivites = self.request.get('activites')
        description = self.request.get('description')
        age = self.request.get('age')
        commentaire = self.request.get('commentaire')

        existe = True
        indice = hash_str(keyVille + nomAireDeJeux)
        while existe:
            alreadyExist = AireDeJeux.query(AireDeJeux.indice == indice)
            if alreadyExist.count() == 0:
                existe = False
            indice = hash_str(indice)

        nouvelleAireDeJeux = AireDeJeux(nom=nomAireDeJeux, ville=ndb.Key(urlsafe=keyVille), indice=indice)

        if latitude and longitude:
            nouvelleAireDeJeux.coordonnees = ndb.GeoPt(float(latitude), float(longitude))
        if score:
            nouvelleAireDeJeux.score = int(score)
        if accessibilite:
            nouvelleAireDeJeux.accesibilite = accessibilite
        if horaire:
            nouvelleAireDeJeux.horaires = horaire
        if textActivites:
            listActivites = [activite.strip() for activite in textActivites.split(",")]
            nouvelleAireDeJeux.activites = listActivites
        if description:
            nouvelleAireDeJeux.description = description
        if age:
            nouvelleAireDeJeux.age = age
        if commentaire:
            nouveauCommentaire = Commentaire(aireDeJeux=indice, commentaire=commentaire)
            nouveauCommentaire.put()
        nouvelleAireDeJeux.put()
        self.redirect("/creerAireDeJeux")


class ChercherHandler(Handler):
    #TODO mettre un lien sur chaque marqueur pour selecitioner l'aire de jeux en question
    def render_main(self):
        self.render("chercher.html")

    def get(self):
        self.render_main()


class ListAireDeJeuxHandler(webapp2.RequestHandler):
    def get(self):
        urlsafeKeyVille = self.request.get("keyVille")
        keyVille = ndb.Key(urlsafe=urlsafeKeyVille)
        queryAireDeJeux = AireDeJeux.query(ndb.AND(AireDeJeux.ville == keyVille, AireDeJeux.archive == False))
        listAireDeJeux = queryAireDeJeux.fetch(10)
        data = []
        for aireDeJeux in listAireDeJeux:
            nextADJ = {"nom": aireDeJeux.nom, "indiceAireDeJeux": aireDeJeux.indice, "lat": "", "lng": ""}
            if aireDeJeux.coordonnees:
                nextADJ["lat"] = aireDeJeux.coordonnees.lat
                nextADJ["lng"] = aireDeJeux.coordonnees.lon
            data.append(nextADJ)
        self.response.write(json.dumps(data))


class ModifierHandler(Handler):
    def render_main(self, aireDeJeux, ville):
        self.render("modifier.html", aireDeJeux=aireDeJeux, ville=ville)

    def get(self, indice):
        dbAireDeJeux = AireDeJeux.query(ndb.AND(AireDeJeux.indice == indice, AireDeJeux.archive == False)).get()
        ville = dbAireDeJeux.ville.get()
        self.render_main(dbAireDeJeux, ville)

    def post(self, indice):
        dbAireDeJeux = AireDeJeux.query(ndb.AND(AireDeJeux.indice == indice, AireDeJeux.archive == False)).get()
        ville = dbAireDeJeux.ville.get()
        nomAireDeJeux = self.request.get('nom_aire_de_jeux')
        keyVille = self.request.get('key_ville')
        latitude = self.request.get('lat')
        longitude = self.request.get('lng')
        score = self.request.get('score')
        horaire = self.request.get('horaire')
        accessibilite = self.request.get('acces')
        textActivites = self.request.get('activites')
        description = self.request.get('description')
        age = self.request.get('age')
        commentaire = self.request.get('commentaire')
        nouvelleAireDeJeux = AireDeJeux(nom=nomAireDeJeux, ville=ville.key, indice=indice)

        if latitude and longitude:
            nouvelleAireDeJeux.coordonnees = ndb.GeoPt(float(latitude), float(longitude))
        if score and score != '"None"':
            nouvelleAireDeJeux.score = int(score)
        if accessibilite and accessibilite != '"None"':
            nouvelleAireDeJeux.accesibilite = accessibilite
        if horaire and horaire != '"None"':
            nouvelleAireDeJeux.horaires = horaire
        if textActivites and textActivites != '"None"':
            listActivites = [activite.strip() for activite in textActivites.split(",")]
            nouvelleAireDeJeux.activites = listActivites
        if description and description != '"None"':
            nouvelleAireDeJeux.description = description
        if age and age != '"None"':
            nouvelleAireDeJeux.age = age
        if commentaire:
            nouveauCommentaire = Commentaire(aireDeJeux=indice, commentaire=commentaire)
            nouveauCommentaire.put()
        nouvelleAireDeJeux.put()
        dbAireDeJeux.archive = True
        dbAireDeJeux.put()
        self.redirect("/")

app = webapp2.WSGIApplication([
    ('/', ChercherHandler),
    ('/creerAireDeJeux', CreerAireDeJeuxHandler),
    ('/ajouterAireDeJeux', AjouterHandler),
    ('/chercher', ChercherHandler),
    ('/listAireDeJeux', ListAireDeJeuxHandler),
    ('/airedejeux/([^/]+)?', AireDeJeuxHandler),
    ('/modifier/([^/]+)?', ModifierHandler)
], debug=True)
