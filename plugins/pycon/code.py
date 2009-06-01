from infogami.utils import delegate
from infogami.utils.template import render

class earlybird_registration(delegate.page):
    def POST(self):
        return render.earlybird()

