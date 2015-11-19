from google.appengine.ext import ndb


class AireDeJeux(ndb.Model):
    nom = ndb.StringProperty(required=True)
    ville = ndb.KeyProperty(required=True)
    activites = ndb.StringProperty(repeated=True)
    score = ndb.IntegerProperty()
    horaires = ndb.StringProperty()
    accesibilite = ndb.StringProperty()
    description = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()
    age = ndb.StringProperty()
    indice = ndb.StringProperty(required=True)
    archive = ndb.BooleanProperty(default=False, required=True)


class Commune(ndb.Model):
    nom = ndb.StringProperty()
    CP = ndb.StringProperty()
    departement = ndb.StringProperty()
    pays = ndb.StringProperty()
    coordonnees = ndb.GeoPtProperty()

    def urlsafe(self):
        data = {"urlsafeKey": self.key.urlsafe(),
                "CP": self.CP,
                "departement": self.departement,
                "coordonnees": self.coordonnees,
                "nom": self.nom}
        return data


class User(ndb.Model):
    User = ndb.UserProperty()


class Commentaire(ndb.Model):
    userId = ndb.KeyProperty()
    aireDeJeux = ndb.StringProperty()
    commentaire = ndb.StringProperty()
    valide = ndb.BooleanProperty()


class Photo(ndb.Model):
    blobKey = ndb.BlobKeyProperty()
    indice_aireDeJeux = ndb.StringProperty()
    photo_url = ndb.StringProperty()
