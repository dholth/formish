import logging
from restish import http, resource, templating
import formish, schemaish, validatish
from formish.util import title_from_name
from pprint import pformat

from testish.lib import forms as form_defs
from testish.lib import extract_function

log = logging.getLogger(__name__)



class Root(resource.Resource):

    @resource.GET()
    @templating.page('root.html')
    def root(self, request):
        return {}
    
    def resource_child(self, request, segments):
        if segments[0] == 'filehandler':
            return FileResource(), segments[1:]
        return FormResource(segments[0]), segments[1:]


class FormResource(resource.Resource):

    def __init__(self, id):
        self.id = id
        self.title = formish.util.title_from_name(id)
        self.form_getter = getattr(form_defs,id)
        self.description = self.form_getter.func_doc
    
    @resource.GET()
    def GET(self, request):
        return self.render_form(request)

    @templating.page('form.html')
    def render_form(self, request, form=None, data=None):
        if form is None:
            form = self.form_getter()
        return {'title': self.title, 'description': self.description,
                'form': form, 'data': pformat(data),
                'definition': extract_function.extract(self.id),
                'tests': extract_function.extract('test_%s'%self.id)}
    
    @resource.POST()
    def POST(self, request):
        form = self.form_getter()
        try:
            data = form.validate(request)
        except formish.FormError, e:
            return self.render_form(request, form=form)
        else:
            return self.render_form(request, form=None, data=data)
