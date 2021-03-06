# -*- coding: utf-8 -*-
import webapp2
import datetime
import json
import cloudstorage as gcs

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import taskqueue
from dbClass import *
from google.appengine.datastore.datastore_query import Cursor


template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


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


class MainHandler(webapp2.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/admin/upload')
        html_string = """
         <form action="%s" method="POST" enctype="multipart/form-data">
        Upload File:
        <input type="file" name="file"> <br>
        <input type="submit" name="submit" value="Submit">
        <div>
            <a href='/admin/netoyerDoublon'>Netoyer es ville en doubles</a>
        </div>
        <div>
            <a href='/admin/lowerCaseVille'>Lower case the name of the city</a>
        </div>
        <div>
            <a href='/admin/rest_compte_dep_ville'>recompt le nombre d'aire de jeux par département et par commune</a>
        </div>
        <div>
            <input type="radio" name="type_csv" value="ville"> Fichier des villes <br>
            <input type="radio" name="type_csv" value="departement" checked> Fichier des département <br>
        </div>
        <div>
            <a href='/admin/creat_sitemap_blob'>creer le fichier site map</a>
        </div>
        <div>
            <a href='/admin/ajout_date_creation'>Ajouter des dates sur les enregistrements de la base de données</a>
        </div>
        <div>
            <a href='/admin/a_valider'>Affichage des enregistrement a valider</a>
        </div>
        <div>
            <a href='/admin/ajout_fichier'>Ajout a partir d'un fichier de type json</a>
        </div>
        <div>
            <a href='/admin/ajout_fichier_csv'>Ajout a partir d'un fichier de type csv</a>
        </div>
        <div>
            <a href='/admin/ajout_limite_ville'>Ajout d'une limite autour des villes</a>
        </div>
        <div>
            <a href='/admin/ajout_limite_departement'>Ajout d'une limite autour des départements</a>
        </div>
        <div>
            <a href='/admin/cleanUrl'>Simplifier les url des aires des jeux</a>
        </div>
        <div>
            <a href='/admin/addmissingnumberurl'>Ajouter les nombres manquants pour la ville de Caen</a>
        </div>
        <div>
            <a href='/admin/ajouterCarvin'>Ajouter carvin</a>
        </div>
        </form>
        
        
        
        """ % upload_url

        self.response.write(html_string)


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
        type = self.request.get("type_csv")
        blob_info = upload_files[0]
        if type == "ville":
            taskqueue.add(url='/admin/process_csv', params={'blob_key': blob_info.key(), 'cursor': 0})
        elif type == "departement":
            taskqueue.add(url='/admin/departement_csv', params={'blob_key': blob_info.key()})
        # blobstore.delete(blob_info.key())  # optional: delete file after import
        self.redirect("/admin/")


class NetoyerDoublonHandler(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/process_doublon')
        self.redirect("/admin/")


class ProcessCsv(webapp2.RequestHandler):
    def post(self):
        max_data_access = 1000
        blob_info = self.request.get('blob_key')
        cursor = int(self.request.get('cursor'))
        blob_reader = blobstore.BlobReader(blob_info)
        i = 0
        for row in blob_reader:
            if i >= cursor and i < cursor + max_data_access:
                pays, CP, ville, info1, info2, departement, \
                numDepartement, arrond, numArrond, latitude, longitude, precision = row.split('\t')
                if len(CP) <= 5:
                    entry = Commune(nom=ville, CP=CP, departement=numDepartement, pays=pays,
                                    coordonnees=ndb.GeoPt(latitude + ", " + longitude))
                    queryVille = Commune.query(ndb.AND(Commune.nom == entry.nom, Commune.CP == entry.CP))
                    if queryVille.count() == 0:
                        entry.put()
            elif i >= cursor + max_data_access:
                next_cursor = cursor + max_data_access
                taskqueue.add(url='/admin/process_csv', params={'blob_key': blob_info,
                                                                'cursor': next_cursor},
                              countdown=21600)
                break
            i += 1


class DepartementCsv(webapp2.RequestHandler):
    def post(self):
        blob_info = self.request.get('blob_key')
        blob_reader = blobstore.BlobReader(blob_info)
        for row in blob_reader:
            old_num, num, nom, info1, info2, info3 = row.split(",")
            query_departement = Departement.query(Departement.numero == num[1:-1]).get()
            if query_departement:
                query_departement.lettre = nom[1:-1]
                query_departement.put()
            else:
                nouveau_departement = Departement(numero=num[1:-1], lettre=nom[1:-1])
                nouveau_departement.put()


class SuprimeDoubleVille(webapp2.RequestHandler):
    def post(self):
        max_data_access = 10000
        curs = Cursor(urlsafe=self.request.get('cursor'))
        if curs:
            query_ville, next_cursor, more = Commune.query().fetch_page(max_data_access, start_cursor=curs)
        else:
            query_ville, next_cursor, more = Commune.query().fetch_page(max_data_access)

        for ville in query_ville:
            query_same = Commune.query(ndb.AND(ndb.AND(Commune.nom == ville.nom, Commune.departement == ville.departement),
                                               Commune.CP != ville.CP))
            for doublon in query_same:
                doublon.key.delete()

        if more:
            taskqueue.add(url='/admin/process_doublon', params={'cursor': next_cursor.urlsafe()},
                              countdown=86400)


class LowerCase(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/lowerCaseVille')
        self.redirect("/admin/")

    def post(self):
        max_data_access = 7000
        curs = Cursor(urlsafe=self.request.get('cursor'))
        if curs:
            queryVille, next_cursor, more = Commune.query().fetch_page(max_data_access, start_cursor=curs)
        else:
            queryVille, next_cursor, more = Commune.query().fetch_page(max_data_access)
        for ville in queryVille:
            ville.put()

        if more:
            taskqueue.add(url='/admin/lowerCaseVille', params={'cursor': next_cursor.urlsafe()},
                              countdown=86400)


class RecompteHandler(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/rest_compte_dep_ville')
        self.redirect("/admin/")

    def post(self):
        max_data_access = 1000
        curs = Cursor(urlsafe=self.request.get('cursor'))
        query_ville = AireDeJeux.query(projection=[AireDeJeux.ville], distinct=True)
        if curs:
            liste_ville, next_cursor, more = query_ville.fetch_page(max_data_access, start_cursor=curs)
        else:
            liste_ville, next_cursor, more = query_ville.fetch_page(max_data_access)
        for key_ville in liste_ville:
            query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville == key_ville.ville)
            ville = key_ville.ville.get()
            ville.nbr_aire_de_jeux = query_aire_de_jeux.count()
            logging.info(ville.nom + ": " + str(ville.nbr_aire_de_jeux))
            ville.put()
        if more:
            taskqueue.add(url='/admin/rest_compte_dep_ville', params={'cursor': next_cursor.urlsafe()},
                              countdown=86400)
        else:
            query_departement = Commune.query(projection=[Commune.departement], distinct=True)
            for dep in query_departement:
                query_ville = Commune.query(Commune.departement == dep.departement).fetch(projection=[Commune.nbr_aire_de_jeux])
                count = 0
                for ville in query_ville:
                    count += ville.nbr_aire_de_jeux
                departement = Departement.query(Departement.numero == dep.departement).get()
                if departement:
                    departement.nbr_aire_de_jeux = count
                    departement.put()
                else:
                    new_departement = Departement(numero=dep.departement, nbr_aire_de_jeux=count)
                    new_departement.put()


class SitemapBlobHandler(webapp2.RequestHandler):
    def get(self):
        sitemap = gcs.open("/oujouerdehors/sitemap.xml", mode="w", content_type="text/xml")
        sitemap.write("""<?xml version="1.0" encoding="UTF-8"?>
                            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                                """)
        sitemap.write("""<url><loc>http://www.oujouerdehors.org/</loc>
                        <changefreq>monthly</changefreq>
                        <priority>1</priority></url>""")
        sitemap.write("""<url><loc>http://www.oujouerdehors.org/aireDeJeux</loc>
                        <changefreq>monthly</changefreq>
                        <priority>0.9</priority></url>""")
        template = """<url><loc>http://www.oujouerdehors.org/%DATA%</loc>
                        <changefreq>monthly</changefreq>
                        <priority>%SCORE%</priority></url>"""
        query_aire_de_jeux = AireDeJeux.query()
        for aire_de_jeux in query_aire_de_jeux:
            new_url = template.replace("%DATA%", "aireDeJeux/" + aire_de_jeux.url)
            new_url = new_url.replace("%SCORE%", "0.5")
            sitemap.write(new_url.encode("utf-8"))
        query_departement = Departement.query(Departement.nbr_aire_de_jeux > 0)
        for departement in query_departement:
            logging.info(departement.numero)
            new_url = template.replace("%DATA%", "aireDeJeux/" + departement.numero)
            new_url = new_url.replace("%SCORE%", "0.85")
            sitemap.write(new_url.encode("utf-8"))
        query_commune = Commune.query(Commune.nbr_aire_de_jeux > 0)
        for commune in query_commune:
            new_url = template.replace("%DATA%", "aireDeJeux/" + commune.departement + "/" + commune.nom)
            new_url = new_url.replace("%SCORE%", "0.75")
            sitemap.write(new_url.encode("utf-8"))
        sitemap.write("</urlset>")
        sitemap.close()
        self.redirect("/admin/")


class AjoutDateHandler(webapp2.RequestHandler):
    def get(self):
        curent_date = datetime.datetime.now()
        query_aire_de_jeux = AireDeJeux.query()
        for aire_de_jeux in query_aire_de_jeux:
            change = False
            if not aire_de_jeux.date_creation:
                aire_de_jeux.date_creation = curent_date
                change = True
            if not aire_de_jeux.valider:
                aire_de_jeux.valider = True
                change = True
            if change:
                aire_de_jeux.put()
        query_detail = Detail.query()
        for detail in query_detail:
            change = False
            if not detail.date_creation:
                detail.date_creation = curent_date
                change = True
            if not detail.valider:
                detail.valider = True
                change = True
            if change:
                detail.put()
        query_commentaire = Commentaire.query()
        for commentaire in query_commentaire:
            change = False
            if not commentaire.date_creation:
                commentaire.date_creation = curent_date
                change = True
            if not commentaire.valider:
                commentaire.valider = True
                change = True
            if change:
                commentaire.put()
        query_photos = Photo.query()
        for photo in query_photos:
            change = False
            if not photo.date_creation:
                photo.date_creation = curent_date
                change = True
            if not photo.valider:
                photo.valider = True
                change = True
            if change:
                photo.put()
        self.redirect("/admin/")


class AValiderHandler(Handler):
    def render_main(self, liste_aire_de_jeux, liste_details, liste_comments, liste_photos):
        self.render("a_valider.html",
                    liste_aire_de_jeux=liste_aire_de_jeux,
                    liste_details=liste_details,
                    liste_comments=liste_comments,
                    liste_photos=liste_photos)

    def get(self):
        query_aire_de_jeux = AireDeJeux.query(AireDeJeux.valider==False).fetch(100)
        query_details = Detail.query(Detail.valider==False).fetch(100)
        query_comments = Commentaire.query(Commentaire.valider==False).fetch(100)
        query_photos = Photo.query(Photo.valider==False).fetch(100)
        valider(False)
        self.render_main(query_aire_de_jeux, query_details, query_comments, query_photos)

    def post(self):
        urlsafe_key = self.request.get('key')
        logging.info("key=" + urlsafe_key)
        key = ndb.Key(urlsafe=urlsafe_key)
        enregistrement = key.get()
        enregistrement.valider = True
        enregistrement.put()


class AjouterFichierHandler(Handler):
    def render_main(self):
        upload_url = blobstore.create_upload_url('/admin/upload_aire_de_jeux')
        self.render("ajout_fichier_aire_de_jeux.html", upload_url=upload_url)

    def get(self):
        self.render_main()


class AjouterFichierBlobHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        key_ville = ndb.Key(urlsafe=self.request.get('key_ville'))
        ville = key_ville.get()
        departement = Departement.query(Departement.numero == ville.departement).get()
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        blob_key = blob_info.key()
        blob_reader = blobstore.BlobReader(blob_key)
        jason_value = unicode(blob_reader.read(), 'latin-1')
        data = json.loads(jason_value)
        liste_nom = {}
        list_coordonnees = []
        for aire_de_jeux in data:
            nom = aire_de_jeux[5][0][1][0]
            if nom[:4] == 'Aire':
                nom = nom[15:]
                coordonnees = ndb.GeoPt(float(aire_de_jeux[1][0][0][0]),
                                        float(aire_de_jeux[1][0][0][1]))
                if coordonnees not in list_coordonnees:
                    list_coordonnees.append(coordonnees)
                    if nom in liste_nom.iterkeys():
                        liste_nom[nom] += 1
                    else:
                        liste_nom[nom] = 0
                    # test_unique = AireDeJeux.query(ndb.AND(AireDeJeux.nom == nom, AireDeJeux.ville == key_ville))
                    count = ""
                    if liste_nom[nom] > 0:
                        count = " " + str(liste_nom[nom])
                    existe = True
                    while existe:
                        indice = random_str()
                        already_existe = AireDeJeux.query(AireDeJeux.indice == indice)
                        if already_existe.count() == 0:
                            existe = False
                    new_detail = Detail(indice=indice,
                                        valider=True,
                                        coordonnees=coordonnees)
                    detail_key = new_detail.put()
                    new_aire_de_jeux = AireDeJeux(nom=nom + count,
                                                  ville=key_ville,
                                                  indice=indice,
                                                  detail=detail_key,
                                                  valider=True,
                                                  url=ville.departement + "/" + ville.nom + "/" + nom)
                    new_aire_de_jeux.put()
                    ville.nbr_aire_de_jeux += 1
                    departement.nbr_aire_de_jeux += 1
        departement.put()
        ville.put()
        self.redirect("/admin/")


class AjouterBordureVille(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/ajout_limite_ville')
        self.redirect("/admin/")

    def post(self):
        max_data_access = 5000
        curs = Cursor(urlsafe=self.request.get('cursor'))
        query_ville = Commune.query()
        if curs:
            liste_ville, next_cursor, more = query_ville.fetch_page(max_data_access, start_cursor=curs)
        else:
            liste_ville, next_cursor, more = query_ville.fetch_page(max_data_access)
        for ville in liste_ville:
            query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville == ville.key)
            marge = 0.0015
            ville.NWcoordonnees = ndb.GeoPt(ville.coordonnees.lat + marge, ville.coordonnees.lon - marge)
            ville.SEcoordonnees = ndb.GeoPt(ville.coordonnees.lat - marge, ville.coordonnees.lon + marge)
            for aire_de_jeux in query_aire_de_jeux:
                detail = aire_de_jeux.detail.get()
                if detail.coordonnees:
                    if detail.coordonnees.lat > ville.NWcoordonnees.lat:
                        ville.NWcoordonnees.lat = detail.coordonnees.lat + marge/5
                    elif detail.coordonnees.lat < ville.SEcoordonnees.lat:
                        ville.SEcoordonnees.lat = detail.coordonnees.lat - marge/5
                    if detail.coordonnees.lon > ville.SEcoordonnees.lon:
                        ville.SEcoordonnees.lon = detail.coordonnees.lon + marge/5
                    elif detail.coordonnees.lon < ville.NWcoordonnees.lon:
                        ville.NWcoordonnees.lon = detail.coordonnees.lon - marge/5
            ville.put()
        if more:
            taskqueue.add(url='/admin/ajout_limite_ville', params={'cursor': next_cursor.urlsafe()}, countdown=86400)


class AjouterBordureDepartement(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/ajout_limite_departement')
        self.redirect("/admin/")

    def post(self):
        max_data_access = 5000
        query_departement = Departement.query()
        liste_departement, next_cursor, more = query_departement.fetch_page(max_data_access)
        for departement in liste_departement:
            query_commune = Commune.query(Commune.departement == departement.numero)
            marge = 0.002
            test = False
            for commune in query_commune:
                if not test:
                    departement.NWcoordonnees = ndb.GeoPt(commune.coordonnees.lat,
                                                          commune.coordonnees.lon)
                    departement.SEcoordonnees = ndb.GeoPt(commune.coordonnees.lat,
                                                          commune.coordonnees.lon)
                    test = True
                elif commune.coordonnees:
                    if commune.coordonnees.lat > departement.NWcoordonnees.lat:
                        departement.NWcoordonnees.lat = commune.coordonnees.lat + marge/5
                    elif commune.coordonnees.lat < departement.SEcoordonnees.lat:
                        departement.SEcoordonnees.lat = commune.coordonnees.lat - marge/5
                    if commune.coordonnees.lon > departement.SEcoordonnees.lon:
                        departement.SEcoordonnees.lon = commune.coordonnees.lon + marge/5
                    elif commune.coordonnees.lon < departement.NWcoordonnees.lon:
                        departement.NWcoordonnees.lon = commune.coordonnees.lon - marge/5
            departement.put()

class cleanUrlHandler(webapp2.RequestHandler):
    def get(self):
        curent_date = datetime.datetime.now()
        query_aire_de_jeux = AireDeJeux.query()
        for aire_de_jeux in query_aire_de_jeux:
            change = False
            if not aire_de_jeux.urldirty:
                aire_de_jeux.urldirty = aire_de_jeux.url
                aire_de_jeux.url = urlParse(aire_de_jeux.url)
                change = True                
            if change:
                aire_de_jeux.put()

class addmissingnumberurl(webapp2.RequestHandler):
    def get(self):
        query_aire_de_jeux = AireDeJeux.query(AireDeJeux.ville==ndb.Key("Commune",4534100874493952));
        for aire_de_jeux in query_aire_de_jeux:
            array_url = aire_de_jeux.url.split("/")
            if array_url[-1] != urlParse(aire_de_jeux.nom):
                array_url[-1]  = urlParse(aire_de_jeux.nom)
                aire_de_jeux.url = "/".join(array_url)
                aire_de_jeux.put()
        self.redirect("/admin/")

class ajouterCarvinHandler(webapp2.RequestHandler):
    def get(self):
        ville_carvin = Commune(nom="Courrière", departement="62", CP="62220", coordonnees = ndb.GeoPt(50.4924, 2.9582), SEcoordonnees = ndb.GeoPt(50.4924, 2.9582), NWcoordonnees = ndb.GeoPt(50.4924, 2.9582))
        #ville_carvin.put()
        new_departement = Departement(lettre="Pas de Calais", numero="62", nbr_aire_de_jeux=0, SEcoordonnees = ndb.GeoPt(50.4924, 2.9582), NWcoordonnees = ndb.GeoPt(50.4924, 2.9582) )
        new_departement.put()
        self.redirect("/admin/")

app = webapp2.WSGIApplication([
    ('/admin/', MainHandler),
    ('/admin/upload', UploadHandler),
    ('/admin/upload_aire_de_jeux', AjouterFichierBlobHandler),
    ('/admin/process_csv', ProcessCsv),
    ('/admin/departement_csv', DepartementCsv),
    ('/admin/process_doublon', SuprimeDoubleVille),
    ('/admin/netoyerDoublon', NetoyerDoublonHandler),
    ('/admin/lowerCaseVille', LowerCase),
    ('/admin/rest_compte_dep_ville', RecompteHandler),
    ('/admin/creat_sitemap_blob', SitemapBlobHandler),
    ('/admin/ajout_date_creation', AjoutDateHandler),
    ('/admin/a_valider', AValiderHandler),
    ('/admin/ajout_fichier', AjouterFichierHandler),
    ('/admin/ajout_limite_ville', AjouterBordureVille),
    ('/admin/ajout_limite_departement', AjouterBordureDepartement),
    ('/admin/addmissingnumberurl', addmissingnumberurl),
    ('/admin/cleanUrl', cleanUrlHandler),
    ('/admin/ajouterCarvin', ajouterCarvinHandler)
], debug=True)
