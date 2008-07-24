from webhelpers.html import literal
from restish.templating import render
import schemaish


# Singleton used to represent no argument passed, for when None is a valid
# value for the arg.
NOARG = object()


def validate(structure, data, context=None, errors=None):
    if errors is None:
        errors = {}
    if context == 'POST':
        data = getDictFromDottedDict(data)
    # Use formencode to validate each field in the schema, return 
    # a dictionary of errors keyed by field name
    for attr in structure.attrs:
        try:
            if hasattr(attr[1],'attrs'):
                d, e = validate(attr[1], data[attr[0]], errors=errors.get(attr[0],{}))
                if len(e.keys()) != 0:
                    errors[attr[0]] = e
            else: 
                attr[1].validate(data.get(attr[0]))
        except schemaish.Invalid, e:
            errors[attr[0]] = e
    return data, errors


def setDict(out, keys, value):
    if len(keys) == 1:
        if out.has_key(keys[0]):
            raise KeyError('Clash in keys when converting from dotted to nested')
        out[keys[0]] = value
    else:
        if not out.has_key(keys[0]):
            out[keys[0]] = {}
        return setDict(out[keys[0]], keys[1:], value)


def getDictFromDottedDict(data):
    out = {}
    keyslist=[key.split('.') for key in data.keys()]
    keyslist.sort(reverse=True)
    for keys in keyslist:
        setDict(out, keys, data['.'.join(keys)])
    return out    


def getDataUsingDottedKey(data, dottedkey, default=NOARG):
    keys = dottedkey.split('.')
    d = data
    try:
        for key in keys:
            d = d[key]
    except KeyError, e:
        if default is not NOARG:
            return default
        raise KeyError('Dotted key does not exist')
    return d
        

class Field(object):
    """
    A wrapper for a schema field type that includes form information. 
    
    The Schema field does not have any bindings to the form libaray, it can be used on it's own. The Bound field.
    
    The _widget attribute is a base widget to which the real widget is bound 
    
    """

    def __init__(self, name, attr, form):
        """
        @param name:            Fields dotted name
        @type name:             String
        @param attr_name:       a name for the field
        @type attr_name:        String
        @param attr:            a Schema attr to bind to the container
        @type attr:             Attribute object
        """
        self.name = name
        self.attr = attr
        self._widget = Widget()
        self.form = form

    @property
    def title(self):
        return self.attr.title

    @property
    def description(self):
        return self.attr.description        
        
    def __call__(self):
        """Default template renderer for the field (not the widget itself) """
        return literal(render(self.form.request, "formish/field.html", {'field': self}))
    
    @property
    def value(self):
        """ Lazily get the value from the form.data when needed """
        return getDataUsingDottedKey(self.form.data, self.name, None)
        
    @property
    def error(self):
        """ Lazily get the error from the form.errors when needed """
        return getDataUsingDottedKey(self.form.errors, self.name, None)
    
    def _getWidget(self):
        return BoundWidget(self._widget, self)
    
    def _setWidget(self, widget):
        self._widget = widget
        
    widget = property(_getWidget, _setWidget)
    

class Group(object):

    def __init__(self, name, attr, form):
        """
        @param name:            Fields dotted name
        @type name:             String
        @param attr_name:       a name for the field
        @type attr_name:        String
        @param attr:            a Schema attr to bind to the container
        @type attr:             Attribute object
        """
        self.name = name
        self.attr = attr
        self._widget = Widget()
        self.form = form
        self._fields = {}    

    @property
    def title(self):
        return self.attr.title

    @property
    def description(self):
        return self.attr.description        
        
    @property
    def attrs(self):
        return self.attr.attrs
    
    @property
    def fields(self):
        for attr in self.attr.attrs:
            yield self.bind(attr[0], attr[1])        
    
    def __getattr__(self, name):
        if name == "value":
            print "***", self.attr
        return self.bind( name, self.attr.get(name) )

    def bind(self, attr_name, attr):
        try:
            return self._fields[attr_name]
        except KeyError:
            if self.name is None:
                keyprefix = attr_name
            else:
                keyprefix = '%s.%s'%(self.name,attr_name)
            if isinstance( attr, schemaish.Structure ):
                bf = Group(keyprefix, attr, self.form)
            else:
                bf = Field(keyprefix, attr, self.form)
            self._fields[attr_name] = bf
            return bf
        
    def __call__(self):
        return literal(render(self.form.request, "formish/structure.html", {'field': self, 'fields': self.fields}))

        
class BoundWidget(object):
    
    def __init__(self, widget, field):
        self.widget = widget
        self.field = field
        
    def __call__(self):
        return self.widget(self.field)


class Widget(object):

    def __call__(self, field):
        return literal(render(field.form.request, "formish/widgets/default.html", {'widget': self, 'field': field}))
    
    
class Form(object):

    def __init__(self, name, structure, request, data=None, widgets=None, errors=None):
        self.name = name
        self.structure = Group(None, structure, self)
        self.request = request
        self.data = data or {}
        self.errors = errors or {}
        self.set_widgets(self.structure, widgets)
        
    def set_widgets(self, structure, widgets):
        if not widgets: 
            return
        for name, widget in widgets.iteritems():
            form_item = getattr(structure, name)
            if isinstance(widget, dict):
                # We have a dict of widgets presumably desitined for form_item that *should* be a bound structure.
                self.set_widgets( form_item, widget )
            else:
                # Set the widget on this form item
                form_item.widget = widget

    def __call__(self):
        return literal(render(self.request, "formish/form.html", {'form': self}))

    def __getattr__(self, name):
        return getattr( self.structure, name )

    @property
    def values(self):
        return {}
    
    @property
    def fields(self):
        return self.structure.fields
            
    def validateRequest(self):
        data, errors = validate(self.structure, self.request.POST, context='POST')
        self.data = data
        self.errors = errors
        return len(errors.keys()) == 0
            

class TextArea(Widget):
    
    def __init__(self, cols=None, rows=None):
        if cols is not None:
            self.cols = cols
        if rows is not None:
            self.rows = rows 
            
    def __call__(self, form, field):
        return literal(render(form.request, "formish/widgets/textarea.html", {'widget': self, 'field': field}))
