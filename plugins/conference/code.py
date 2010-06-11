from infogami.utils import delegate
from infogami.utils.view import render, add_flash_message
from infogami import config
import web
from web.form import Form, Textbox, Textarea, notnull, regexp

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
    Textarea("summary", notnull),
    Textarea("outline"),    
    Textarea("notes"),    
)

class submit_talk(delegate.page):
    path = "/talks/submit"
    
    def GET(self):
        f = form_talk()
        return render_template("talks/submit", f)
        
    def POST(self):
        i = web.input()
        f = form_talk()
        
        if not f.validates(i):
            return render_template("talks/submit", f)
        
        if config.get('from_address') and config.get('talk_submission_contact'):
            email = render_template("talks/email", i)
            web.sendmail(
                from_address=config.from_address, 
                to_address=config.talk_submission_contact,
                subject=web.safestr(email.subject.strip()),
                message=web.safestr(email)
            )
        return render_template("talks/submitted")
