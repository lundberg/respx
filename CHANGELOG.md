# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.20.1] - 2022-11-18

### Fixed

- Support HTTPX 0.23.1, thanks @g-as for input (#223)

## Added

- Officially support Python 3.11 (#223)
- Run pre-commit hooks in CI workflow (#219)

### Changed

- Bump autoflake, thanks @antonagestam (#220)

### Removed

- Drop support for Python 3.6 (#218)

## [0.20.0] - 2022-09-16

### Changed

- Type `Router.__getitem__` to not return optional routes, thanks @flaeppe (#216)
- Change `Call.response` to raise instead of returning optional response (#217)
- Change `CallList.last` to raise instead of return optional call (#217)
- Type `M()` to not return optional pattern, by introducing a `Noop` pattern (#217)
- Type `Route.pattern` to not be optional (#217)

### Fixed

- Correct type hints for side effects (#217)

### Added

- Runs `mypy` on both tests and respx (#217)
- Added nox test session for python 3.11 (#217)
- Added `Call.has_response` helper, now that `.response` raises (#217)

## [0.19.3] - 2022-09-14

### Fixed

- Fix typing for Route modulos arg
- Respect patterns with empty value when using equal lookup (#206)
- Use pytest asyncio auto mode (#212)
- Fix mock decorator to work together with pytest fixtures (#213)
- Wrap pytest function correctly, i.e. don't hide real function name (#213)

### Changed

- Enable mypy strict_optional (#201)

## [0.19.2] - 2022-02-03

### Fixed

- Better cleanup before building egg, thanks @nebularazer (#198)

## [0.19.1] - 2022-01-10

### Fixed

- Allow first path segments containing colons, thanks @hannseman. (#192)
- Fix license classifier, thanks @shadchin (#195)
- Fix typos, thanks @kianmeng (#194)

## [0.19.0] - 2021-11-15

### Fixed

- Support HTTPX 0.21.0. (#189)
- Use Session.notify when chaining nox sessions, thanks @flaeppe. (#188)
- Add overloads to `MockRouter.__call__`, thanks @flaeppe. (#187)
- Enhance AND pattern evaluation to fail fast. (#185)
- Fix CallList assertion error message. (#178)

### Changed

- Prevent method and url as lookups in HTTP method helpers, thanks @flaeppe. (#183)
- Fail pattern match when JSON path not found. (#184)

## [0.18.2] - 2021-10-22

### Fixed

- Include extensions when instantiating request in HTTPCoreMocker. (#176)

## [0.18.1] - 2021-10-20

### Fixed

- Respect ordered param values. (#172)

### Changed

- Raise custom error types for assertion checks. (#174)

## [0.18.0] - 2021-10-14

### Fixed

- Downgrade `HTTPX` requirement to 0.20.0. (#170)

### Added

- Add support for matching param with _ANY_ value. (#167)

## [0.18.0b0] - 2021-09-15

### Changed

- Deprecate RESPX MockTransport in favour of HTTPX MockTransport. (#152)

### Fixed

- Support `HTTPX` 1.0.0b0. (#164)
- Allow tuples as params to align with httpx, thanks @shelbylsmith. (#151)
- Fix xfail marked tests. (#153)
- Only publish docs for upstream repo, thanks @hugovk. (#161)

### Added

- Add optional route arg to side effects. (#158)

## [0.17.1] - 2021-06-05

### Added

- Implement support for async side effects in router. (#147)
- Support mocking responses using asgi/wsgi apps. (#146)
- Added pytest fixture and configuration marker. (#150)

### Fixed

- Typo in import from examples.md, thanks @shelbylsmith. (#148)
- Fix pass-through test case. (#149)

## [0.17.0] - 2021-04-27

### Changed

- Require `HTTPX` 0.18.0 and implement the new transport API. (PR #142)
- Removed ASGI and WSGI transports from httpcore patch list. (PR #131)
- Don't pre-read mocked async response streams. (PR #136)

### Fixed

- Fixed syntax highlighting in docs, thanks @florimondmanca. (PR #134)
- Type check `route.return_value`, thanks @tzing. (PR #133)
- Fixed a typo in the docs, thanks @lewoudar. (PR #139)

### Added

- Added support for adding/removing patch targets. (PR #131)
- Added test session for python 3.10. (PR #140)
- Added RESPX Mock Swallowtail to README. (PR #128)

## [0.16.3] - 2020-12-14

### Fixed

- Fixed decorator `respx_mock` kwarg, mistreated as a `pytest` fixture. (PR #117)
- Fixed `JSON` pattern sometimes causing a `JSONDecodeError`. (PR #124)

### Added

- Snapshot and rollback of routes' pattern and name. (PR #120)
- Internally extracted a `RouteList` from `Router`. (PR #120)
- Auto registration of `Mocker` implementations and their `using` name. (PR #121)
- Added `HTTPXMocker`, optionally patching `HTTPX`. (PR #122)

### Changed

- Protected a routes' pattern to be modified. (PR #120)

## [0.16.2] - 2020-11-26

### Added

- Easier support for using HTTPX MockTransport. (PR #118)
- Support mixed case for `method__in` and `scheme__in` pattern lookups. (PR #113)

### Fixed

- Handle missing path in URL pattern (PR #113)

### Changed

- Refactored internal mocking vs `MockTransport`. (PR #112)

### Removed

- Dropped raw request support when parsing patterns (PR #113)

## [0.16.1] - 2020-11-16

### Added

- Extended `url` pattern with support for `HTTPX` proxy url format. (PR #110)
- Extended `host` pattern with support for regex lookup. (PR #110)
- Added `respx.request(...)`. (PR #111)

### Changed

- Deprecated old `MockTransport` in favour of `respx.mock(...)`. (PR #109)
- Wrapping actual `MockTransport` in `MockRouter`, instead of extending. (PR #109)
- Extracted a `HTTPXMock`, for transport patching, from `MockRouter`. (PR #109)

## [0.16.0] - 2020-11-13

One year since first release, yay!

### Removed

- Dropped all deprecated APIs and models, see `0.15.0` Changed section. (PR #105)

### Added

- Added support for content, data and json patterns. (PR #106)
- Automatic pattern registration when subclassing Pattern. (PR #108)

### Fixed

- Multiple snapshots to support nested mock routers. (PR #107)

## [0.15.1] - 2020-11-10

### Added

- Snapshot routes and mocks when starting router, rollback when stopping. (PR #102)
- Added support for base_url combined with pattern lookups. (PR #103)
- Added support for patterns/lookups to the HTTP method helpers. (PR #104)

### Fixed

- Fix to not clear routes added outside mock context when stopping router. (PR #102)

## [0.15.0] - 2020-11-09

### Added

- Added `respx.route(...)` with enhanced request pattern matching. (PR #96)
- Added support for AND/OR when request pattern matching. (PR #96)
- Added support for adding responses to a route using % operator. (PR #96)
- Added support for both `httpx.Response` and `MockResponse`. (PR #96)
- Enhanced Route (RequestPattern) with `.respond(...)` response details. (PR #96)
- Enhanced Route (RequestPattern) with `.pass_through()`. (PR #96)
- Add support for using route as side effect decorator. (PR #98)
- Add `headers` and `cookies` patterns. (PR #99)
- Add `contains` and `in` lookups. (PR #99)
- Introduced Route `.mock(...)` in favour of callbacks. (PR #101)
- Introduced Route `.return_value` and `.side_effect` setters. (PR #101)

### Changed

- Deprecated mixing of request pattern and response details in all API's. (PR #96)
- Deprecated passing http method as arg in `respx.add` in favour of `method=`. (PR #96)
- Deprecated `alias=...` in favour of `name=...` when adding routes. (PR #96)
- Deprecated `respx.aliases` in favour of `respx.routes`. (PR #96)
- Deprecated `RequestPattern` in favour of `Route`. (PR #96)
- Deprecated `ResponseTemplate` in favour of `MockResponse`. (PR #96)
- Deprecated `pass_through=` in HTTP method API's (PR #96)
- Deprecated `response` arg in side effects (callbacks). (PR #97)
- Stacked responses are now recorded on same route calls. (PR #96)
- Pass-through routes no longer capture real response in call stats. (PR #97)
- Stacked responses no longer keeps and repeats last response. (PR #101)

### Removed

- Removed support for regex `base_url`. (PR #96)
- Dropped support for `async` side effects (callbacks). (PR #97)
- Dropped support for mixing side effect (callback) and response details. (PR #97)

## [0.14.0] - 2020-10-15

### Added

- Added `text`, `html` and `json` content shorthands to ResponseTemplate. (PR #82)
- Added `text`, `html` and `json` content shorthands to high level API. (PR #93)
- Added support to set `http_version` for a mocked response. (PR #82)
- Added support for mocking by lowercase http methods, thanks @lbillinghamtn. (PR #80)
- Added query `params` to align with HTTPX API, thanks @jocke-l. (PR #81)
- Easier API to get request/response from call stats, thanks @SlavaSkvortsov. (PR #85)
- Enhanced test to verify better content encoding by HTTPX. (PR #78)
- Added Python 3.9 to supported versions and test suite, thanks @jairhenrique. (PR #89)

### Changed

- `ResponseTemplate.content` as proper getter, i.e. no resolve/encode to bytes. (PR #82)
- Enhanced headers by using HTTPX Response when encoding raw responses. (PR #82)
- Deprecated `respx.stats` in favour of `respx.calls`, thanks @SlavaSkvortsov. (PR #92)

### Fixed

- Recorded requests in call stats are pre-read like the responses. (PR #86)
- Postponed request decoding for enhanced performance. (PR #91)
- Lazy call history for enhanced performance, thanks @SlavaSkvortsov. (PR #92)

### Removed

- Removed auto setting the `Content-Type: text/plain` header. (PR #82)

## [0.13.0] - 2020-09-30

### Fixed

- Fixed support for `HTTPX` 0.15. (PR #77)

### Added

- Added global `respx.pop` api, thanks @paulineribeyre. (PR #72)

### Removed

- Dropped deprecated `HTTPXMock` in favour of `MockTransport`.
- Dropped deprecated `respx.request` in favour of `respx.add`.
- Removed `HTTPX` max version requirement in setup.py.

## [0.12.1] - 2020-08-21

### Fixed

- Fixed non-iterable pass-through responses. (PR #68)

## [0.12.0] - 2020-08-17

### Changed

- Dropped no longer needed `asynctest` dependency, in favour of built-in mock. (PR #69)

## [0.11.3] - 2020-08-13

### Fixed

- Fixed support for `HTTPX` 0.14.0. (PR #45)

## [0.11.2] - 2020-06-25

### Added

- Added support for pop'ing a request pattern by alias, thanks @radeklat. (PR #60)

## [0.11.1] - 2020-06-01

### Fixed

- Fixed mocking `HTTPX` clients instantiated with proxies. (PR #58)
- Fixed matching URL patterns with missing path. (PR #59)

## [0.11.0] - 2020-05-29

### Fixed

- Fixed support for `HTTPX` 0.13. (PR #57)

### Added

- Added support for mocking out `HTTP Core`.
- Added support for using mock transports with `HTTPX` clients without patching.
- Include LICENSE.md in source distribution, thanks @synapticarbors.

### Changed

- Renamed passed mock to decorated functions from `httpx_mock` to `respx_mock`.
- Renamed `HTTPXMock` to `MockTransport`, but kept a deprecated `HTTPXMock` subclass.
- Deprecated `respx.request()` in favour of `respx.add()`.

## [0.10.1] - 2020-03-11

### Fixed

- Fixed support for `HTTPX` 0.12.0. (PR #45)

## [0.10.0] - 2020-01-30

### Changed

- Refactored high level and internal api for better editor autocompletion. (PR #44)

## [0.9.0] - 2020-01-22

### Fixed

- Fixed usage of nested or parallel mock instances. (PR #39)

## [0.8.3] - 2020-01-10

### Fixed

- Fixed support for `HTTPX` 0.11.0 sync api. (PR #38)

## [0.8.2] - 2020-01-07

### Fixed

- Renamed refactored httpx internals. (PR #37)

## [0.8.1] - 2019-12-09

### Added

- Added support for configuring patterns `base_url`. (PR #34)
- Added manifest and `py.typed` files.

### Fixed

- Fixed support for `HTTPX` 0.9.3 refactorizations. (PR #35)

## [0.8] - 2019-11-27

### Added

- Added documentation built with `mkdocs`. (PR #30)

### Changed

- Dropped sync support and now requires `HTTPX` version 0.8+. (PR #32)
- Renamed `respx.mock` module to `respx.api`. (PR #29)
- Refactored tests- and checks-runner to `nox`. (PR #31)

## [0.7.4] - 2019-11-24

### Added

- Allowing assertions to be configured through decorator and context manager. (PR #28)

## [0.7.3] - 2019-11-21

### Added

- Allows `mock` decorator to be used as sync or async context manager. (PR #27)

## [0.7.2] - 2019-11-21

### Added

- Added `stats` to high level API and patterns, along with `call_count`. (PR #25)

### Fixed

- Allowing headers to be modified within a pattern match callback. (PR #26)

## [0.7.1] - 2019-11-20

### Fixed

- Fixed responses in call stats when using synchronous `HTTPX` client. (PR #23)

## [0.7] - 2019-11-19

### Added

- Added support for `pass_through` patterns. (PR #20)
- Added `assert_all_mocked` feature and setting. (PR #21)

### Changed

- Requires all `HTTPX` requests to be mocked.

## [0.6] - 2019-11-18

### Changed

- Renamed `activate` decorator to `mock`. (PR #15)

## [0.5] - 2019-11-18

### Added

- Added `assert_all_called` feature and setting. (PR #14)

### Changed

- Clears call stats when exiting decorator.

## [0.4] - 2019-11-16

### Changed

- Renamed python package to `respx`. (PR #12)
- Renamed `add()` to `request()` and added HTTP method shorthands. (PR #13)

## [0.3.1] - 2019-11-16

### Changed

- Renamed PyPI package to `respx`.

## [0.3] - 2019-11-15

### Added

- Exposes `responsex` high level API along with a `activate` decorator. (PR #5)
- Added support for custom pattern match callback function. (PR #7)
- Added support for repeated patterns. (PR #8)

## [0.2] - 2019-11-14

### Added

- Added support for any `HTTPX` concurrency backend.

## [0.1] - 2019-11-13

### Added

- Initial POC.
