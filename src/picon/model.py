from google.appengine.ext import db

class PiUser(db.Model):
    account = db.UserProperty(required=True)
    token  = db.StringProperty(required=True)
    active = db.BooleanProperty(required=True)
    create = db.DateTimeProperty(required=True)

class PiDevice(db.Model):
    devregid = db.StringProperty(required=True)
    devid = db.StringProperty(required=True)
    owner = db.UserProperty(required=True)
    active = db.BooleanProperty(required=True)
    create = db.DateTimeProperty(required=True)
