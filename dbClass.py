# -*- coding: utf-8 -*-
import jinja2
import os

from google.appengine.ext import ndb

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
    age = ndb.StringProperty()
    indice = ndb.StringProperty(required=True)
    archive = ndb.BooleanProperty(default=False, required=True)

    def str(self):
        # TODO probleme d'encoding
        text = jinja_env.get_template("email_body_detail.txt")
        return text.render(nom=self.nom,
                           activites=self.activites,
                           score=self.score,
                           horaires=self.horaires,
                           age=self.age,
                           accesibilite=self.accesibilite,
                           description=self.description)


class Commune(ndb.Model):
    nom = ndb.StringProperty()
    CP = ndb.StringProperty()
    departement = ndb.StringProperty()
    pays = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()

    def urlsafe(self):
        data = {"urlsafeKey": self.key.urlsafe(),
                "CP": self.CP,
                "departement": self.departement,
                "coordonnees": self.coordonnees,
                "nom": self.nom}
        return data


class User(ndb.Model):
    User = ndb.UserProperty()


class Commentaire(ndb.Model):
    userId = ndb.KeyProperty()
    aireDeJeux = ndb.StringProperty()
    commentaire = ndb.StringProperty()
    valide = ndb.BooleanProperty()

    def str(self):
        return self.commentaire

class Photo(ndb.Model):
    blobKey = ndb.BlobKeyProperty()
    indice_aireDeJeux = ndb.StringProperty()
    photo_url = ndb.StringProperty()
