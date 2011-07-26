# -*- coding: utf-8 -*-
from infogami.utils import delegate
from infogami.utils.context import context
from infogami.utils.view import render, add_flash_message, public
from infogami.infobase.client import parse_datetime
from infogami import config
import web
from web.form import Form, Textbox, Password, File, Textarea, notnull, regexp, Validator
import os
import time
import simplejson
import datetime
import string
import random

import tweet
import blog
from blog import urlsafe

@public
def render_template(name, *a, **kw):
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return render[name](*a, **kw)
    
re_email = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,4}$'
    
form_talk = Form(
    Textbox("title", notnull),
    Textbox("talk_type", notnull),
    Textbox("authors", notnull),
    Textbox("contact", notnull, regexp(re_email, "Please enter a valid email address.")),
    Textbox("phone", notnull),
    Textarea("profile", notnull),
    Textbox("level", notnull),
    Textbox("topic", notnull),
    Textbox("tags"),
    Textarea("summary", notnull,
        Validator("Summary should have at least 10 words", lambda i: len(i.split())>=10)),
    Textarea("outline", notnull,
        Validator("Outline should have at least 25 words", lambda i: len(i.split())>=25)),
    Textarea("notes"),
)

form_upload = Form(
    Password("secret", notnull),
    File("file", notnull),
    Textbox("comment")
)

def new_talk(talk):
    talk['type'] = 'talk'
    talk['created_on'] = datetime.datetime.utcnow().isoformat()
    talk['secret'] = random_string()
    
    index = web.ctx.site.seq.next_value("talks")
    key = "talks/%d" % index
    web.ctx.site.store[key] = talk
    return key

def random_string(n=10):
    """Creates a random string of n chars."""
    return "".join(random.choice(string.lowercase) for i in range(n))
    
class submit_talk(delegate.page):
    path = "/talks/submit"
    
    def GET(self):
        f = form_talk()
        return render_template("talks/submit", form=f)
        
    def POST(self):
        i = web.input()
        f = form_talk()
        
        if not f.validates(i):
            return render_template("talks/submit", form=f)

        key = new_talk(i)
        
        if config.get('from_address') and config.get('talk_submission_contact'):
            email = render_template("talks/email", i)
            web.sendmail(
                from_address=config.from_address, 
                to_address=config.talk_submission_contact,
                subject=web.safestr(email.subject.strip()),
                message=web.safestr(email)
            )

        dir = config.get("talks_dir", "/tmp/talks")
        write("%s/%s.txt" % (dir, time.time()), simplejson.dumps(i))
        
        tweet.tweet("talk_template", title=i.title, author=i.authors, url=web.ctx.home + "/" + key)
        
        add_flash_message("info", "Thanks for submitting your talk. The selection committee will review your talk and get in touch with you shortly.")
        raise web.seeother("/" + key)
        
class display_talk(delegate.page):
    path = "/talks/(\d+)(.*)"
    
    def GET(self, id, title):
        talk = _get_talk(id, title)
        return render_template("talks/view", talk)
        
def _get_talk(id, title, suffix=""):
    title = title and title[1:] # strip leading hyphen
    try:
        talk = web.ctx.site.store["talks/" + id]
    except KeyError:
        raise web.notfound()
        
    xtitle = urlsafe(talk.get('title', 'untitled'))
    if xtitle != title:
        path = "/talks/%s-%s%s" % (id, xtitle, suffix)
        qs = web.ctx.env.get("QUERY_STRING")
        if qs:
            path += "?" + qs
        raise web.redirect(path)
        
    talk['key'] = 'talks/' + id
    talk['files'] = [web.storage(f) for f in talk.get('files', [])]
    talk = web.storage(talk)
    
    return talk
    
def is_admin():
    return context.user and context.user.key in [m.key for m in web.ctx.site.get('/usergroup/admin').members]

class edit_talk(delegate.page):
    path = "/talks/(\d+)(-.*)?/edit"
    
    def verify_code(self, talk):
        i = web.input(secret="", _method="GET")
        return is_admin() or i.secret == talk.get("secret")
        
    def GET(self, id, title):        
        talk = _get_talk(id, title, suffix="/edit")
        if self.verify_code(talk):
            f = form_talk()
            f.fill(talk)
            return render_template("talks/submit", form=f, edit=True)
        else:
            return render_template("permission_denied", web.ctx.path, "Permission denied to edit this talk.")
            
    def POST(self, id, title):
        talk = _get_talk(id, title, suffix="/edit")
        if self.verify_code(talk):
            i = web.input(_method="POST")
            for k in ["key", "type", "password"]:
                i.pop("password", None)
            
            f = form_talk()
            if not f.validates(i):
                return render_template("talks/submit", form=f, edit=True)
            else:
                talk.update(i)
                talk['revision'] = 1 + talk.get("revision", 1)
                
                dir = config.get("talks_dir", "/tmp/talks")
                write("%s/%s-%s.txt" % (dir, id, talk['revision']), simplejson.dumps(i))
                
                web.ctx.site.store["talks/%s" % id] = talk
                raise web.seeother("talks/%s" % id)
        else:
            return render_template("permission_denied", web.ctx.path, "Permission denied to edit this talk.")

class talk_attach(delegate.page):
    path = "/talks/(\d+)(-.*)?/upload"

    def verify_code(self, talk):
        i = web.input(secret="", _unicode=False)
        return is_admin() or i.secret == talk.get("secret")

    def GET(self, id, title):
        i = web.input(secret="")
        
        talk = _get_talk(id, title, suffix="/upload")
        form = form_upload()
        form.secret.value = i.secret
        return render_template("talks/upload", talk=talk, form=form)

    def POST(self, id, title):
        talk = _get_talk(id, title, suffix="/upload")
        
        i = web.input(file={}, comment="")
        form = form_upload()
        form.fill(i)
    
        if not self.verify_code(talk):
            form.note = "Incorrect password"
            return render_template("talks/upload", talk=talk, form=form)
            
        filename = i.file.filename.replace(" ", "-")
        # work-around for windoz
        if "\\" in filename:
            filename = filename.split("\\")[-1]
        data = i.file.value
        
        try:
            savefile(talk['key'], filename, data)
        except OverwriteError:
            form.note = "A file already exists with the given file name. Delete that file first if you want to overwrite."
            return render_template("talks/upload", talk=talk, form=form)
        
        f = {
            "name": filename,
            "size": self.prettysize(len(data)),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "comment": i.comment
        }
        files = talk.get('files', [])
        files.append(f)
        talk['files'] = files
        
        web.ctx.site.store[talk.key] = talk

        if config.get('from_address') and config.get('talk_submission_contact'):
            email = render_template("talks/file_uploaded_email", talk, filename)
            web.sendmail(
                from_address=config.from_address, 
                to_address=config.talk_submission_contact,
                subject=web.safestr(email.subject.strip()),
                message=web.safestr(email)
            )

        raise web.seeother("/" + talk.key)
        
    def prettysize(self, n):
        if n < 1024:
            return "%d bytes" % n
        elif n < 1024 * 1024:
            return "%.1f KB" % (n/1024.0)
        else:
            return "%.1f MB" % (n / (1024 * 1024.0))
            
class OverwriteError(IOError):
    pass
            
def savefile(key, filename, data):
    dir ="static/files/" + key
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    path = dir + "/" + filename
    
    if os.path.exists(path):
        raise OverwriteError("file already exists")
    
    f = open(path, 'w')
    f.write(data)
    f.close()

class talks(delegate.page):
    def GET(self):
        i = web.input(status="selected")
        items = web.ctx.site.store.items(type='talk', limit=1000)
        items = list(items)[::-1]
        
        if 'topic' in i:
            items = [(k, talk) for k, talk in items if talk.get('topic') == i.topic]

        if 'level' in i:
            items = [(k, talk) for k, talk in items if talk.get('level') == i.level]

        if 'talk_type' in i:
            items = [(k, talk) for k, talk in items if talk.get('talk_type') == i.talk_type]

        if i.status:
            items = [(k, talk) for k, talk in items if talk.get('status') == i.status]
        
        return render_template("talks/index", items)
        
class talks_edit(delegate.page):
    path = "/talks/edit"
    def GET(self):
        if not is_admin():
            return render_template("permission_denied", web.ctx.path, "Permission denied to modify talks.")
        else:
            items = web.ctx.site.store.items(type='talk', limit=1000)
            items = list(items)[::-1] # to order by id
            return render_template("talks/edit_all", items)
    
    def POST(self):
        i = dict((k, v) for k, v in web.input().items() if k.startswith("status-"))
        
        store = web.ctx.site.store
        for k, v in i.items():
            key = 'talks/' + web.numify(k)
            talk = store[key]
            if talk.get('status') != v:
                store[key] = dict(talk, status=v)
        
        raise web.seeother("/talks")

def write(path, text):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    f = open(path, 'w')
    f.write(text)
    f.close()
    
class Request:
    path = property(lambda self: web.ctx.path)
    home = property(lambda self: web.ctx.home)
    domain = property(lambda self: web.ctx.host)

web.template.Template.globals['request'] = Request()

@public
def get_cfp_status():
    return config.get("cfp_status")

public(web.numify)
public(parse_datetime)
