# Changelog

# v0.12.2

- Add additional tests to improve coverage
- Fix some SSH code to use SFTP client whenever possible

# v0.12.1

- Enforce source `directory` definition in transfer schemas for SSH and SFTP
- Ensure a recent `pylint` is being used
- Remove comment from CODEOWNERS file
- Add codecov to CI steps
- Add badges to `README.md`

# v0.12.0

- Added JSON formatter for logging to stderr. This replaces the default Python logging format with structured JSON output. This is enabled by setting the `OTF_LOG_JSON` environment variable to `1`. Log files are not impact, as these are always in standard format, as this is required for the batch log parsing to allow for rerunability.
- Tidy up logging
- Fix SSH transfers to ensure that SSH connections are fully closed after use
- Update SFTP transfers to use .partial file extension while files are being uploaded, and then rename them to their final name the transfer is complete.
- Altered log level for some messages
- Added `OTF_BATCH_RESUME_LOG_DATE` to allow resuming of batch runs from a specific date. This is useful if you want to rerun a batch from a specific date, especially if the failure happens just after midnight and the date is no longer the same as the original run.

# v0.11.0

- Added ability to run local transfers and executions using new `local` protocol. This is based on the same syntax as the SSH based protocols but doesn't need a `hostname` to be defined.
- Fixed an issue in the transfer taskhandler to ensure that protocols are handled correctly.
- Added missing `rename` functionality to the `sftp` protocol on destination files.

# v0.10.0

- Migrated deprecated jsonschema validation to use `referencing` package instead of `RefResolver`
- Added default SFTP protocol for transfers
- Added optional (unused) `createDirectoryIfNotExists` property to transfers for transfer destinations (SSH & SFTP). If `true` directory will be created with default permissions

# v0.9.0

- Linting updates
- Added new pre-commit tasks
- Add argument sanitisation when passing arguments for remote execution

# v0.8.1

- Added pre-commit config to devcontainer
- Applied pre-commit fixes
- Fixed task-run so that errors we actually get a non-zero return code on failures
- Update docs

# v0.8

- Added ability to override global variables at runtime. e.g. Override date variables to pick up files from previous days

## v0.7.1

- Removed old setup.py
- Removed old TODO message

## v0.7

- Add some Dockerfiles to allow `task-run` to be run via a Docker container
- Update documentation
- Add the ability to use a globally overridden SSH private key for connectivity via the `OTF_SSH_KEY` env var
- Update test fixture for SSH clients to ensure that the private key file being used is actually valid
- Fix protocol definition JSON schema to validate the use of `keyFile` in credentials section
- Permission issues with Docker tests

## v0.6.3

- Force requirement for protocol definition in JSON schemas

## v0.6.2

- Update package config to link to changelog
- Update `README.md` to show new workflow badge

## v0.6.1

- Added proper JSON validation code

## v0.4.2

- Updated batches to better kill threads.
- Fixed logging class to handle checking previous runs when the log dir doesn't already exist

## v0.4.1

- Fixed a bug in executions causing them not to generate an error if an exception is thrown when executing them .
