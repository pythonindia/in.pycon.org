import web
from web.form import Form, Textbox, Textarea, notnull
import datetime
import re

from infogami.utils import delegate
from infogami.utils.view import render, add_flash_message, public, context
from infogami.infobase.client import parse_datetime
from infogami import config

import tweet

@public
def render_template(name, *a, **kw):
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return render[name](*a, **kw)
    
def urlsafe(path):
    """Replaces space and special chars in the path with hyphen.

        >>> urlsafe('a b')
        'a-b'
        >>> urlsafe('a - b')
        'a-b'
        >>> urlsafe('a--b')
        'a-b'
        >>> urlsafe('a: b?x')
        'a-b-x'
    """
    # limit the length to avoid too long urls.
    path = path.lower()[:100] 
    return get_safepath_re().sub('-', path).strip('-')

@web.memoize
def get_safepath_re():
    """Make regular expression that matches all unsafe chars."""
    # unsafe chars according to RFC 2396
    reserved = ";/?:@&=+$,"
    delims = '<>#%"'
    unwise = "{}|\\^[]`"
    space = ' \n\r'
    
    spacelike = "-_"

    unsafe = reserved + delims + unwise + space + spacelike
    pattern = '[%s]+' % re.escape(unsafe)
    return re.compile(pattern)    

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
    post.url = "/%s-%s" % (post.key, urlsafe(post.title))
    return post
        
def get_post(id, process=True):
    key = "blog/%s" % id
    post = web.ctx.site.store[key]
    if process:
        post = process_post(post)
    else:
        post = web.storage(post)
    return post

@public
def get_all_posts():
    return [process_post(post) for post in web.ctx.site.store.values(type="post")]
    
def is_admin():
    """"Returns True if the current user is in admin usergroup."""
    return context.user and context.user.key in [m.key for m in web.ctx.site.get('/usergroup/admin').members]
    
def _get_post(id, title, process=True):
    try:
        post = get_post(id, process)
    except KeyError:
        raise web.notfound()
    
    title = (title or "")[1:] # strip -
    ptitle = urlsafe(post.title)
    if ptitle != title:
        raise web.redirect("/blog/%s-%s" % (id, ptitle))
    return post

class post(delegate.page):
    path = "/blog/(\d+)(-[^/]*)?"
    def GET(self, id, title):
        post = _get_post(id, title)
        return render_template("blog/post", post)

class edit(delegate.page):
    path = "/blog/(\d+)(-.*)?/edit"
    def GET(self, id, title):
        if not is_admin():
            return render_template("permission_denied", web.ctx.path, "Only admins can edit blog posts.")

        post = _get_post(id, title)
        f = form_new()
        f.fill(post)
        return render_template("blog/new", f)

    def POST(self, id, title):
        if not is_admin():
            return render_template("permission_denied", web.ctx.path, "Only admins can edit blog posts.")

        post = _get_post(id, title, process=False)
        i = web.input()

        post['title'] = i.title
        post['body'] = i.body
        web.ctx.site.store[post['key']] = post
        raise web.seeother("/blog/%s" % id)

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
        tweet.tweet("blog_template", title=d['title'], url=web.ctx.home + "/" + key)
        raise web.seeother('/' + key)
