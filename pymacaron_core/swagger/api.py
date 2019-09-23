import yaml
import logging
from pymacaron_core.swagger.server import spawn_server_api
from pymacaron_core.swagger.client import generate_client_callers
from pymacaron_core.swagger.spec import ApiSpec
from pymacaron_core.models import generate_model_class


log = logging.getLogger(__name__)


class APIClient():
    """Object gathering the API's client side code.
    Offers client-side methods to call every server endpoint declared in the API.
    """
    pass


class APIModels():
    """Object mapping constructors of API models to their names"""
    pass


def default_error_callback(e):
    """The default callback for handling exceptions caught in the client and server stubs:
    just raise the exception."""
    raise e


def generate_model_instantiator(model_name, definitions):
    # We need this to localize the value of model_class
    def instantiate_model(*args, **kwargs):
        return definitions.get(model_name)(*args, **kwargs)
    return instantiate_model


class API():
    """Describes a REST client/server API, with sugar coating:
    - easily instantiating the objects defined in the API
    - auto-generation of client code

    usage: See apipool.py
    """

    def __init__(self, name, yaml_str=None, yaml_path=None, timeout=10, error_callback=None, formats=None, do_persist=True, host=None, port=None, local=False, proto=None, verify_ssl=True):
        """An API Specification"""

        self.name = name

        # Is the endpoint callable directly as a python method from within the server?
        # (true is the flask server also serves that api)
        self.local = local

        # Callback to handle exceptions
        self.error_callback = default_error_callback

        # Flag: true if this api has spawned_api
        self.is_server = False
        self.app = None

        # Object holding the client side code to call the API
        self.client = APIClient()

        # Object holding constructors for the API's objects
        self.model = APIModels()

        self.client_timeout = timeout

        if yaml_path:
            log.info("Loading swagger file at %s" % yaml_path)
            swagger_dict = yaml.load(open(yaml_path))
        elif yaml_str:
            swagger_dict = yaml.load(yaml_str)
        else:
            raise Exception("No swagger file specified")

        self.api_spec = ApiSpec(swagger_dict, formats, host, port, proto, verify_ssl)

        if error_callback:
            self.error_callback = error_callback

        # Auto-generate class methods for every object model defined
        # in the swagger spec, calling that model's constructor
        # Ex:
        #     my_api.Version(version='1.2.3')   => return a Version object
        for model_name in self.api_spec.definitions:

            spec = swagger_dict['definitions'][model_name]

            # Should this model inherit from a base class?
            parent_name = None
            if 'x-parent' in spec:
                parent_name = spec['x-parent']

            # Is this model persistent?
            persist = None
            if do_persist and 'x-persist' in spec:
                persist = spec['x-persist']

            # Associate model generator to ApiPool().<api_name>.model.<model_name>
            log.debug("Generating model class for %s" % model_name)
            model = generate_model_class(
                name=model_name,
                # bravado_class=generate_model_instantiator(model_name, self.api_spec.definitions),
                bravado_class=self.api_spec.definitions.get(model_name),
                swagger_dict=swagger_dict['definitions'][model_name],
                swagger_spec=self.api_spec.spec,
                parent_name=parent_name,
                persist=persist,
                properties=spec['properties'] if 'properties' in spec else {},
            )
            setattr(self.model, model_name, model)

        # Auto-generate client callers
        # so we can write
        # api.call.login(param)  => call /v1/login/ on server with param as json parameter
        self._generate_client_callers()


    def _generate_client_callers(self, app=None):
        # If app is defined, we are doing local calls
        if app:
            callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback, True, app)
        else:
            callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback, False, None)

        for method, caller in list(callers_dict.items()):
            setattr(self.client, method, caller)


    def spawn_api(self, app, decorator=None):
        """Auto-generate server endpoints implementing the API into this Flask app"""
        if decorator:
            assert type(decorator).__name__ == 'function'
        self.is_server = True
        self.app = app

        if self.local:
            # Re-generate client callers, this time as local and passing them the app
            self._generate_client_callers(app)

        return spawn_server_api(self.name, app, self.api_spec, self.error_callback, decorator)


    def get_version(self):
        """Return the version of the API (as defined in the swagger file)"""
        return self.api_spec.version


    def model_to_json(self, object):
        """Take a model instance and return it as a json struct"""
        return object.to_json()


    def json_to_model(self, model_name, j, validate=False):
        """Take a json strust and a model name, and return a model instance"""
        if validate:
            self.api_spec.validate(model_name, j)
        o = getattr(self.model, model_name)
        return o.from_json(j)
