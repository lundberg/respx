# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
