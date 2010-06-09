from infogami.utils import delegate
from infogami.utils.view import render, add_flash_message
import web

def render_template(name, *a, **kw):
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return render[name](*a, **kw)

class submit_talk(delegate.page):
    path = "/talks/submit"
    
    def GET(self):
        return render_template("talks/submit")
        
    def POST(self):
        add_flash_message("error", "Talk submission is not yet implemented!")
        i = web.input()
        return render_template("talks/submit", i)
