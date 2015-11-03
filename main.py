#TODO filtrer les donnee pour eviter les injections HTML
#TODO permettre la modification depuis la page Detail
#TODO avoir l'option de s'enregistrer avec un compt gmail
import webapp2
import jinja2
import os
from google.appengine.ext import ndb
import json
import logging

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


class AireDeJeux(ndb.Model):
    nom = ndb.StringProperty(required=True)
    ville = ndb.KeyProperty(required=True)
    activites = ndb.StringProperty(repeated=True)
    score = ndb.IntegerProperty()
    horaires = ndb.StringProperty()
    accesibilite = ndb.StringProperty()
    description = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()


class User(ndb.Model):
    User = ndb.UserProperty()


class Commentaire(ndb.Model):
    userId = ndb.KeyProperty()
    aireDeJeux = ndb.KeyProperty()
    commentaire = ndb.StringProperty()
    valide = ndb.BooleanProperty()


class Commune(ndb.Model):
    nom = ndb.StringProperty()
    CP = ndb.StringProperty()
    departement = ndb.StringProperty()
    pays = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @staticmethod
    def render_str(template, **params):
        t = jinja_env.get_template(template)
        return t.render(params).encode(encoding="utf-8")

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw).decode(encoding="utf-8"))


class MainHandler(Handler):
    def render_main(self):
        self.render("detail.html")

    def get(self):
        self.render_main()


class CreerAireDeJeuxHandler(Handler):
    #TODO cacher longitude et latitude
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
        commentaire = self.request.get('commentaire')
        nouvelleAireDeJeux = AireDeJeux(nom=nomAireDeJeux, ville=ndb.Key(urlsafe=keyVille))

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
        nouvelleAireDeJeux.put()
        self.redirect("/creerAireDeJeux")


class ChercherHandler(Handler):
    #TODO afficher un marker pour chaque aire de jeux sur la carte
    #TODO numeroter les markers sur la cartes
    #TODO mettre un lien sur chaque marqueur pour selecitioner l'aire de jeux en question
    #TODO cliquer sur une aire de jeux pour ouvrire la fenetre detaile
    def render_main(self):
        self.render("chercher.html")

    def get(self):
        self.render_main()


class ListAireDeJeuxHandler(webapp2.RequestHandler):
    def get(self):
        urlsafeKeyVille = self.request.get("keyVille")
        keyVille = ndb.Key(urlsafe=urlsafeKeyVille)
        queryAireDeJeux = AireDeJeux.query(AireDeJeux.ville == keyVille)
        listAireDeJeux = queryAireDeJeux.fetch(10)
        data = []
        for aireDeJeux in listAireDeJeux:
            nextADJ = {"nom": aireDeJeux.nom, "keyAireDeJeux": aireDeJeux.key.urlsafe(), "lat": "", "lng": ""}
            if aireDeJeux.coordonnees:
                nextADJ["lat"] = aireDeJeux.coordonnees.lat
                nextADJ["lng"] = aireDeJeux.coordonnees.lon
            data.append(nextADJ)
        self.response.write(json.dumps(data))


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/creerAireDeJeux', CreerAireDeJeuxHandler),
    ('/ajouterAireDeJeux', AjouterHandler),
    ('/chercher', ChercherHandler),
    ('/listAireDeJeux', ListAireDeJeuxHandler)
], debug=True)
