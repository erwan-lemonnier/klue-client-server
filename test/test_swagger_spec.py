from datetime import date
import pprint
import yaml
import unittest
from klue.swagger.spec import ApiSpec


class Tests(unittest.TestCase):

    def test_apispec_constructor__scheme_http(self):
        yaml_str = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
"""
        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)
        self.assertEqual(spec.host, 'pnt-login.elasticbeanstalk.com')
        self.assertEqual(spec.port, 80)
        self.assertEqual(spec.protocol, 'http')
        self.assertEqual(spec.version, '0.0.1')


    def test_apispec_constructor__scheme_https(self):
        yaml_str = """
swagger: '2.0'
info:
  title: test
  version: '1.2.3'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - https
basePath: /v1
produces:
  - application/json
"""
        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)
        self.assertEqual(spec.host, 'pnt-login.elasticbeanstalk.com')
        self.assertEqual(spec.port, 443)
        self.assertEqual(spec.protocol, 'https')
        self.assertEqual(spec.version, '1.2.3')


    def test_apispec_constructor__https_is_default(self):
        yaml_str = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
basePath: /v1
produces:
  - application/json
"""
        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)
        self.assertEqual(spec.host, 'pnt-login.elasticbeanstalk.com')
        self.assertEqual(spec.port, 443)
        self.assertEqual(spec.protocol, 'https')
        self.assertEqual(spec.version, '0.0.1')


    def foo(self):
        pass


    def test_call_on_each_endpoint__missing_produces(self):
        yaml_str = """
swagger: '2.0'
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
paths:
  /v1/auth/login:
    post:
      parameters:
        - in: query
          name: whatever
          description: User login credentials.
          required: true
          type: string
      x-bind-server: pnt_login.handlers.do_login
"""
        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)

        with self.assertRaisesRegexp(Exception, "Swagger api has no 'produces' section"):
            spec.call_on_each_endpoint(self.foo)


    def test_call_on_each_endpoint__invalid_produces(self):
        yaml_str = """
swagger: '2.0'
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
paths:
  /v1/auth/login:
    post:
      parameters:
        - in: query
          name: whatever
          description: User login credentials.
          required: true
          type: string
      produces:
        - foo/bar
      x-bind-server: pnt_login.handlers.do_login
"""
        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)

        with self.assertRaisesRegexp(Exception, "Only 'application/json' is supported"):
            spec.call_on_each_endpoint(self.foo)


    def test_call_on_each_endpoint__too_many_produces(self):
        yaml_str = """
swagger: '2.0'
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
paths:
  /v1/auth/login:
    post:
      parameters:
        - in: query
          name: whatever
          description: User login credentials.
          required: true
          type: string
      produces:
        - foo/bar
        - bar/baz
      x-bind-server: pnt_login.handlers.do_login
"""
        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)

        with self.assertRaisesRegexp(Exception, "Expecting only one type"):
            spec.call_on_each_endpoint(self.foo)


    call_count = 0

    def test_call_on_each_endpoint(self):
        yaml_str = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
paths:
  /v1/auth/login:
    post:
      summary: blabla
      description: blabla
      parameters:
        - in: body
          name: whatever
          description: User login credentials.
          required: true
          schema:
            $ref: '#/definitions/Credentials'
      produces:
        - application/json
      x-bind-server: pnt_login.handlers.do_login
      x-bind-client: login
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/auth/logout/:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: query
          name: baboom
          description: foooo
          required: true
          type: string
      produces:
        - application/json
      x-bind-server: pnt_login.babar
      x-decorate-request: foo.bar.baz
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/version/:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      x-bind-server: do_version
      x-decorate-server: foo.bar.baz
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/hybrid/{foo}:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      parameters:
        - in: body
          name: whatever
          description: User login credentials.
          required: true
          schema:
            $ref: '#/definitions/Credentials'
        - in: path
          name: foo
          description: foooo
          required: true
          type: string
      x-bind-server: do_version
      x-decorate-server: foo.bar.baz
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/ignoreme/:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      x-no-bind-server: true
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

definitions:

  SessionToken:
    type: object
    description: An authenticated user''s session token
    properties:
      token:
        type: string
        description: Session token.

  Credentials:
    type: object
    description: A user''s login credentials.
    properties:
      email:
        type: string
        description: User''s email.
      password_hash:
        type: string
        description: MD5 of user''s password, truncated to 16 first hexadecimal characters.
"""

        Tests.call_count = 0

        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)

        def test_callback(data):
            print("Looking at %s %s" % (data.method, data.path))

            Tests.call_count = Tests.call_count + 1

            self.assertEqual(type(data.operation).__name__, 'Operation')

            if data.path == '/v1/auth/logout/':
                self.assertEqual(data.method, 'GET')
                self.assertEqual(data.handler_server, 'pnt_login.babar')
                self.assertIsNone(data.handler_client)
                self.assertIsNone(data.decorate_server)
                self.assertEqual(data.decorate_request, 'foo.bar.baz')
                self.assertFalse(data.param_in_body)
                self.assertTrue(data.param_in_query)
                self.assertFalse(data.no_params)

            elif data.path == '/v1/auth/login':
                self.assertEqual(data.method, 'POST')
                self.assertEqual(data.handler_server, 'pnt_login.handlers.do_login')
                self.assertEqual(data.handler_client, 'login')
                self.assertIsNone(data.decorate_server)
                self.assertIsNone(data.decorate_request)
                self.assertTrue(data.param_in_body)
                self.assertFalse(data.param_in_query)
                self.assertFalse(data.param_in_path)
                self.assertFalse(data.no_params)

            elif data.path == '/v1/version':
                self.assertEqual(data.method, 'GET')
                self.assertEqual(data.handler_server, 'do_version')
                self.assertIsNone(data.handler_client)
                self.assertIsNone(data.decorate_request)
                self.assertEqual(data.decorate_server, 'foo.bar.baz')
                self.assertFalse(data.param_in_body)
                self.assertFalse(data.param_in_query)
                self.assertFalse(data.param_in_path)
                self.assertTrue(data.no_params)

            elif data.path == '/v1/hybrib':
                self.assertEqual(data.method, 'GET')
                self.assertEqual(data.handler_server, 'do_version')
                self.assertIsNone(data.handler_client)
                self.assertIsNone(data.decorate_request)
                self.assertEqual(data.decorate_server, 'foo.bar.baz')
                self.assertTrue(data.param_in_body)
                self.assertFalse(data.param_in_query)
                self.assertTrue(data.param_in_path)
                self.assertTrue(data.no_params)

        spec.call_on_each_endpoint(test_callback)

        self.assertEqual(Tests.call_count, 4)


    yaml_complex_model = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
basePath: /v1
produces:
  - application/json

definitions:

  Foo:
    type: object
    description: Foo
    properties:
      token:
        type: string
        description: Session token.
      bar:
        $ref: '#/definitions/Bar'

  Bar:
    type: object
    description: Bar
    properties:
      a:
        type: string
        description: a
      b:
        type: string
        format: date-time
        description: b
"""


    # Test model_to_json on a deep structure, with object in object
    def test_model_to_json(self):
        swagger_dict = yaml.load(Tests.yaml_complex_model)
        spec = ApiSpec(swagger_dict)

        Foo = spec.definitions['Foo']
        Bar = spec.definitions['Bar']

        f = Foo(
            token='abcd',
            bar=Bar(
                a='1',
                b=date.today()
            )
        )

        print("foo: " + pprint.pformat(f))

        j = spec.model_to_json(f)
        self.assertDictEqual(j, {
            'token': 'abcd',
            'bar': {
                'a': '1',
                'b': date.today().isoformat()
            }
        })


    def test_json_to_model(self):
        swagger_dict = yaml.load(Tests.yaml_complex_model)
        spec = ApiSpec(swagger_dict)

        j = {
            'token': 'abcd',
            'bar': {
                'a': '1',
                'b': date.today().isoformat()
            }
        }

        m = spec.json_to_model('Foo', j)

        Foo = spec.definitions['Foo']
        Bar = spec.definitions['Bar']

        self.assertEqual(m.token, 'abcd')
        b = m.bar
        self.assertEqual(b.__class__.__name__, 'Bar')
        self.assertEqual(b.a, '1')
        self.assertEqual(str(b.b), str(date.today()) + " 00:00:00")
