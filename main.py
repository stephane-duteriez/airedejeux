# -*- coding: utf-8 -*-
# TODO permettre la modification depuis la page Detail
# TODO avoir l'option de s'enregistrer avec un compt gmail
# TODO nettoyer les codes postales avec une seule entre par ville
# TODO ajout d'un commentaire directement depuis la page detail
# TODO changer l'affichage des ville "CARVIN (62)" est abandonner le CP
# TODO carte fix, modifiable en cliquant dessus et s'ouvre en grand.
# TODO recherche de place de jeux à proximité en dehors de la ville
# TODO ajouter des photos depuis detail et modifier
import webapp2
import jinja2
import os
import json
import logging


from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api.images import get_serving_url

from dbClass import *

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


# utilisé pour créer un indice aléatoire pour chaque indice
def random_str():
    return os.urandom(16).encode('hex')


class Handler(webapp2.RequestHandler):
    # Handler modifier pour intégrer la prise ne charge de jinja
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @staticmethod
    def render_str(template, **params):
        t = jinja_env.get_template(template)
        return t.render(params).encode(encoding="utf-8")

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw).decode(encoding="utf-8"))


class AireDeJeuxHandler(Handler):
    def render_main(self, aire_de_jeux, ville, listCommentaires, listImage):
        self.render("detail.html", aireDeJeux=aire_de_jeux, ville=ville, listCommentaires=listCommentaires, listImage=listImage)

    def get(self, indice):
        dbAireDeJeux = AireDeJeux.query(ndb.AND(AireDeJeux.indice == indice, AireDeJeux.archive == False)).get()
        ville = dbAireDeJeux.ville.get()
        queryCommentaire = Commentaire.query(Commentaire.aireDeJeux == dbAireDeJeux.indice)
        listCommentaires = queryCommentaire.fetch(10)
        queryPhotos = Photo.query(Photo.indice_aireDeJeux == dbAireDeJeux.indice)
        listImage = queryPhotos.fetch(10)
        self.render_main(dbAireDeJeux, ville, listCommentaires, listImage)


class CreerAireDeJeuxHandler(Handler):
    # TODO mettre de filtre pour valider les donnee avant de les envoyer vers la base de donnee
    # TODO changer le fonctionement du bouton Ajouter pour vérifier que l'utilisateur à submit avant de quiter la page
    def render_main(self, indice="",  dataVille=""):
        self.render("nouvelleAireDeJeux.html", new_indice=indice, ville=dataVille)

    def get(self):
        urlsafeKeyVille = self.request.get("keyVille")

        existe = True
        while existe:
            indice = random_str()
            alreadyExist = AireDeJeux.query(AireDeJeux.indice == indice)
            if alreadyExist.count() == 0:
                existe = False

        if urlsafeKeyVille:
            keyVille = ndb.Key(urlsafe=urlsafeKeyVille)
            ville = keyVille.get()
            self.render_main(indice, ville.urlsafe())
        else:
            self.render_main(indice)


class ListeVilleHandler(webapp2.RequestHandler):
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


class ListeImageHandler(webapp2.RequestHandler):
    def get(self):
        indice = self.request.GET['q']
        logging.info(indice)
        queryPhotos = Photo.query(Photo.indice_aireDeJeux == indice)
        listImage = queryPhotos.fetch(10)
        logging.info(listImage)
        data = []
        for image in listImage:
            data.append(image.photo_url)
        self.response.write(json.dumps(data))


class AjouterHandler(webapp2.RequestHandler):
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
        indice = self.request.get('indice')
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
    def render_main(self, aireDeJeux, ville, listImage):
        self.render("modifier.html", aireDeJeux=aireDeJeux, ville=ville, listImage=listImage)

    def get(self, indice):
        dbAireDeJeux = AireDeJeux.query(ndb.AND(AireDeJeux.indice == indice, AireDeJeux.archive == False)).get()
        ville = dbAireDeJeux.ville.get()
        queryPhotos = Photo.query(Photo.indice_aireDeJeux == dbAireDeJeux.indice)
        listImage = queryPhotos.fetch(10)
        self.render_main(dbAireDeJeux, ville, listImage)

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


class PhotoUploadFormHandler(Handler):
    def render_main(self, upload_url, indice):
        self.render("uploadPhoto.html", upload_url=upload_url, indice=indice)

    def get(self):
        indice = self.request.get('indice')
        upload_url = blobstore.create_upload_url('/upload_photo')
        logging.info('PhotoUploadForm, upload_url:' + upload_url)
        # To upload files to the blobstore, the request method must be "POST"
        # and enctype must be set to "multipart/form-data".
        self.render_main(upload_url, indice)


class PhotoUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        indice = self.request.get('indice')
        try:
            upload = self.get_uploads()[0]
            photo = Photo(indice_aireDeJeux=indice, blobKey=upload.key(), photo_url=get_serving_url(upload.key()))
            photo.put()
            self.redirect('/add_photo?indice=' + indice)
        except:
            self.error(500)


class ViewPhotoHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, photo_key):
        if not blobstore.get(photo_key):
            self.error(404)
        else:
            self.send_blob(photo_key)


app = webapp2.WSGIApplication([
    ('/', ChercherHandler),
    ('/creerAireDeJeux', CreerAireDeJeuxHandler),
    ('/ajouterAireDeJeux', AjouterHandler),
    ('/chercher', ChercherHandler),
    ('/listeVille', ListeVilleHandler),
    ('/listAireDeJeux', ListAireDeJeuxHandler),
    ('/airedejeux/([^/]+)?', AireDeJeuxHandler),
    ('/modifier/([^/]+)?', ModifierHandler),
    ('/add_photo', PhotoUploadFormHandler),
    ('/view_photo/([^/]+)?', ViewPhotoHandler),
    ('/upload_photo', PhotoUploadHandler),
    ('/listeImage', ListeImageHandler)
], debug=True)
