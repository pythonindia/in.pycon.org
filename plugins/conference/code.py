from infogami.utils import delegate
from infogami.utils.view import render, add_flash_message
from infogami import config
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
        i = web.input()
        
        if config.get('from_address') and config.get('talk_submission_contact'):
            email = render_template("talks/email", i)
            web.sendmail(
                from_address=config.from_address, 
                to_address=config.talk_submission_contact,
                subject=web.safestr(email.subject.strip()),
                message=web.safestr(email)
            )
        return render_template("talks/submitted")
