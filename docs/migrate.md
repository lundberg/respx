# Migrate from requests

## responses

Here's a few examples on how to migrate your code *from* the `responses` library *to* `respx`.

### Patching the Client

#### Decorator

``` python
@responses.activate
def test_foo():
    ...
```
``` python
@respx.mock
def test_foo():
    ...
```
> See [Router Settings](guide.md#router-settings) for more details.

#### Context Manager

``` python
def test_foo():
    with responses.RequestsMock() as rsps:
        ...
```
``` python
def test_foo():
    with respx.mock() as respx_mock:
        ...
```
> See [Router Settings](guide.md#router-settings) for more details.

#### unittest setUp

``` python
def setUp(self):
    self.responses = responses.RequestsMock()
    self.responses.start()
    self.addCleanup(self.responses.stop)
```
``` python
def setUp(self):
    self.respx_mock = respx.mock()
    self.respx_mock.start()
    self.addCleanup(self.respx_mock.stop)
```
> See [unittest examples](examples.md#reuse-setup-teardown) for more details.

### Mock a Response

``` python
responses.add(
    responses.GET, "https://example.org/",
    json={"foo": "bar"},
    status=200,
)
```
``` python
respx.get("https://example.org/").respond(200, json={"foo": "bar"})
```
> See [Routing Requests](guide.md#routing-requests) and [Mocking Responses](guide.md#mocking-responses) for more details.

### Mock an Exception

``` python
responses.add(
    responses.GET, "https://example.org/",
    body=Exception("..."),
)
```
``` python
respx.get("https://example.org/").mock(side_effect=ConnectError)
```
> See [Exception Side Effect](guide.md#exceptions) for more details.

### Subsequent Responses

``` python
responses.add(responses.GET, "https://example.org/", status=200)
responses.add(responses.GET, "https://example.org/", status=500)
```
``` python
respx.get("https://example.org/").mock(
    side_effect=[Response(200), Response(500)]
)
```
> See [Iterable Side Effect](guide.md#iterable) for more details.

### Callbacks

``` python
def my_callback(request):
    headers = {"Content-Type": "application/json"}
    body = {"foo": "bar"}
    return (200, headers, json.dumps(resp_body))

responses.add_callback(
    responses.GET, "http://example.org/",
    callback=my_callback,
)
```
``` python
def my_side_effect(request, route):
    return Response(200, json={"foo": "bar"})

respx.get("https://example.org/").mock(side_effect=my_side_effect)
```
> See [Mock with a Side Effect](guide.md#mock-with-a-side-effect) for more details.

### History and Assertions

### History

``` python
responses.calls[0].request
responses.calls[0].response
```
``` python
respx.calls[0].request
respx.calls[0].response

request, response = respx.calls[0]
respx.calls.last.response
```
> See [Call History](guide.md#call-history) for more details.

#### Call Count
``` python
responses.assert_call_count("http://example.org/", 1)
```
``` python
route = respx.get("https://example.org/")
assert route.call_count == 1
```
> See [Call History](guide.md#call-history) for more details.

#### All Called
``` python
with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
    ...
```
``` python
with respx.mock(assert_all_called=False) as respx_mock:
    ...
```
> See [Assert all Called](guide.md#assert-all-called) for more details.

### Modify Mocked Response

``` python
responses.add(responses.GET, "http://example.org/", json={"data": 1})
responses.replace(responses.GET, "http://example.org/", json={"data": 2})
```
``` python
respx.get("https://example.org/").respond(json={"data": 1})
respx.get("https://example.org/").respond(json={"data": 2})
```


### Pass Through Requests

``` python
responses.add_passthru("https://example.org/")
```
``` python
respx.route(url="https://example.org/").pass_through()
```
> See [Pass Through](guide.md#pass-through) for more details.


## requests-mock

*todo ... contribution welcome* ;-)
