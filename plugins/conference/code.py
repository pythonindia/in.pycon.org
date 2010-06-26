# -*- coding: utf-8 -*-
from infogami.utils import delegate
from infogami.utils.view import render, add_flash_message, public
from infogami import config
import web
from web.form import Form, Textbox, Textarea, notnull, regexp, Validator
import os
import time
import simplejson

from tools import captcha

@public
def render_template(name, *a, **kw):
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return render[name](*a, **kw)
    
re_email = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,4}$'
    
form_talk = Form(
    Textbox("title", notnull),
    Textbox("duration", notnull),
    Textbox("authors", notnull),
    Textbox("contact", notnull, regexp(re_email, "Please enter a valid email address.")),
    Textarea("profile", notnull),
    Textbox("level", notnull),
    Textbox("topic", notnull),
    Textbox("tags"),
    Textarea("summary", notnull,
        Validator("Summary should be at least 10 words or more", lambda i: len(i.split())>=10)),
    Textarea("outline", notnull,
        Validator("Outline should be at least 100 words or more", lambda i: len(i.split())>=100)),
    Textarea("notes"),
)

import threading
talk_lock = threading.Lock()

def new_talk(talk):
    talk['type'] = 'talk'

    talk_lock.acquire()
    try:
        index = 1 + len(web.ctx.site.store.keys(type='talk', limit=1000))
        key = "talks/%d" % index
        web.ctx.site.store[key] = talk
    finally: 
        talk_lock.release()
    return key

class submit_talk(delegate.page):
    path = "/talks/submit"
    
    def GET(self):
        f = form_talk()
        c = captcha.displayhtml(public_key="6LeHGbsSAAAAAPwlmoQCVUYlP_vip_iXv5vAAcEN")
        return render_template("talks/submit", form=f, captcha=c)
        
    def POST(self):
        i = web.input()
        f = form_talk()
        
        if not f.validates(i):
            c = captcha.displayhtml(public_key="6LeHGbsSAAAAAPwlmoQCVUYlP_vip_iXv5vAAcEN")
            return render_template("talks/submit", form=f, captcha=c)

        if not captcha.submit( i.recaptcha_challenge_field, i.recaptcha_response_field,
                                    "6LeHGbsSAAAAANlVLj-gvWA5mkv1ztTnoJJcJYRv", web.ctx.ip).is_valid:
            c = captcha.displayhtml(public_key="6LeHGbsSAAAAAPwlmoQCVUYlP_vip_iXv5vAAcEN")
            return render_template("talks/submit", form=f, captcha=c, captcha_error = "Are you human?")
                
            
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
        
        add_flash_message("info", "Thanks for submitting your talk. The selection committee will review your talk and get in touch with you shortly.")
        raise web.seeother("/" + key)
        
class display_talk(delegate.page):
    path = "/talks/(\d+)(.*)"
    
    def GET(self, id, title):
        title = title.lstrip("-").replace("-", " ")
        try:
            talk = web.ctx.site.store["talks/" + id]
        except KeyError:
            raise web.notfound()
            
        xtitle = talk.get('title', 'untitled')
        if xtitle != title:
            path = "/talks/%s-%s" % (id, xtitle.replace(" ", "-"))
            raise web.redirect(path)
            
        talk = web.storage(talk)
        return render_template("talks/view", talk)
        
class talks(delegate.page):
    def GET(self):
        i = web.input()
        items = web.ctx.site.store.items(type='talk', limit=1000)
        items = list(items)
        
        if 'topic' in i:
            items = [(k, talk) for k, talk in items if talk.get('topic') == i.topic]

        if 'level' in i:
            items = [(k, talk) for k, talk in items if talk.get('level') == i.level]
        
        return render_template("talks/index", items)

def write(path, text):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    f = open(path, 'w')
    f.write(text)
    f.close()
