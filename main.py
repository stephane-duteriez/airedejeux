# -*- coding: utf-8 -*-
# TODO avoir l'option de s'enregistrer avec un compt gmail
# TODO carte fix, modifiable en cliquant dessus et s'ouvre en grand.
# TODO recherche de place de jeux à proximité en dehors de la ville
# TODO indiquer  que lq photo est en téléchargemment
# TODO améliorer la visualisation sur mobile avec des materiel bord à bords
import webapp2
import json
import time

import urllib

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api.images import get_serving_url
from google.appengine.api import mail

from dbClass import *

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


def send_mail_notification(subject, body):
    message = mail.EmailMessage(sender="aire-de-jeux notification <notification@aire-de-jeux.appspotmail.com>",
                                to="stephane.duteriez@gmail.com")
    message.body = body
    message.subject = subject
    logging.info(body)
    message.send()


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
    def render_main(self, aire_de_jeux, liste_commentaires, liste_images):
        self.render("detail.html",
                    aireDeJeux=aire_de_jeux,
                    listCommentaires=liste_commentaires,
                    listImage=liste_images)

    def get(self, url):
        logging.info(url)
        db_aire_de_jeux = AireDeJeux.query(AireDeJeux.url == url).get()
        query_commentaire = Commentaire.query(Commentaire.aireDeJeux == db_aire_de_jeux.key)
        list_commentaires = query_commentaire.fetch(10)
        query_photo = Photo.query(Photo.indice_aireDeJeux == db_aire_de_jeux.indice)
        liste_images = query_photo.fetch(10)
        self.render_main(db_aire_de_jeux.export(), list_commentaires, liste_images)


class CreerAireDeJeuxHandler(Handler):
    # TODO mettre de filtre pour valider les donnee avant de les envoyer vers la base de donnee
    # TODO changer le fonctionement du bouton Ajouter pour vérifier que l'utilisateur à submit avant de quiter la page
    def render_main(self, indice="", data_ville=""):
        self.render("modifier.html", new_indice=indice, ville=data_ville, aireDeJeux="", nouveau="true")

    def get(self):
        urlsafe_key_ville = self.request.get("keyVille")
        existe = True
        while existe:
            indice = random_str()
            already_existe = AireDeJeux.query(AireDeJeux.indice == indice)
            if already_existe.count() == 0:
                existe = False

        if urlsafe_key_ville:
            key_ville = ndb.Key(urlsafe=urlsafe_key_ville)
            ville = key_ville.get()
            self.render_main(indice, ville.urlsafe())
        else:
            self.render_main(indice)


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
        logging.info(indice)
        query_photos = Photo.query(Photo.indice_aireDeJeux == indice)
        liste_images = query_photos.fetch(10)
        logging.info(liste_images)
        data = []
        for image in liste_images:
            data.append(image.photo_url)
        self.response.write(json.dumps(data))


class AjouterHandler(webapp2.RequestHandler):
    def post(self):
        nom_aire_de_jeux = self.request.get('nom_aire_de_jeux')
        key_ville = self.request.get('key_ville')
        latitude = self.request.get('lat')
        longitude = self.request.get('lng')
        score = self.request.get('score')
        horaire = self.request.get('horaire')
        accessibilite = self.request.get('acces')
        liste_activites = self.request.get_all('activites')
        description = self.request.get('description')
        age = self.request.get('age')
        commentaire = self.request.get('commentaire')
        indice = self.request.get('indice')
        ville = ndb.Key(urlsafe=key_ville).get()
        url = ville.departement + "/" + ville.nom + "/" + nom_aire_de_jeux
        nouvelle_aire_de_jeux = AireDeJeux(nom=nom_aire_de_jeux, ville=ville.key, indice=indice, url=url)
        # TODO vérifier qu'il n'éxiste pas déjà une aire de jeux avec le meme nom
        nouveau_detail = Detail(indice=indice)
        if latitude and longitude:
            nouveau_detail.coordonnees = ndb.GeoPt(float(latitude), float(longitude))
        if score:
            nouveau_detail.score = int(score)
        if accessibilite:
            nouveau_detail.accessibilite = accessibilite
        if horaire:
            nouveau_detail.horaires = horaire
        if liste_activites:
            nouveau_detail.activites = liste_activites
        if description:
            nouveau_detail.description = description
        if age:
            nouveau_detail.age = age
        nouveau_detail.put()
        nouvelle_aire_de_jeux.detail = nouveau_detail.key
        key_aire_de_jeux = nouvelle_aire_de_jeux.put()
        if commentaire:
            nouveau_commentaire = Commentaire(aireDeJeux=key_aire_de_jeux, commentaire=commentaire)
            send_mail_notification("nouveaux commentaire", nouveau_commentaire.str())
            nouveau_commentaire.put()
        send_mail_notification("nouvelle aire-de-jeux", nouvelle_aire_de_jeux.str())
        time.sleep(0.1)
        absolute_url = "/aireDeJeux/" + url
        self.redirect(urllib.quote(absolute_url.encode("utf-8")))


class ChercherHandler(Handler):
    # TODO mettre un lien sur chaque marqueur pour sélectionner l'aire de jeux en question
    def render_main(self):
        self.render("chercher.html")

    def get(self):
        self.render_main()


class ListAireDeJeuxHandler(webapp2.RequestHandler):
    def get(self):
        urlsafe_key_ville = self.request.get("keyVille")
        key_ville = ndb.Key(urlsafe=urlsafe_key_ville)
        query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville == key_ville)
        liste_aire_de_jeux = query_aire_de_jeux.fetch(30)
        data = []
        for aireDeJeux in liste_aire_de_jeux:
            next_aire_de_jeux = {"nom": aireDeJeux.nom,
                                 "indiceAireDeJeux": aireDeJeux.indice,
                                 "url": aireDeJeux.url,
                                 "lat": "",
                                 "lng": ""}
            detail = aireDeJeux.detail.get()
            if detail.coordonnees:
                next_aire_de_jeux["lat"] = detail.coordonnees.lat
                next_aire_de_jeux["lng"] = detail.coordonnees.lon
            data.append(next_aire_de_jeux)
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


class ModifierHandler(Handler):
    def render_main(self, aire_de_jeux, ville, list_image):
        self.render("modifier.html",
                    aireDeJeux=aire_de_jeux,
                    ville=ville,
                    listImage=list_image,
                    nouveau="false")

    def get(self, indice):
        db_aire_de_jeux = AireDeJeux.query(AireDeJeux.indice == indice).get()
        ville = db_aire_de_jeux.ville.get()
        query_photos = Photo.query(Photo.indice_aireDeJeux == db_aire_de_jeux.indice)
        list_image = query_photos.fetch(10)
        self.render_main(db_aire_de_jeux.export(), ville.urlsafe(), list_image)

    def post(self, indice):
        db_aire_de_jeux = AireDeJeux.query(AireDeJeux.indice == indice).get()
        db_detail = Detail(indice=indice)
        latitude = self.request.get('lat')
        longitude = self.request.get('lng')
        score = self.request.get('score')
        horaire = self.request.get('horaire')
        accessibilite = self.request.get('acces')
        liste_activites = self.request.get_all('activites')
        description = self.request.get('description')
        age = self.request.get('age')
        commentaire = self.request.get('commentaire')

        if latitude and longitude:
            db_detail.coordonnees = ndb.GeoPt(float(latitude), float(longitude))
        if score and score != '"None"':
            db_detail.score = int(score)
        if accessibilite and accessibilite != '"None"':
            db_detail.accessibilite = accessibilite
        if horaire and horaire != '"None"':
            db_detail.horaires = horaire
        if liste_activites:
            db_detail.activites = liste_activites
        if description and description != '"None"':
            db_detail.description = description
        if age and age != '"None"':
            db_detail.age = age

        key_detail = db_detail.put()
        db_aire_de_jeux.detail = key_detail
        db_aire_de_jeux.put()

        if commentaire:
            nouveau_commentaire = Commentaire(aireDeJeux=db_aire_de_jeux.key, commentaire=commentaire)
            send_mail_notification("nouveaux commentaire", nouveau_commentaire.str())
            nouveau_commentaire.put()

        time.sleep(0.1)
        send_mail_notification("nouvelle aire-de-jeux", db_aire_de_jeux.str())

        absolut_url = "/aireDeJeux/" + db_aire_de_jeux.url
        self.redirect(urllib.quote(absolut_url.encode("utf-8")))


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
            time.sleep(0.1)
            self.redirect('/add_photo?indice=' + indice)
        except:
            self.error(500)


class AddCommentHandler(Handler):
    def render_main(self, key):
        self.render("newComment.html", key=key)

    def get(self):
        key = self.request.get('key')
        self.render_main(key)

    def post(self):
        key_aire_de_jeux = self.request.get("key")
        comment = self.request.get("commentaire")
        new_comment = Commentaire(
            aireDeJeux=ndb.Key(urlsafe=key_aire_de_jeux),
            commentaire=comment
        )
        new_comment.put()
        send_mail_notification("new comment", new_comment.str())
        self.redirect('/add_comment?key=' + key_aire_de_jeux)


class ViewPhotoHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, photo_key):
        if not blobstore.get(photo_key):
            self.error(404)
        else:
            self.send_blob(photo_key)


class VerifierUniqueHandler(webapp2.RequestHandler):
    def get(self):
        key_ville = ndb.Key(urlsafe=self.request.get("keyVille"))
        nom_aire_de_jeux = self.request.get("nom")
        query_existe = AireDeJeux.query(ndb.AND(AireDeJeux.nom == nom_aire_de_jeux, AireDeJeux.ville == key_ville))
        result = True
        if query_existe.get():
            result = False
        logging.info(result)
        self.response.write(json.dumps(result))


class GoogleVerificationHandler(Handler):
    def render_main(self):
        self.render("google21d16423d723f0d0.html")

    def get(self):
        self.render_main()

app = webapp2.WSGIApplication([
    ('/', ChercherHandler),
    ('/créerAireDeJeux', CreerAireDeJeuxHandler),
    ('/ajouterAireDeJeux', AjouterHandler),
    ('/listeVille', ListeVilleHandler),
    ('/listAireDeJeux', ListAireDeJeuxHandler),
    ('/listeCommentaire', ListeCommentaireHandler),
    ('/aireDeJeux/(.*)?', AireDeJeuxHandler),
    ('/modifier/([^/]+)?', ModifierHandler),
    ('/add_photo', PhotoUploadFormHandler),
    ('/add_comment', AddCommentHandler),
    ('/view_photo/([^/]+)?', ViewPhotoHandler),
    ('/upload_photo', PhotoUploadHandler),
    ('/listeImage', ListeImageHandler),
    ('/google21d16423d723f0d0.html', GoogleVerificationHandler),
    ('/verifierUnique', VerifierUniqueHandler)
], debug=True)
