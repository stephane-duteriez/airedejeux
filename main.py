# -*- coding: utf-8 -*-
# TODO avoir l'option de s'enregistrer avec un compt gmail
# TODO ajout d'un commentaire directement depuis la page detail
# TODO carte fix, modifiable en cliquant dessus et s'ouvre en grand.
# TODO recherche de place de jeux à proximité en dehors de la ville
# TODO ajouter action sur le bouton "+" pour inserer un mouveau commentaire
# TODO indiquer  que lq photo est en téléchargement
import webapp2
import json
import time

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
        logging.info(db_aire_de_jeux.export())
        self.render_main(db_aire_de_jeux.export(), list_commentaires, liste_images)


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
        queryPhotos = Photo.query(Photo.indice_aireDeJeux == indice)
        listImage = queryPhotos.fetch(10)
        logging.info(listImage)
        data = []
        for image in listImage:
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
        text_activites = self.request.get('activites')
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
        if text_activites:
            liste_activites = [activite.strip() for activite in text_activites.split(",")]
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
        self.redirect("/aireDeJeux/" + url)


class ChercherHandler(Handler):
    # TODO mettre un lien sur chaque marqueur pour sélectionner l'aire de jeux en question
    def render_main(self):
        self.render("chercher.html")

    def get(self):
        self.render_main()


class ListAireDeJeuxHandler(webapp2.RequestHandler):
    def get(self):
        urlsafeKeyVille = self.request.get("keyVille")
        keyVille = ndb.Key(urlsafe=urlsafeKeyVille)
        queryAireDeJeux = AireDeJeux.query(AireDeJeux.ville == keyVille)
        listAireDeJeux = queryAireDeJeux.fetch(30)
        data = []
        for aireDeJeux in listAireDeJeux:
            nextADJ = {"nom": aireDeJeux.nom,
                       "indiceAireDeJeux": aireDeJeux.indice,
                       "url": aireDeJeux.url,
                       "lat": "",
                       "lng": ""}
            detail = aireDeJeux.detail.get()
            if detail.coordonnees:
                nextADJ["lat"] = detail.coordonnees.lat
                nextADJ["lng"] = detail.coordonnees.lon
            data.append(nextADJ)
        self.response.write(json.dumps(data))


class ModifierHandler(Handler):
    def render_main(self, aire_de_jeux, ville, list_image):
        self.render("modifier.html", aireDeJeux=aire_de_jeux, ville=ville, listImage=list_image)

    def get(self, indice):
        db_aire_de_jeux = AireDeJeux.query(AireDeJeux.indice == indice).get()
        ville = db_aire_de_jeux.ville.get()
        db_detail = db_aire_de_jeux.detail.get()
        query_photos = Photo.query(Photo.indice_aireDeJeux == db_aire_de_jeux.indice)
        list_image = query_photos.fetch(10)
        self.render_main(db_aire_de_jeux.export(), ville, list_image)

    def post(self, indice):
        dbAireDeJeux = AireDeJeux.query(AireDeJeux.indice == indice).get()
        db_detail = Detail(indice=indice)
        latitude = self.request.get('lat')
        longitude = self.request.get('lng')
        score = self.request.get('score')
        horaire = self.request.get('horaire')
        accessibilite = self.request.get('acces')
        textActivites = self.request.get('activites')
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
        if textActivites and textActivites != '"None"':
            list_activites = [activite.strip() for activite in textActivites.split(",")]
            db_detail.activites = list_activites
        if description and description != '"None"':
            db_detail.description = description
        if age and age != '"None"':
            db_detail.age = age

        key_detail = db_detail.put()
        dbAireDeJeux.detail = key_detail
        dbAireDeJeux.put()

        if commentaire:
            nouveau_commentaire = Commentaire(aireDeJeux=dbAireDeJeux.key, commentaire=commentaire)
            send_mail_notification("nouveaux commentaire", nouveau_commentaire.str())
            nouveau_commentaire.put()

        time.sleep(0.1)
        send_mail_notification("nouvelle aire-de-jeux", dbAireDeJeux.str())
        self.redirect("/aireDeJeux/" + dbAireDeJeux.url)


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
        queryExiste = AireDeJeux.query(ndb.AND(AireDeJeux.nom == nom_aire_de_jeux, AireDeJeux.ville == key_ville))
        resulta = True
        if queryExiste.get():
            resulta = False
        logging.info(resulta)
        self.response.write(json.dumps(resulta))


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
    ('/aireDeJeux/(.*)?', AireDeJeuxHandler),
    ('/modifier/([^/]+)?', ModifierHandler),
    ('/add_photo', PhotoUploadFormHandler),
    ('/view_photo/([^/]+)?', ViewPhotoHandler),
    ('/upload_photo', PhotoUploadHandler),
    ('/listeImage', ListeImageHandler),
    ('/google21d16423d723f0d0.html', GoogleVerificationHandler),
    ('/verifierUnique', VerifierUniqueHandler)
], debug=True)
