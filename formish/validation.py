import re
from formish.dottedDict import dottedDict
from validatish.validate import Invalid
from convertish import convert

def convert_sequences(d):
    if not hasattr(d,'keys'):
        return d
    try:
        k = int(d.keys()[0])
    except ValueError:
        return dottedDict(d)
    intkeys = []
    for key in d.keys():
        intkeys.append(int(key))
    intkeys.sort()
    out = []
    for key in intkeys:
        out.append(d[str(key)])
    return out

def recursive_convert_sequences(d):
    if not hasattr(d,'keys'):
        return d
    if len(d.keys()) == 0:
        return d
    try:
        k = int(d.keys()[0])
    except ValueError:
        tmp = {}
        for k, v in d.items():
            tmp[k] = recursive_convert_sequences(v)
        return tmp
    intkeys = []
    for key in d.keys():
        intkeys.append(int(key))
    intkeys.sort()
    out = []
    for key in intkeys:
        out.append(recursive_convert_sequences(d[str(key)]))
    return out

def getNestedProperty(d,dottedkey):
    if dottedkey == '':
        return d
    keys = dottedkey.split('.')
    firstkey = keys[0]
    remaining_dottedkey = '.'.join(keys[1:])
    try:
        firstkey = int(firstkey)
    except:
        pass
    try:
        return getNestedProperty(d[firstkey],remaining_dottedkey)
    except (KeyError, IndexError):
        return None

def validate(structure, requestData, errors=None, keyprefix=None):
    """ Take a schemaish structure and use it's validators to return any errors"""
    if errors is None:
        errors = dottedDict()
    # Validate each field in the schema, return 
    # a dictionary of errors keyed by field name
    for attr in structure.attrs:
        # function is recursive so we have to build up a full key
        if keyprefix is None:
            newprefix = attr[0]
        else:
            newprefix = '%s.%s'%(keyprefix,attr[0])
        try:
            if hasattr(attr[1],'attrs'):
                validate(attr[1], requestData, errors=errors, keyprefix=newprefix)
            else: 
                if requestData.has_key(newprefix):
                    c = convert_sequences(requestData[newprefix])
                    attr[1].validate(c)
        except (Invalid, FieldValidationError), e:
            errors[newprefix] = e
    return errors

def convertDataToRequestData(formStructure, data, requestData=None, errors=None):
    """ Take a form structure and use it's widgets to convert data to request data """
    if requestData is None:
        requestData = dottedDict()
    if errors is None:
        errors = dottedDict()
    for field in formStructure.fields:
        try:
            if field.type is 'group' or (field.type is 'sequence' and (field.widget is None or field.widget.converttostring is False)):
                convertDataToRequestData(field, data, requestData=requestData, errors=errors)
            else:
                d = getNestedProperty(data, field.name)
                requestData[field.name] = field.widget.pre_render(field.attr,d)
        except Invalid, e:
            errors[field.name] = e
            raise
    return requestData
        
def convertRequestDataToData(formStructure, requestData, data=None, errors=None):
    """ Take a form structure and use it's widgets to convert data to request data """
    
    if data is None:
        data = {}
    if errors is None:
        errors = {}

    for field in formStructure.fields:
        try:
            if field.type is 'group' or (field.type == 'sequence' and (field.widget is None or field.widget.converttostring is False)):
                if field.type == 'sequence':
                    # Make sure we have an empty field at least. If we don't do this and there are no items in the list then this key wouldn't appear.
                    data[field.name] = []
                convertRequestDataToData(field, requestData, data=data, errors=errors)
            else: 
                # This needs to be cleverer... 
                data[field.name] = field.widget.convert(field.attr,requestData.get(field.name,[]))
        except convert.ConvertError, e:
            errors[field.name] = e
            
    data = recursive_convert_sequences(dottedDict(data))
    return data

def preParseRequestData(formStructure, requestData, data=None):
    if data is None:
        data = {}
    for field in formStructure.fields:
        if field.type is 'group' or (field.type == 'sequence' and field.widget is None):
            preParseRequestData(field, requestData, data=data)
        else: 
            # This needs to be cleverer...
            d = requestData.get(field.name,[])
            data[field.name] = field.widget.pre_parse_request(field.attr,d)
    return dottedDict(data)


class FormishError(Exception):
    """
    Base class for all Forms errors. A single string, message, is accepted and
    stored as an attribute.
    
    The message is not passed on to the Exception base class because it doesn't
    seem to be able to handle unicode at all.
    """
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


class FormError(FormishError):
    """
    Form validation error. Raise this, typically from a submit callback, to
    signal that the form (not an individual field) failed to validate.
    """
    pass
    
class NoActionError(FormishError):
    """
    Form validation error. Raise this, typically from a submit callback, to
    signal that the form (not an individual field) failed to validate.
    """
    pass
    
    
class FieldError(FormishError):
    """
    Base class for field-related exceptions. The failure message and the failing
    field name are stored as attributes.
    """
    def __init__(self, message, fieldName=None):
        FormishError.__init__(self, message)
        self.fieldName = fieldName


class FieldValidationError(FieldError):
    """
    Exception that signals that a field failed to validate.
    """
    pass
    
    
class FieldRequiredError(FieldValidationError):
    """
    Exception that signals that a field that is marked as required was not
    entered.
    """
    pass
