import pprint
import yaml
import responses
from httplib import HTTPResponse
from mock import patch, MagicMock
from klue.swagger.spec import ApiSpec
from klue.swagger.client import generate_client_callers
from klue.exceptions import KlueException, ValidationError

def _slurp_yaml(yaml_str):
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    callers_dict = generate_client_callers(spec)

    assert len(callers_dict.keys()) == 1
    assert 'do_test' in callers_dict

    handler = callers_dict['do_test']
    assert type(handler).__name__ == 'function'

    return handler, spec


yaml_query_param = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: some.server.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
paths:
  /v1/some/path:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: query
          name: arg1
          description: foooo
          required: true
          type: string
        - in: query
          name: arg2
          description: foooo
          required: true
          type: string
      produces:
        - application/json
      x-bind-server: whatever
      x-bind-client: do_test
      x-auth-required: false
      responses:
        '200':
          description: result
          schema:
            $ref: '#/definitions/Result'

definitions:

  Result:
    type: object
    description: result
    properties:
      foo:
        type: string
        description: blabla
      bar:
        type: string
        description: bloblo
"""

@responses.activate
def test_client_with_query_param():
    handler, _ = _slurp_yaml(yaml_query_param)

    responses.add(responses.GET, "http://some.server.com:80//v1/some/path",
                  body='{"foo": "a", "bar": "b"}', status=200,
                  content_type="application/json")

    res = handler(arg1='this', arg2='that').call()

    print("response: " + pprint.pformat(res))
    assert type(res).__name__ == 'Result'
    assert res.foo == 'a'
    assert res.bar == 'b'


@patch('klue.swagger.client.grequests')
def test_requests_parameters_with_query_param(grequests):
    handler, _ = _slurp_yaml(yaml_query_param)

    grequests.get = MagicMock()
    try:
        handler(arg1='this', arg2='that').call()
    except Exception as e:
        pass

    grequests.get.assert_called_once_with('http://some.server.com:80//v1/some/path',
                                          data=None, headers={}, params={'arg1': 'this', 'arg2': 'that'}, timeout=10)


yaml_body_param = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: some.server.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
paths:
  /v1/some/path:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: body
          name: arg1
          description: foooo
          required: true
          schema:
            $ref: '#/definitions/Param'
      produces:
        - application/json
      x-bind-server: whatever
      x-bind-client: do_test
      x-auth-required: false
      responses:
        '200':
          description: result
          schema:
            $ref: '#/definitions/Result'

definitions:

  Result:
    type: object
    description: result
    properties:
      foo:
        type: string
        description: blabla
      bar:
        type: string
        description: bloblo

  Param:
    type: object
    description: param
    properties:
      arg1:
        type: string
        description: blabla
      arg2:
        type: string
        description: bloblo

"""

@responses.activate
def test_client_with_body_param():
    handler, spec = _slurp_yaml(yaml_body_param)

    responses.add(responses.GET, "http://some.server.com:80//v1/some/path",
                  body='{"foo": "a", "bar": "b"}', status=200,
                  content_type="application/json")

    # Only 1 parameter expected
    try:
        res = handler()
    except ValidationError as e:
        assert 1
    else:
        assert 0
    try:
        res = handler(1, 2)
    except ValidationError as e:
        assert 1
    else:
        assert 0

    # Send a valid parameter object
    model_class = spec.definitions['Param']
    param = model_class(arg1='a', arg2='b')

    res = handler(param).call()
    assert type(res).__name__ == 'Result'
    assert res.foo == 'a'
    assert res.bar == 'b'


@patch('klue.swagger.client.grequests')
def test_requests_parameters_with_query_param(grequests):
    handler, spec = _slurp_yaml(yaml_body_param)
    model_class = spec.definitions['Param']
    param = model_class(arg1='a', arg2='b')

    grequests.get = MagicMock()
    try:
        handler(param).call()
    except Exception as e:
        pass

    grequests.get.assert_called_once_with('http://some.server.com:80//v1/some/path',
                                          data=None, headers={},
                                          params={'arg1': 'a', 'arg2': 'b'}, timeout=10)


def test_client_with_auth_required():
    pass