import copy
import schemaish

from formish import util
from formish.dottedDict import dottedDict
from formish.converter import *
from formish.validation import *
from formish.widgets import *


class Action(object):
    """ Tracks an action that has been added to a form. """
    def __init__(self, callback, name, label):

        if not util.valid_identifier(name):
            raise FormError('Invalid action name %r.'%name)

        self.callback = callback
        self.name = name
        if label is None:
            self.label = util.titleFromName(name)
        else:
            self.label = label

            
def _cssname(self):
    """ Returns a hyphenated identifier using the form name and field name """
    return '%s-%s'%(self.form.name, '-'.join(self.name.split('.')))    


def _classes(self):
    """ Works out a list of classes that can be applied to the field """
    classes = [
        'field',
        self.attr.__class__.__name__.lower(),
        self.widget.widget.__class__.__name__.lower(),
        ]
    if self.required:
        classes.append('required')
    if self.widget.cssClass:
        classes.append(self.widget.cssClass)        
    if self.error:
        classes.append('error')
    return ' '.join(classes)
            

def _required(self):
    """ Does this field have a Not Empty validator of some sort """
    hasrequiredvalidator = _isNotEmpty(self, self.attr.validator)
    return hasrequiredvalidator


def _isNotEmpty(self,validator):
    """ parses through validators to work out if there is a not empty validator """
    if validator is None:
        return False
    if isinstance(validator, schemaish.NotEmpty) or getattr(validator,'not_empty'):
        return True
    if hasattr(validator,'validators'):
        for v in validator.validators:
            self._isNotEmpty(v)
    return False


class Field(object):
    """
    A wrapper for a schema field type that includes form information.
    
    The Schema Type Atribute does not have any bindings to the form library, it can be
    used on it's own. We bind the Schema Attribute to a Field in order to include form
    related information.
    
    The _widget attribute is a base widget to which the real widget is bound 
    """

    def __init__(self, name, attr, form):
        """
        @param name:            Fields dotted name
        @type name:             String
        @param attr:            a Schema attr to bind to the field
        @type attr:             Schema Attribute object
        @param form:            The form the field belongs to.
        @type form:             Form instance.
        """
        self.name = name
        self.attr = attr
        self.form = form

    @property
    def cssname(self):
        """ Works out a list of classes that can be applied to the field """
        return _cssname(self)
    
    @property
    def classes(self):
        """ Works out a list of classes that can be applied to the field """
        return _classes(self)
   
    @property 
    def required(self):
        """ Does this field have a Not Empty validator of some sort """
        return _required(self)
        
    @property
    def description(self):
        """ Description attribute """
        return self.attr.description        
        
    @property
    def data(self):
        """ Lazily get the data from the form.data when needed """
        return self.form.data[self.name]
    
    @property
    def _data(self):
        """ Lazily get the raw data from the form.data when needed """
        return self.form._data[self.name]
    
    @property
    def value(self):
        """Convert the requestData to a value object for the form or None."""
        return self.form._requestData.get(self.name, [None])
        
    @property
    def error(self):
        """ Lazily get the error from the form.errors when needed """
        return self.form.errors.get(self.name, None)
    
    @property
    def widget(self):
        """ return the fields widget bound with extra params. """
        try:
            w = self.form[self.name].widget
        except KeyError:
            w = Input()
        return BoundWidget(w, self)
        
    @property
    def title(self):
        try:
            t = self.form[self.name].title
        except KeyError:
            if self.attr.title is not None:
                return self.attr.title
            else:
                return util.title_from_name(self.name.split('.')[-1])
            
    

class Group(object):
    """
    A wrapper for a schema group type that includes form information.
    
    The Schema structure does not have any bindings to the form library, it can be
    used on it's own. We bind the schema Structure Attribute to a Group which includes form information.
    
    The _widget attribute is a base widget to which the real widget is bound 
    """    

    def __init__(self, name, attr, form):
        """
        @param name:            Group's dotted name
        @type name:             String
        @param attr:            a Schema attr to bind to the this group
        @type attr:             Schema Attribute object
        @param form:            The form the field belongs to.
        @type form:             Form instance.        
        """
        self.name = name
        self.attr = attr
        self.form = form
        self._fields = {}    
        # Create a default widget for the group. XXX Shouldn't this be some
        # sort of GroupWidget? It doesn't seem to be used anyway.
        self._widget = None
        # Construct a title
        self.title = self.attr.title
        if self.title is None and name is not None:
            self.title = util.title_from_name(self.name.split('.')[-1])

    @property
    def cssname(self):
        """ Works out a list of classes that can be applied to the field """        
        return _cssname(self)
    
    @property
    def classes(self):
        """ Works out a list of classes that can be applied to the field """        
        return _classes(self)           
            
    @property 
    def required(self):
        """ Does this field have a Not Empty validator of some sort """
        return _required(self)

    @property
    def description(self):
        return self.attr.description        
        
    @property
    def attrs(self):
        return self.attr.attrs
    
    @property
    def fields(self):
        """ 
        If we iterate through the fields, lazily bind the schema to the fields
        before returning.
        """
        for attr in self.attr.attrs:
            yield self.bind(attr[0], attr[1])        
    
    def __getattr__(self, name):
        """
        When we try to get a child field, lazily bind the child to the schema
        for that child.
        """
        return self.bind( name, self.attr.get(name) )

    def bind(self, attr_name, attr):
        """ 
        return cached bound schema as a field; Otherwise bind the attr to a
        Group or Field as appropriate and store on the _fields cache
        
        @param attr_name:     Form Field/Group identifier
        @type attr_name:      Python identifier string
        @param attr:          Attribute to bind
        @type attr:           Schema attribute
        """
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

    @property
    def error(self):
        """ Lazily get the error from the form.errors when needed """
        return self.form.errors.get(self.name, None)        
        
    @property
    def widget(self):
        """ return the fields widget bound with extra params. """
        return BoundWidget(self._widget, self)
    
    
class BoundWidget(object):
    
    def __init__(self, widget, field, cssClass=[]):
        self.widget = widget
        self.field = field
        self.cssClass=cssClass
        
    def pre_render(self, schemaType, data):
        return self.widget.pre_render(schemaType, data)

    def pre_parse_request(self, schemaType, data):
        if hasattr(self.widget,'pre_parse_request'):
            return self.widget.pre_parse_request(schemaType, data)
        else:
            return data
    
    def convert(self, schemaType, data):
        return self.widget.convert(schemaType, data)
        
    def validate(self, data):
        return self.widget.validate(data)


class Form(object):
    """
    The Form type is the container for all the information a form needs to
    render and validate data.
    """    

    element_name = None
    __requestData = None

    def __init__(self, structure, name=None, defaults=None, errors=None, action=''):
        """
        The form can be initiated with a set of data defaults (using defaults) or with some requestData. The requestData
        can be instantiated in order to set up a partially completed form with data that was persisted in some fashion.
        
        @param structure:       a Schema Structure attribute to bind to the the form
        @type structure:        Schema Structure Attribute object
        @param name:            Optional form name used to identify multiple forms on the same page.
        @type name:             String
        @param defaults:        Defaults to override the standard form widget defaults
        @type defaults:         Dictionary (dotted or nested)
        @param widgets:         Widgets to use for form fields
        @type widgets:          Dictionary (dotted or nested)
        @param errors:          Errors to store on the form for redisplay
        @type errors:           Dictionary of validation error objects
        """
        self.structure = Group(None, structure, self)
        self.item_data = {}
        self._name = name
        self.defaults = defaults or {}
        self.errors = dottedDict(errors or {})
        self.error = None
        self.actions = []
        self._action = action
        # Stuff on item_data

    @property
    def name(self):
        parts = [self.element_name, self._name]
        parts = [p for p in parts if p is not None]
        return '.'.join(parts)

    def addAction(self, callback, name="submit", label=None):
        """ 
        Add an action object to the form
        
        @param callback:       A function to call if this action is triggered
        @type callback:        Function or Method
        @param name:           The identifier for this action
        @type name:            Python identifier string
        @param label:          Use this label instead of the name for the value (label) of the action
        @type label:           String
        
        """
        if name in [action.name for action in self.actions]:
            raise ValueError('Action with name %r already exists.' % name)
        self.actions.append( Action(callback, name, label) )              

    def action(self, request):
        """ Find and call the action callback for the action used """
        if len(self.actions)==0:
            raise NoActionError('The form does not have any actions')
        for action in self.actions:
            if action.name in request.POST.keys():
                return action.callback(request, self)
        return self.actions[0].callback(request, self)
            

    def get_unvalidated_data(self, request_data, raiseErrors=True):
        """
        Convert the request object into a nested dict in the correct structure
        of the schema but without applying the schema's validation.
        """
        data = convertRequestDataToData(self.structure, request_data, errors=self.errors) 
        if raiseErrors and len(self.errors.keys()):
            raise FormError('Tried to access data but conversion from request failed with %s errors (%s)'%(len(self.errors.keys()), self.errors.data))
        return dottedDict(data)
    
    def validate(self, request):
        """ 
        Get the data without raising exception and then validate the data. If
        there are errors, raise them; otherwise return the data
        """
        # Check this request was POSTed by this form.
        if not request.method =='POST' and request.POST.get('__formish_form__',None) == self.name:
            raise Exception("request does not match form name")
        request_data = preParseRequestData(self.structure,dottedDict(request.POST))
        data = self.get_unvalidated_data(request_data, raiseErrors=False)
        errors = validate(self.structure, data, errors=self.errors)
        if len(self.errors.keys()) > 0:
            self.__requestData = request_data
            print '###############',request_data
            raise FormError('Tried to access data but conversion from request failed with %s errors (%s)'%(len(errors.keys()), errors.data))
        return dottedDict(data)

    ## 
    #  request_data
    #

    def _getRequestData(self):
        if self.__requestData is not None:
            return self.__requestData
        self.__requestData = convertDataToRequestData(self.structure, dottedDict(self.defaults))
        return self.__requestData
    
    def _setRequestData(self, requestData):
        """ 
        Assign raw request data 
        
        @param requestData:     raw request data (e.g. request.POST)
        @type requestData:      Dictionary (dotted or nested or dottedDict or MultiDict)
        """
        self.__requestData = dottedDict(requestData)

    _requestData = property(_getRequestData, _setRequestData)
    
    
    ##
    # defaults
    #
    
    def _getDefaults(self):
        """ Get the raw default data """
        return self._defaults
    
    def _setDefaults(self, data):
        """ assign data """
        self._defaults = data
        self.__requestData = None
        
    defaults = property(_getDefaults, _setDefaults)
    


    ##
    # The handler for item_data
    #
    
    def set_item_data(self, key, name, value):
        print 'setting key "%s" and name "%s" to value "%s"'%(key,name,value)
        self.item_data.setdefault(key, {})[name] = value

    def get_item_data(self, key, name):
        print 'getting key "%s" and name "%s"'%(key,name)
        return self.item_data.setdefault(key, {})[name]

    def get_item_data_values(self, name):
        d = dottedDict({})
        for k,v in self.item_data:
            if v.has_key(name):
                d[k] = v[name]
        return d
    
    def __getitem__(self, key):
        return FormAccessor(self, key)
    
    @property
    def fields(self):
        return self.structure.fields
    
    
class FormAccessor(object):

    def __init__(self, form, key, prefix=None):
        self.__dict__['form'] = form
        if prefix is not None:
            self.__dict__['key'] = '%s.%s'%(prefix,key)
        else:
            self.__dict__['key'] = key

    def __setattr__(self, name, value):
        self.form.set_item_data(self.key, name, value)

    def __getattr__(self, name):
        return self.form.get_item_data(self.key, name)
    
    def __getitem__(self, key):
        return FormAccessor(self.form, key, prefix=self.key)
        
NOVALUE = object()
def recursiveDottedGet(o, key):
    if key == '':
        if o == NOVALUE:
            raise KeyError
        else:
            return o
    ks = key.split('.')
    first = ks[0]
    remaining = '.'.join(ks[1:])
    return recursiveDottedGet( o.get(first, NOVALUE), remaining )

        
