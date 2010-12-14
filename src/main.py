#
# Copyright 2010 (c) Takuo Kitame <kitame@debian.org> 
#
# This program can be (re)distributed under GPLv2
#

import datetime
import time
import hashlib
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from picon.model import PiDevice
from picon.model import PiUser

class SendHandler(webapp.RequestHandler):
    def get(self):
        self.response.set_status(400)
        self.response.out.write("<html><body><h1>Invalid request</body></html>")

    def post(self):
        self.response.headers.add_header('Content-Type', 'application/json')
        key = self.request.get('key')
        event = self.request.get('event')
        text = self.request.get('text')
        prio = self.request.get('priority')
        q = db.GqlQuery("SELECT * FROM PiUser WHERE token = :1", key)
        if not q.count > 0:
            self.response.out.write('{"status":403, "error":"Invalid key token"}')
            return
        u = q.get()
        q = db.GqlQuery("SELECT * FROM PiDevice WHERE owner = :1 AND active = true", u.account)
#        if q.count() > 0:
#            for dev in q.fetch():
#                # C2DM Sending method here

        self.response.out.write('{"status":200}')

class RegisterHandler(webapp.RequestHandler):
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
            dev.active = True
            dev.put()
        else:
            dev = PiDevice(id=devid,owner=user,active=True,create=datetime.datetime.now())
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

        string = "<div style='float:right'><b>%s</b> | <a href='%s'>Sign out</a></div>" % (c2dmuser.account, users.create_logout_url('/'))
        string += "<h1>Dashboard</h1>"
        string += "<p>API Key: %s</p>" % c2dmuser.token
        string += "<p>Registered devices</p>"

        query = db.GqlQuery("SELECT * from PiDevice WHERE owner = :1", c2dmuser.account)
        if query.count() > 0:
            devices = query.fetch()
            table = "<table><tr><th>enable</th><th>ID</th></tr>\n"
            for dev in devices:
                tr = "<tr><td>%s</td><td>%s</td></tr>\n" % (dev.active, dev.id)
                table += tr
            table += "</table>"
            string += table
        else:
            string += "<p><i>No devices registered.</i></p>\n"
        string += "<p>Send test message</p>"
        self.response.out.write("<html><body>%s</body></html>" % string)

app = webapp.WSGIApplication([('/', DashBoardHandler),
                              ('/send', SendHandler),
                              ('/register', RegisterHandler),
                              ('/unregister', UnregisterHandler)
                              ], debug=True)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
