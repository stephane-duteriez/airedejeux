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
        detail = self.detail.get()
        ville = self.ville.get()
        data = {"key": self.key.urlsafe(),
                "nom": self.nom,
                "indice": self.indice,
                "url": self.url,
                "activites": detail.activites,
                "score": detail.score,
                "horaires": detail.horaires,
                "accessibilite": detail.accessibilite,
                "description": detail.description,
                "coordonnees": detail.coordonnees,
                "age": detail.age,
                "ville": ville.nom,
                "departement": ville.departement,
                "coordonnees_ville": ville.coordonnees,
                "key_ville": ville.key.urlsafe()
                }
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
    nom_lower = ndb.ComputedProperty(lambda self: self.nom.lower())

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
