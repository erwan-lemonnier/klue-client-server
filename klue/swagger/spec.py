import pprint
import logging
from klue.exceptions import ValidationError
from bravado_core.spec import Spec
from bravado_core.operation import Operation
from bravado_core.marshal import marshal_model


log = logging.getLogger(__name__)


class EndpointData():
    """Just holding some info about an api endpoint"""
    path = None
    method = None
    handler_server = None
    handler_client = None
    has_auth = True
    operation = None

    param_in_body = False
    param_in_query = False
    no_params = False

    def __init__(self, path, method):
        self.path = path
        self.method = method.upper()

class ApiSpec():
    """Object holding the swagger spec as a YAML dict and a bravado-core Spec object,
    as well as methods for exploring the spec.
    """
    swagger_dict = None
    spec = None
    definitions = None

    host = None
    port = None
    protocol = None
    version = None


    def __init__(self, swagger_dict):
        self.swagger_dict = swagger_dict
        self.spec = Spec.from_dict(self.swagger_dict,
                                   config={
                                       'validate_responses': True,
                                       'validate_requests': True,
                                       'validate_swagger_spec': False,
                                       'use_models': True,
                                   })
        self.definitions = self.spec.definitions

        self.host = swagger_dict.get('host', None)
        if not self.host:
            raise Exception("Swagger file has no 'host' entry")

        schemes = swagger_dict.get('schemes', None)
        if 'https' in schemes:
            self.port = 443
            self.protocol = 'https'
        elif 'http' in schemes:
            self.port = 80
            self.protocol = 'http'
        else:
            raise Exception("Swagger schemes contain neither http nor https: %s" % pprint.pformat(schemes))

        self.version = swagger_dict.get('info', {}).get('version', '')


    def model_to_json(self, object):
        """Take a model instance and return it as a json struct"""
        model_name = type(object).__name__
        if model_name not in self.swagger_dict['definitions']:
            raise ValidationError("Swagger spec has no definition for model %s" % model_name)
        model_def = self.swagger_dict['definitions'][model_name]
        return marshal_model(self.spec, model_def, object)


    def call_on_each_endpoint(self, callback):
        """Find all server endpoints defined in the swagger spec and calls 'callback' for each,
        with an instance of EndpointData as argument.
        """
        for path, d in self.swagger_dict['paths'].items():
            for method, op_spec in d.items():
                data = EndpointData(path, method)

                # Make sure that endpoint only produces 'application/json'
                if 'produces' not in op_spec:
                    raise Exception("Swagger api has no 'produces' section for %s %s" % (method, path))
                if len(op_spec['produces']) != 1:
                    raise Exception("Expecting only one type under 'produces' for %s %s" % (method, path))
                if 'application/json' not in op_spec['produces']:
                    raise Exception("Only 'application/json' is supported. See %s %s" % (method, path))

                # Which server method handles this endpoint?
                if 'x-bind-server' not in op_spec:
                    if 'x-no-bind-server' in op_spec:
                        # That route should not be auto-generated
                        log.info("Skipping generation of %s %s" % (method, path))
                        continue
                    else:
                        raise Exception("Swagger api defines no x-bind-server for %s %s" % (method, path))
                data.handler_server = op_spec['x-bind-server']

                # Which client method handles this endpoint?
                if 'x-bind-client' in op_spec:
                    data.handler_client = op_spec['x-bind-client']

                # Does this method require authentication?
                has_auth = True
                if 'x-auth-required' in op_spec:
                    has_auth = op_spec['x-auth-required']
                    if type(has_auth).__name__ != 'bool':
                        raise Exception("Swagger api contains x-auth-required without boolean value at %s %s" % (method, path))
                data.has_auth = has_auth

                # Generate a bravado-core operation object
                data.operation = Operation.from_spec(self.spec, path, method, op_spec)

                # Figure out how parameters are passed: one json in body? one or
                # more values in query?
                if 'parameters' in op_spec:
                    params = op_spec['parameters']
                    if len(params) == 1 and params[0]['in'] == 'body':
                        data.param_in_body = True
                    elif params[0]['in'] == 'query':
                        data.param_in_query = True
                    elif params[0]['in'] == 'path':
                        raise Exception("'path' parameters are not supported (%s %s)" % (method, path))
                    else:
                        raise Exception("%s %s uses an unsupported parameter model" % (method, path))
                else:
                    data.no_params = True

                callback(data)