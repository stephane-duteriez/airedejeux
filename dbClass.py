# -*- coding: utf-8 -*-
import jinja2
import os
import logging

from google.appengine.ext import ndb

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


class AireDeJeux(ndb.Model):
    nom = ndb.StringProperty(required=True)
    ville = ndb.KeyProperty(required=True)
    indice = ndb.StringProperty(required=True)
    detail = ndb.KeyProperty()
    url = ndb.StringProperty()

    def export(self):
        data = {}
        data["nom"] = self.nom
        data["indice"] = self.indice
        data["url"] = self.url
        detail = self.detail.get()
        data["activites"] = detail.activites
        data["score"] = detail.score
        data["horaires"] = detail.horaires
        data["accessibilite"] = detail.accessibilite
        data["description"] = detail.description
        data["coordonnees"] = detail.coordonnees
        data["age"] = detail.age
        ville = self.ville.get()
        data["ville"] = ville.nom
        data["departement"] = ville.departement
        data["coordonnees_ville"] = ville.coordonnees
        logging.info(data)
        return data

    def str(self):
        text = jinja_env.get_template("email_body_detail.txt")
        detail = self.detail.get()
        return text.render(nom=self.nom,
                           activites=detail.activites,
                           score=detail.score,
                           horaires=detail.horaires,
                           age=detail.age,
                           accessibilite=detail.accessibilite,
                           description=detail.description)


class Detail(ndb.Model):
    indice = ndb.StringProperty()
    activites = ndb.StringProperty(repeated=True)
    score = ndb.IntegerProperty()
    horaires = ndb.StringProperty()
    accessibilite = ndb.StringProperty()
    description = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()
    age = ndb.StringProperty()



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


class Commentaire(ndb.Model):
    userId = ndb.KeyProperty()
    aireDeJeux = ndb.KeyProperty()
    commentaire = ndb.StringProperty()
    valide = ndb.BooleanProperty()

    def str(self):
        return self.commentaire


class Photo(ndb.Model):
    blobKey = ndb.BlobKeyProperty()
    indice_aireDeJeux = ndb.StringProperty()
    photo_url = ndb.StringProperty()
