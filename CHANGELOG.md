# Changelog

All notable changes to the SendGrid library for Griptape Nodes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/), and each version is
the `library_version` in `sendgrid_nodes/griptape_nodes_library.json`.
**Breaking** marks a change that can stop a saved workflow from working without edits.

## [Unreleased]

<!-- Entries go in changelog.d/, one file each. See changelog.d/README.md. -->

## [0.2.0] - 2026-11-06

### Changed

- **Breaking:** SendGrid Email fails the run when an attachment is over 10 MB or the attachments
  total over 30 MB. It used to set `status` to the error and finish normally, so downstream nodes ran
  as if the email had been handled. Shrink the attachments to stay under the limits.
  [#3](https://github.com/griptape-ai/griptape-nodes-library-sendgrid/issues/3)
- SendGrid Email shows its own error message when a run fails, with the HTTP status and SendGrid's
  response under More info. A missing `SENDGRID_API_KEY` is reported first and on its own, with links
  to Settings and SendGrid's key page, and a refused key links to Settings. A missing `To Email`,
  `From Email` or content stops the node before it starts. Requires engine 0.105.0 or later.
  [#3](https://github.com/griptape-ai/griptape-nodes-library-sendgrid/issues/3)

[Unreleased]: https://github.com/griptape-ai/griptape-nodes-library-sendgrid/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/griptape-ai/griptape-nodes-library-sendgrid/compare/a89bafc8d6d8039b2e5a1d3cd1849fd3312b3338...v0.2.0
