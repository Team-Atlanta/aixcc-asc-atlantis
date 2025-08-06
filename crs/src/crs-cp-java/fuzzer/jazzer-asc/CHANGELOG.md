# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [v3.0.0] – 2024-06-25

### Changed

- Revert back to upstream design that allows forked subprocesses, i.e., no
  longer blocking process builder. This enables testing components that fork
  instead of denying it as a partial security mitigation.

## [v2.0.0] – 2024-05-24

### Changed

- Updated sanitizers for the updated Jenkins Challenge

## [v1.0.0] – 2024-04-16

Initial release

<!-- markdownlint-disable-file MD024 -->
