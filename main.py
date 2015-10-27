
import webapp2
import jinja2
import os
from google.appengine.ext import ndb


template_dir = os.path.join(os.path.dirname(__file__), 'template')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


class AireDeJeux(ndb.Model):
    nom = ndb.StringProperty()
    ville = ndb.KeyProperty()
    activitee = ndb.StringProperty(repeated=True)
    score = ndb.IntegerProperty()
    horaires = ndb.StringProperty()
    accesibilite = ndb.StringProperty()
    description = ndb.StringProperty()
    coordonees = ndb.GeoPtProperty()


class User(ndb.Model):
    User = ndb.UserProperty()


class Commentaire(ndb.Model):
    userId = ndb.KeyProperty()
    aireDeJeux = ndb.KeyProperty()
    commentaire = ndb.StringProperty()
    valide = ndb.BooleanProperty()


class Commune(ndb.Model):
    nom = ndb.StringProperty()
    CP = ndb.IntegerProperty()
    coordonees = ndb.GeoPtProperty()


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @staticmethod
    def render_str(template, **params):
        t = jinja_env.get_template(template)
        return t.render(params).encode(encoding="utf-8")

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw).decode(encoding="utf-8"))


class MainHandler(Handler):
    def render_main(self):
        self.render("detail.html")

    def get(self):
        self.render_main()


class LocationHandler(Handler):
    def render_main(self):
        self.render("Commune.html")

    def get(self):
        self.render_main()


class CreerAireDeJeuxHandler(Handler):
    def render_main(self):
        self.render("nouvelleAireDeJeux.html")

    def get(self):
        self.render_main()


class AjouterHandler(Handler):
    def post(self):
        pass

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/Commune', LocationHandler),
    ('/creerAireDeJeux', CreerAireDeJeuxHandler),
    ('/ajouter', AjouterHandler)
], debug=True)
