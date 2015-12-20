# -*- coding: utf-8 -*-
import jinja2
import os
import logging

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import mail

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


def send_mail_notification(subject, body):
    message = mail.EmailMessage(sender="aire-de-jeux notification <notification@aire-de-jeux.appspotmail.com>",
                                to="stephane.duteriez@gmail.com")
    message.body = body
    message.subject = subject
    message.send()


def valider(nouvelle_etat):
    a_valider = memcache.get("a_valider")
    if a_valider is None or a_valider != nouvelle_etat:
        variable = Variable.query().get()
        if not variable:
            variable = Variable()
        if not variable.a_valider or variable.a_valider != nouvelle_etat:
            variable.a_valider = nouvelle_etat
            variable.put()
            send_mail_notification("nouvelle enregistrement", "www.oujouerdehors.org/admin/a_valider")
        memcache.set('a_valider', nouvelle_etat)


class AireDeJeux(ndb.Model):
    nom = ndb.StringProperty(required=True)
    ville = ndb.KeyProperty(required=True)
    indice = ndb.StringProperty(required=True)
    detail = ndb.KeyProperty()
    url = ndb.StringProperty()
    date_creation = ndb.DateTimeProperty(auto_now_add=True)
    valider = ndb.BooleanProperty(default=False)

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
    date_creation = ndb.DateTimeProperty(auto_now_add=True)
    valider = ndb.BooleanProperty(default=False)


class Commune(ndb.Model):
    nom = ndb.StringProperty()
    CP = ndb.StringProperty()
    departement = ndb.StringProperty()
    pays = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()
    nom_lower = ndb.ComputedProperty(lambda self: self.nom.lower())
    nbr_aire_de_jeux = ndb.IntegerProperty(default=0)

    def urlsafe(self):
        data = {"urlsafeKey": self.key.urlsafe(),
                "CP": self.CP,
                "departement": self.departement,
                "coordonnees": self.coordonnees,
                "nom": self.nom}
        return data


class Departement(ndb.Model):
    numero = ndb.StringProperty()
    nbr_aire_de_jeux = ndb.IntegerProperty(default=0)
    lettre = ndb.StringProperty()


class Commentaire(ndb.Model):
    aireDeJeux = ndb.KeyProperty()
    commentaire = ndb.StringProperty()
    date_creation = ndb.DateTimeProperty(auto_now_add=True)
    valider = ndb.BooleanProperty(default=False)

    def str(self):
        return self.commentaire


class Photo(ndb.Model):
    blobKey = ndb.BlobKeyProperty()
    indice_aireDeJeux = ndb.StringProperty()
    photo_url = ndb.StringProperty()
    date_creation = ndb.DateTimeProperty(auto_now_add=True)
    valider = ndb.BooleanProperty(default=False)


class Variable(ndb.Model):
    a_valider = ndb.BooleanProperty()
