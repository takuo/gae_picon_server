#
# Copyright 2010 (c) Takuo Kitame <kitame@debian.org> 
#
# This program can be (re)distributed under GPLv2
#

import os
import datetime
import time
import hashlib
import urllib
import logging
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch
from picon.model import PiDevice
from picon.model import PiUser
from picon.model import Settings

class SendHandler(webapp.RequestHandler):
    def send(self, dev, event, text, priority):
        q = db.GqlQuery("SELECT * FROM Settings")
        settings = q.get()
        token = settings.token
        header = {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': 'GoogleLogin auth=' + token
        }
        params = {
          'registration_id': dev.devregid,
          'collapse_key': "picon",
          'data.event': event,
          'data.text': text,
          'data.priority': priority
        }
        data = urllib.urlencode(params)
        res = urlfetch.fetch(url='https://android.apis.google.com/c2dm/send',
                             payload=data,
                             method='POST',
                             headers=header)
        if not res.status_code == 200:
            logging.info("C2DM response: " + str(res.status_code))
            return False
        logging.info("Response: " + res.content)
        if res.headers.has_key('update_client_auth') and res.headers['update_client_auth'] != token:
            settings.token = res.headers['update_client_auth']
            settings.put()
            token = res.headers['update_client_auth']
        return True

    def get(self):
        self.response.set_status(400)
        self.response.out.write("<html><body><h1>Invalid request</body></html>")

    def post(self):
        self.response.headers.add_header('Content-Type', 'application/json')
        key = self.request.get('key')
        event = self.request.get('event') or "none"
        text = self.request.get('text') or "null"
        priority = self.request.get('priority') or 0
        q = db.GqlQuery("SELECT * FROM PiUser WHERE token = :1", key)
        if not q.count > 0:
            self.response.out.write('{"status":403, "error":"Invalid key token"}')
            return
        u = q.get()
        if u:
            q = db.GqlQuery("SELECT * FROM PiDevice WHERE owner = :1 AND active = true", u.account)
            if q.count() > 0:
                for dev in q.fetch(1000):
                    if not self.send(dev, event, text, priority):
                        self.response.out.write('{"status":500, "error":"could not send C2DM"}')
                        return
            else:
                self.response.out.write('{"status":200, "body":"done nothing"}')
                return
        else:
            self.response.out.write('{"status":200, "body":"done nothing."}')
            return
        self.response.out.write('{"status":200}')

class RegisterHandler(webapp.RequestHandler):
    def get(self):
        self.response.set_status(400)
        self.response.out.write("<html><body><h1>Invalid request</body></html>")

    def post(self):
        self.response.headers.add_header('Content-Type', 'application/json')
        devregid = self.request.get('devregid')
        devid = self.request.get('devid')
        if devid == None or devregid == None:
            self.response.set_status(400)
            self.response.out.write("<html><body><h1>Invalid request</body></html>")
            return

        user = users.get_current_user()
        q = db.GqlQuery("SELECT * FROM PiDevice WHERE owner = :1 AND devid = :2" , user, devid)
        if q.count() > 0:
            dev = q.get()
            dev.active = True
            dev.put()
        else:
            dev = PiDevice(devregid=devregid,devid=devid,owner=user,active=True,create=datetime.datetime.now())
            dev.put()
        self.response.out.write('{"status":200}')

class UnregisterHandler(webapp.RequestHandler):
    def get(self):
        self.response.set_status(400)
        self.response.out.write("<html><body><h1>Invalid request</body></html>")

    def post(self):
        self.response.headers.add_header('Content-Type', 'application/json')
        devid = self.request.get('devid')
        if devid == None:
            self.response.set_status(400)
            self.response.out.write("<html><body><h1>Invalid request</body></html>")
            return

        user = users.get_current_user()
        q = db.GqlQuery("SELECT * FROM PiDevice WHERE owner = :1 AND id = :2" , user, devid)
        if q.count() > 0:
            dev = q.get()
            dev.delete()
        self.response.out.write('{"status":200}')

class DashBoardHandler(webapp.RequestHandler):
    def gentoken(self, user):
        # do nothing
        string = "%s&%s&%s&%s " % ( user,  self.request.remote_addr, time.localtime(), "")
        return hashlib.sha1(string).hexdigest()

    def get(self):
        user = users.get_current_user()
        query = db.GqlQuery("SELECT * from PiUser WHERE account = :1", user)
        c2dmuser = query.get()
        if not c2dmuser:
            token = self.gentoken(user)
            c2dmuser = PiUser(account=user,active=True,token=token,
                                create=datetime.datetime.now())
            c2dmuser.put()

        query = db.GqlQuery("SELECT * from PiDevice WHERE owner = :1", c2dmuser.account)
        if query.count() > 0:
            devices = query.fetch(1000)
        else:
            devices = None

        template_values = {
          'user': c2dmuser.account.email(),
          'signout_url': users.create_logout_url('/'),
          'token': c2dmuser.token,
          'devices': devices
        } 
        path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
        self.response.out.write(template.render(path, template_values))

app = webapp.WSGIApplication([('/', DashBoardHandler),
                              ('/send', SendHandler),
                              ('/register', RegisterHandler),
                              ('/unregister', UnregisterHandler)
                              ], debug=True)

def load_conf():
    q = db.GqlQuery("SELECT * FROM Settings")
    settings = q.get()
    if not settings or settings.token == None:
        path = os.path.join(os.path.dirname(__file__), 'token.txt')
        fp = open(path, "r")
        token = fp.readline().rstrip()
        fp.close()
        if not settings:
            settings = Settings()
        settings.token = token
        settings.put()

def main():
    load_conf()
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
