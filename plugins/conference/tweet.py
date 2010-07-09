"""tweet helper. 

Uses [python-twitter](http://code.google.com/p/python-twitter/).
"""
import sys

try:
    import twitter
except ImportError:
    print >> sys.stderr, "Unlable to import twitter module"
    print "Unlable to import twitter module"
    twitter = None
    raise

import web    
from infogami import config

def tweet(template_name, **kw):
    """Tweet a message using the template from the configuration with the given template_name. 
    
    The template is parsed using web.py templetor. Here is a sample template:
        '#inpycon2010 New talk: "$title[:40]" by $author[:20] $url'
    """
    try:
        t = config.get("twitter", {})
        if twitter and t.get('username') and t.get('password') and template_name in t:
            api = twitter.Api(t['username'], t['password'])
        
            message = compile_template(t[template_name])(**kw)
            api.PostUpdate(message[:140])
    except:
        print >> web.debug, "Failed to post to template", template_name, kw
        import traceback
        traceback.print_exc()

@web.memoize
def compile_template(text):
    try:
        # web.py 0.34+
        p = web.template.Parser()
    except:
        # web.py < 0.34
        p = web.template.Parser("")

    code = p.readline(text)[0].emit("")
    code = code.replace("yield '',", "").strip()
    print code
    def f(**kw):
        def extend_(items):
            return "".join(items)
        def escape_(s, _):
            return s
        def join_(*a): 
            return "".join(a)
        kw.update(locals())
        return web.safestr(eval(code, kw))
    return f
    
def test_all():
    t = compile_template("Hello $name")
    assert t(name='a') == 'Hello a'
    assert t(name='b') == 'Hello b'
    
def test_tweet(monkeypatch):
    x = web.storage()
    def PostUpdate(self, message):
        x.message = message
        
    monkeypatch.setattr(twitter.Api, "PostUpdate", PostUpdate)
    t = {"username": "foo", "password": "bar", "talk_template": "New talk: $title[:10]"}
    monkeypatch.setattr(config, "twitter", t, raising=False)

    tweet('talk_template', title='foo')
    assert x.message == 'New talk: foo'
    
    t['talk_template'] = 'New talk: $title'
    tweet('talk_template', title='a' * 1000)
    assert len(x.message) == 140
