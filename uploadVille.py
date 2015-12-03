# -*- coding: utf-8 -*-
import webapp2

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from dbClass import *
from google.appengine.datastore.datastore_query import Cursor


class MainHandler(webapp2.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/admin/upload')
        html_string = """
         <form action="%s" method="POST" enctype="multipart/form-data">
        Upload File:
        <input type="file" name="file"> <br>
        <input type="submit" name="submit" value="Submit">
        <a href='/admin/netoyerDoublon'>Netoyer es ville en doubles</a>
        <a href='/admin/lowerCaseVille'>Lower case the name of the city</a>
        </form>""" % upload_url

        self.response.write(html_string)


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        taskqueue.add(url='/admin/process_csv', params={'blob_key': blob_info.key(), 'cursor': 0})

        #blobstore.delete(blob_info.key())  # optional: delete file after import
        self.redirect("/")


class netoyerDoublonHandler(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/process_doublon')
        self.redirect("/admin/uploadform")

class processCsv(webapp2.RequestHandler):
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


class suprimeDoubleVille(webapp2.RequestHandler):
    def post(self):
        max_data_access = 10000
        curs = Cursor(urlsafe=self.request.get('cursor'))
        if curs :
            queryVille, next_cursor, more = Commune.query().fetch_page(max_data_access, start_cursor=curs)
        else:
            queryVille, next_cursor, more = Commune.query().fetch_page(max_data_access)

        for ville in queryVille:
            query_same = Commune.query(ndb.AND(ndb.AND(Commune.nom == ville.nom, Commune.departement == ville.departement),
                                               Commune.CP != ville.CP))
            for doublon in query_same:
                doublon.key.delete()

        if more:
            taskqueue.add(url='/admin/process_doublon', params={'cursor': next_cursor.urlsafe()},
                              countdown=86400)


class lowerCase(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/admin/lowerCaseVille')
        self.redirect("/admin/uploadform")

    def post(self):
        logging.info("do something")
        max_data_access = 5000
        curs = Cursor(urlsafe=self.request.get('cursor'))
        if curs:
            queryVille, next_cursor, more = Commune.query().fetch_page(max_data_access, start_cursor=curs)
        else:
            queryVille, next_cursor, more = Commune.query().fetch_page(max_data_access)
        logging.info(len(queryVille))
        for ville in queryVille:
            ville.put()

        if more:
            taskqueue.add(url='/admin/lowerCaseVille', params={'cursor': next_cursor.urlsafe()},
                              countdown=86400)

app = webapp2.WSGIApplication([
    ('/admin/uploadform', MainHandler),
    ('/admin/upload', UploadHandler),
    ('/admin/process_csv', processCsv),
    ('/admin/process_doublon', suprimeDoubleVille),
    ('/admin/netoyerDoublon', netoyerDoublonHandler),
    ('/admin/lowerCaseVille', lowerCase)

], debug=True)