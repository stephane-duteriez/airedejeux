# -*- coding: utf-8 -*-
# TODO avoir l'option de s'enregistrer avec un compt gmail
# TODO carte fix, modifiable en cliquant dessus et s'ouvre en grand.
# TODO recherche de place de jeux à proximité en dehors de la ville
# TODO indiquer  que lq photo est en téléchargemment
# TODO ajouter la posibilité d'ajouter un lien, doit etre validé
# TODO ajouter une page
import webapp2
import json
import time

import urllib
import cloudstorage as gcs

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

    def get(self, dep=None, ville=None, aireDeJeux=None):
        url = dep + "/" + ville + "/" + aireDeJeux
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


class AjouterHandler(webapp2.RequestHandler):
    def post(self):
        nom_aire_de_jeux = self.request.get('nom_aire_de_jeux').strip(" ")
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
        ville.nbr_aire_de_jeux += 1
        ville.put()
        departement = Departement.query(Departement.numero == ville.departement).get()
        departement.nbr_aire_de_jeux += 1
        departement.put()
        time.sleep(0.1)
        absolute_url = "/aireDeJeux/" + url
        self.redirect(urllib.quote(absolute_url.encode("utf-8")))


class ChercherHandler(Handler):
    # TODO mettre un lien sur chaque marqueur pour sélectionner l'aire de jeux en question
    def render_main(self):
        self.render("chercher.html")

    def get(self):
        self.render_main()


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


class ListeDepartementsHandler(Handler):
    def render_main(self, liste_departements):
        self.render("listeDepartement.html", liste_departements=liste_departements)

    def get(self):
        query_departement = Departement.query().order(Departement.numero).fetch(200)
        self.render_main(query_departement)


class DepartementHandler(Handler):
    def render_main(self, departement, lettre_dep, liste_communes):
        self.render("listeCommunes.html",
                    departement=departement,
                    lettre_departement=lettre_dep,
                    liste_communes=liste_communes)

    def get(self, dep=None):
        def byName(Commune):
            return Commune.nom
        query_commune = Commune.query(ndb.AND(Commune.departement == dep, Commune.nbr_aire_de_jeux > 0))\
            .fetch(200, projection=[Commune.nom, Commune.nbr_aire_de_jeux])
        query_departement = Departement.query(Departement.numero == dep).get()
        query_commune.sort(key=byName)
        lettre_dep = query_departement.lettre
        self.render_main(dep, lettre_dep, query_commune)


class CommuneHandler(Handler):
    def render_main(self, departement, commune, liste_aire_de_jeux):
        self.render("listeAireDeJeux.html", departement=departement, commune=commune, liste_aire_de_jeux=liste_aire_de_jeux)

    def get(self, dep=None, ville=None):
        def classement(enregistrement):
            reference = [(u"é", u"e"), (u"è", u"e"), (u"ê", u"e")]
            resultat = enregistrement.nom.lower()
            for item1, item2 in reference:
                resultat = resultat.replace(item1, item2)
            return resultat

        query_commune = Commune.query(ndb.AND(Commune.nom == ville, Commune.departement == dep))
        commune = query_commune.get()
        query_departement = Departement.query(Departement.numero == commune.departement).get()
        departement = query_departement.lettre
        key_ville = commune.key
        query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville == key_ville)\
            .fetch(200, projection=[AireDeJeux.nom])
        logging.info(query_aire_de_jeux)
        query_aire_de_jeux.sort(key=lambda x: classement(x))
        self.render_main(departement, commune.urlsafe(), query_aire_de_jeux)


class SiteMapHandler(Handler):
    def get(self):
        sitemap = gcs.open("/oujouerdehors/sitemap.xml")
        self.write(sitemap.read())


app = webapp2.WSGIApplication([
    ('/', ChercherHandler),
    ('/créerAireDeJeux', CreerAireDeJeuxHandler),
    ('/ajouterAireDeJeux', AjouterHandler),
    ('/aireDeJeux', ListeDepartementsHandler),
    webapp2.Route('/aireDeJeux/<dep>', DepartementHandler),
    webapp2.Route('/aireDeJeux/<dep>/<ville>', CommuneHandler),
    webapp2.Route('/aireDeJeux/<dep>/<ville>/<aireDeJeux>', AireDeJeuxHandler),
    ('/modifier/([^/]+)?', ModifierHandler),
    ('/add_photo', PhotoUploadFormHandler),
    ('/add_comment', AddCommentHandler),
    ('/view_photo/([^/]+)?', ViewPhotoHandler),
    ('/upload_photo', PhotoUploadHandler),
    ('/google21d16423d723f0d0.html', GoogleVerificationHandler),
    ('/verifierUnique', VerifierUniqueHandler),
    ('/sitemap.xml', SiteMapHandler)
         ], debug=True)

