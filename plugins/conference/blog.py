from infogami.utils import delegate
from infogami.utils.view import render, add_flash_message, public, context
from infogami.infobase.client import parse_datetime
from infogami import config

import web
from web.form import Form, Textbox, Textarea, notnull
import datetime

@public
def render_template(name, *a, **kw):
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return render[name](*a, **kw)

class index(delegate.page):
    path = "/blog"

    def GET(self):
        posts = get_all_posts()
        title = config.get("blog_title", "Blog")        
        return render_template("blog/index", title, posts)

class feed(delegate.page):
    path = "/blog/feed.rss"
    def GET(self):
        posts = get_all_posts()
        
        # convert timestamp into the format expected by RSS
        from infogami.core.code import feed as _feed
        for p in posts:
            p.timestamp = _feed()._format_date(p.timestamp)
              
        title = config.get("blog_title", "Blog")
        web.header('Content-Type', 'application/rss+xml')
        rss = render_template("blog/feed", web.ctx.home, title, posts)
        return delegate.RawText(rss)
    
def process_post(post):
    post = web.storage(post)
    post.timestamp = parse_datetime(post.timestamp)
    post.author = post.author and web.ctx.site.get(post.author)
    post.url = "/%s-%s" % (post.key, post.title.replace(" ", "-"))
    return post
        
def get_post(id):
    key = "blog/%s" % id
    post = web.ctx.site.store[key]
    return process_post(post)

@public
def get_all_posts():
    return [process_post(post) for post in web.ctx.site.store.values(type="post")]
    
def is_admin():
    """"Returns True if the current user is in admin usergroup."""
    return context.user and context.user.key in [m.key for m in web.ctx.site.get('/usergroup/admin').members]

class post(delegate.page):
    path = "/blog/(\d+)(-.*)?"
    def GET(self, id, title):
        try:
            post = get_post(id)
        except KeyError:
            raise web.notfound()
        
        title = title or ""
        title = web.lstrips(title, "-")
        if post.title != title.replace("-", " "):
            raise web.redirect("/blog/%s-%s" % (id, post.title.replace(" ", "-")))
        return render_template("blog/post", post)

form_new = Form(
    Textbox("title", notnull),
    Textarea("body", notnull),
)

class new(delegate.page):
    path = "/blog/new"
    def GET(self):
        if not is_admin():
            return render_template("permission_denied", "/blog/new", "Only admin users can create new blog posts.")
        return render_template("blog/new", form_new())
        
    def POST(self):
        if not is_admin():
            return render_template("permission_denied", "/blog/new", "Only admin users can create new blog posts.")

        i = web.input()
        
        f = form_new()
        if not f.validates(i):
            return render_template("blog/new", form=f)
        
        key = "blog/%d" % web.ctx.site.seq.next_value("post")
        d = {
            "key": key,
            "type": "post",
            "title": i.title,
            "body": i.body,
            "author": context.user and context.user.key,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        web.ctx.site.store[d['key']] = d
        raise web.seeother('/' + key)
