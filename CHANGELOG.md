# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.3] - 2020-01-10
### Fixed
- Fixed support for `HTTPX` 0.11.0 sync api. (PR #38)

## [0.8.2] - 2020-01-07
### Fixed
- Renamed refactored httpx internals. (PR #37)

## [0.8.1] - 2019-12-09
### Added
- Added support for configuring patterns `base_url`. (PR #34)

### Fixed
- Fixed support for `HTTPX` 0.9.3 refactorizations. (PR #35)
- Added manifest and `py.typed` files.

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
