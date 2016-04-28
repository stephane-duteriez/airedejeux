# -*- coding: utf-8 -*-
# TODO avoir l'option de s'enregistrer avec un compt gmail
# TODO carte fix, modifiable en cliquant dessus et s'ouvre en grand.
# TODO recherche de place de jeux à proximité en dehors de la ville
# TODO indiquer  que lq photo est en téléchargemment
# TODO ajouter la posibilité d'ajouter un lien, doit etre validé
# TODO permettre de localiser le marker a partir de la position du téléphone
# TODO faire une page pour valider ou supprimer facilement les derniere mise a jour de la base e données
import webapp2
import json
import time

import urllib
import cloudstorage as gcs

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api.images import get_serving_url

from dbClass import *

template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


class Handler(webapp2.RequestHandler):
    # Handler modifié pour intégrer la prise ne charge de jinja
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @staticmethod
    def render_str(template, **params):
        t = jinja_env.get_template(template)
        return t.render(params).encode(encoding="utf-8")

    def render(self, template, **kw):
        host = self.request.host_url
        self.write(self.render_str(template, host=host, **kw).decode(encoding="utf-8"))

    def test_appspot(self):
        # test le nom de domaine et redirige vers oujouerdehors dans le cas contraire
        if not self.request.host.endswith('-dot-aire-de-jeux.appspot.com') and not self.request.host.endswith('8080'):
            return self.redirect('http://www.oujouerdehors.org', True)


class AireDeJeuxHandler(Handler):
    # génère la page de description d'une aire de jeux
    def render_main(self, aire_de_jeux, liste_commentaires, liste_images):
        self.render("detail.html",
                    aireDeJeux=aire_de_jeux,
                    listCommentaires=liste_commentaires,
                    listImage=liste_images)

    def get(self, dep=None, ville=None, aireDeJeux=None):
        self.test_appspot()  # test l'url
        url = dep + "/" + ville + "/" + aireDeJeux
        # recherche une aire de jeux correspondant à l'url
        db_aire_de_jeux = AireDeJeux.query(AireDeJeux.url == url).get()
        # renvoi un message d'erreur si la page n'existe pas
        if not db_aire_de_jeux:
            self.write("Désolé mais cette page n'éxiste pas.")
        # recherche d'éventuels commentaires attachés à cette aire de jeux
        query_commentaire = Commentaire.query(Commentaire.aireDeJeux == db_aire_de_jeux.key)
        # limite à 10 commentaires
        # TODO trier les commentaires et les photos par date pour afficher les derniers
        list_commentaires = query_commentaire.fetch(10)
        # recherche les photos attachées à cette aire de jeux
        query_photo = Photo.query(Photo.indice_aireDeJeux == db_aire_de_jeux.indice)
        liste_images = query_photo.fetch(10)
        self.render_main(db_aire_de_jeux.export(), list_commentaires, liste_images)


class CreerAireDeJeuxHandler(Handler):
    # TODO mettre de filtre pour valider les donnee avant de les envoyer vers la base de donnee
    # TODO changer le fonctionement du bouton Ajouter pour vérifier que l'utilisateur à submit avant de quiter la page
    def render_main(self, indice="", data_ville=""):
        self.render("modifier.html", new_indice=indice, ville=data_ville, aireDeJeux="", nouveau="true")

    def get(self):
        self.test_appspot()  # test l'url
        urlsafe_key_ville = self.request.get("keyVille")  # récupère la clé de la ville si elle est déjà présente
        existe = True  # crée un indice unique pour la nouvelle aire de jeux
        while existe:
            indice = random_str()
            already_existe = AireDeJeux.query(AireDeJeux.indice == indice)
            if already_existe.count() == 0:  # recommence jusqu'à ce que l'indice ne soit pas déjà utilisé
                existe = False

        if urlsafe_key_ville:
            # si il y a un paramètre de ville, récupérer les information sur la ville est préremplire le formulaire
            key_ville = ndb.Key(urlsafe=urlsafe_key_ville)
            ville = key_ville.get()
            self.render_main(indice, ville.urlsafe())
        else:
            # sinon afficher un formulaire vierge
            self.render_main(indice)


class AjouterHandler(webapp2.RequestHandler):
    #  Permet d'ajouter une nouvelle aire de jeux
    def post(self):
        #  efface les espace en début et fin pour éviter des erreurs avec les urls
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
        website = self.request.get('website')
        adresse = self.request.get('adresse')
        ville = ndb.Key(urlsafe=key_ville).get()
        url = ville.departement + "/" + ville.nom + "/" + nom_aire_de_jeux  # construit le url de la page
        nouvelle_aire_de_jeux = AireDeJeux(nom=nom_aire_de_jeux,
                                           ville=ville.key,
                                           indice=indice,
                                           url=url)
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
            nouveau_detail.dpescription = description
        if age:
            nouveau_detail.age = age
        if website:
            if website[0:4] == "http":  # ajoute http devant le nom sinon il n'est pas reconnu en href
                nouveau_detail.website = website
            else:
                nouveau_detail.website = "http://" + website
        if adresse:
            nouveau_detail.adresse = adresse
        nouveau_detail.put()
        nouvelle_aire_de_jeux.detail = nouveau_detail.key
        key_aire_de_jeux = nouvelle_aire_de_jeux.put()
        if commentaire:
            nouveau_commentaire = Commentaire(aireDeJeux=key_aire_de_jeux, commentaire=commentaire)
            nouveau_commentaire.put()
        valider(True)  # envoy en email pour demander la validation des entrées
        ville.nbr_aire_de_jeux += 1  # incrémente le nombre d'aire de jeux dans la ville
        ville.put()
        departement = Departement.query(Departement.numero == ville.departement).get()
        departement.nbr_aire_de_jeux += 1  # incrément le nombre d'aire de jeux dans le département
        departement.put()
        time.sleep(0.1)  # donne du temps à la base de donnée de se mettre à jour.
        absolute_url = "/aireDeJeux/" + url
        self.redirect(urllib.quote(absolute_url.encode("utf-8")))


class ChercherHandler(Handler):
    #  gère la page de démarrage pour rechercher les aires de jeux par ville
    def render_main(self):
        self.render("chercher.html")

    def get(self):
        self.test_appspot()
        self.render_main()


class ModifierHandler(Handler):
    # permet de modifier une aire de jeux déjà existante
    def render_main(self, aire_de_jeux, ville, list_image):
        self.render("modifier.html",
                    aireDeJeux=aire_de_jeux,
                    ville=ville,
                    listImage=list_image,
                    nouveau="false")

    def get(self, indice):
        self.test_appspot()
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
        website = self.request.get('website')
        adresse = self.request.get('adresse')

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
        if adresse and adresse != '"None"':
            db_detail.adresse = adresse
        if website:
            if website[0:4] == "http":
                db_detail.website = website
            else:
                db_detail.website = "http://" + website
        key_detail = db_detail.put()
        db_aire_de_jeux.detail = key_detail
        db_aire_de_jeux.put()

        if commentaire:
            nouveau_commentaire = Commentaire(aireDeJeux=db_aire_de_jeux.key, commentaire=commentaire)
            nouveau_commentaire.put()
        # donne du temps à la base de donnée pour enregistrer la nouvelle aire de jeux
        time.sleep(0.1)
        valider(True)  # envoi un émail si nécessaire pour demander une validation
        # renvoie sur la page de description du nouvelle enregistrement
        absolut_url = "/aireDeJeux/" + db_aire_de_jeux.url
        self.redirect(urllib.quote(absolut_url.encode("utf-8")))


class PhotoUploadFormHandler(Handler):
    # création de la page pour ajouter des photos
    def render_main(self, upload_url, indice):
        self.render("uploadPhoto.html", upload_url=upload_url, indice=indice)

    def get(self):
        indice = self.request.get('indice')  # récupère l'indice de l'aire de jeux pour lier celle-ci avec la photo
        upload_url = blobstore.create_upload_url('/upload_photo')
        # To upload files to the blobstore, the request method must be "POST"
        # and enctype must be set to "multipart/form-data".
        self.render_main(upload_url, indice)


class PhotoUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    # gestion de l'ajout des nouvelles photos
    def post(self):
        indice = self.request.get('indice')  # récupère l'indice de l'aire de jeux
        try:
            upload = self.get_uploads()[0]
            photo = Photo(indice_aireDeJeux=indice, blobKey=upload.key(), photo_url=get_serving_url(upload.key()))
            photo.put()
            valider(True)
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
        valider(True)
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
        self.test_appspot()
        query_departement = Departement.query().order(Departement.numero).fetch(200)
        self.render_main(query_departement)


class DepartementHandler(Handler):
    def render_main(self, departement, liste_communes):
        self.render("listeCommunes.html",
                    departement=departement,
                    liste_communes=liste_communes)

    def get(self, dep=None):
        self.test_appspot()

        def byName(Commune):
            return Commune.nom
        query_commune = Commune.query(ndb.AND(Commune.departement == dep, Commune.nbr_aire_de_jeux > 0))\
            .fetch(500)
        query_departement = Departement.query(Departement.numero == dep).get()
        query_commune.sort(key=byName)
        self.render_main(query_departement, query_commune)


class CommuneHandler(Handler):
    # Affiche une page qui liste les aires-de-jeux sur une commune
    def render_main(self, departement, commune, liste_aire_de_jeux):
        self.render("listeAireDeJeux.html",
                    departement=departement,
                    commune=commune,
                    liste_aire_de_jeux=liste_aire_de_jeux)

    def get(self, dep=None, ville=None):
        self.test_appspot()
        def classement(enregistrement):
            # améliore l'ordre alphabétique pour mieux prendre en compte les accents
            reference = [(u"é", u"e"), (u"è", u"e"), (u"ê", u"e")]
            resultat = enregistrement["nom"].lower()
            for item1, item2 in reference:
                resultat = resultat.replace(item1, item2)
            return resultat

        query_commune = Commune.query(ndb.AND(Commune.nom == ville, Commune.departement == dep))
        commune = query_commune.get()
        query_departement = Departement.query(Departement.numero == commune.departement).get()
        departement = query_departement.lettre
        key_ville = commune.key
        query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville == key_ville)\
            .fetch(200, projection=[AireDeJeux.nom, AireDeJeux.url, AireDeJeux.detail])
        liste_aire_de_jeux = []
        for aire_de_jeux in query_aire_de_jeux:
            detail = aire_de_jeux.detail.get()
            record_aire_de_jeux = {
                "nom": aire_de_jeux.nom,
                "url": aire_de_jeux.url,
                "coordonnees": detail.coordonnees
            }
            liste_aire_de_jeux.append(record_aire_de_jeux)
        logging.info(query_aire_de_jeux)
        liste_aire_de_jeux.sort(key=lambda x: classement(x)) # mais les aire-de-jeux par ordre alphabétique
        self.render_main(departement, commune.urlsafe(), liste_aire_de_jeux)


class SiteMapHandler(Handler):
    def get(self):
        sitemap = gcs.open("/oujouerdehors/sitemap.xml")
        self.write(sitemap.read())


class InfoHandler(Handler):
    def get(self):
        self.render("info.html")

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
    ('/sitemap.xml', SiteMapHandler),
    ('/info', InfoHandler)
         ], debug=True)

