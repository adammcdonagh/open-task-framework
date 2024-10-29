# Changelog

# v24.44.1

- Fix batch logic to ensure that all tasks run before exiting

# v24.44.0

- Try to fix issue where SFTP connections were not being closed properly
- Force setting timeout for SFTP transport after connection is established
- Add extra log to SFTP transfers
- Change sleep log message to show how long it's actually sleeping for

# v24.42.0

- Fix issue where different protocols where not being detected properly, and proxy had to be explicitly defined when it was unnecessary
- When creating a destination directory with SFTP, it will now check whether lower level directories exist, and create them if not
- Always check for a directory before trying to delete it and thowing an exception if it doesn't exist.
- Moved exception printing for transfers to earlier in th code to ensure log messages aren't confusing.
- Add ability to check for SSH host key and validate it before proceeding with connection

# No release

- Bump `black` to 24.10.0

# v24.37.2

- Fix issue where nested variables were not being resolved correctly when using lazy loading

# v24.37.1

- Allow loading of multiple variables files via `OTF_VARIABLES_FILE` by specifying them comma-separated
- Ensure global time-based variables resolve when rendering nested variables

# v24.37.0

- Fix issue where new lazy loading code conflicts with `NOOP` mode, where it was trying to resolve variables regardless

# v24.36.2

- Add OTF_PARAMIKO_ULTRA_DEBUG environment variable to enable the hidden `ultra_debug` option for Paramiko (SFTP only).
- Add some more logging to the SFTP transfers
- Set `sftp_client` to `None` when closing the SFTP connection
- Added `OTF_LAZY_LOAD_VARIABLES` environment variable to enable lazy loading of variables.
- Updated `otflogging` to redact sensitive data from logs
- Increate the number of retries for SSH and SFTP connections

# v24.36.1

- Revert removal of some local transfer tests

# v24.36.0

- Add the option to specify conditionals for minimum and maximum expected counts of files matching regex to local, sftp and ssh sources

# v24.32.0

- Add dependabot config.
- Add debug logging to `get_latest_log_file` function
- Fix test for `get_latest_log_file` function to clear the log directory before running the test

# v24.30.0

- Add `supportsPosixRename` option to SFTP source so that post copy actions will work on server that don't support POSIX renames

# v24.25.0

- Remove stray `\\n` characters from private and public keys when doing encryption/decryption, and replace with proper newlines
- Fix workflow for changelog checking

# v24.23.0

- Added new `cacheableVariables` option for transfers. This allows you to specify a list of variables that should be cached and written back to somewhere (depending on the `cachingPlugin` referenced). This is useful for dynamically updated variables that need to be stored centrally. For more detail see the `README.md`ß

# v24.21.0

- Fixed renaming encrypted files when uploading via SFTP - Fixes [#79](https://github.com/adammcdonagh/open-task-framework/issues/79)
- Fix WRAPPER log file to ensure it closes when a child task fails due to an Exception - Fixes [#81](https://github.com/adammcdonagh/open-task-framework/issues/81)
- Allow different file extension for encrypted files. Added `output_extension` to allow a different file extension for GPG encrypted files, instead of the default `.gpg`
- When decrypting, handle both .gpg and .pgp file extensions by default before reverting to .decrypted exetnsion

# v24.19.1

- Add additional timeout values for SFTP connections - Attempting to fix [#68](https://github.com/adammcdonagh/open-task-framework/issues/68)
- Add more steps to capture all log output better

# v24.19.0

- When creating directories, ensure entire path is created recursively rather than just attempting to create rightmost path part

# v24.18.0

- Add the option to sign encrypted files using a private key, by setting `"sign": true`, and supplying the `private_key` property.

# v24.17.3

- Fix issue where using decryption meant that the encrypted file was also transferred to the destination.
- Improved some logging.

# v24.17.2

- Fix further issues relating to encryption and decryption.
- Added some additional tests to test via SFTP instead of just local transfers.

# v24.17.1

- Fix issue where PCA when encrypting files would only handle the encrypted file(s), and not the original file(s)

# v24.17.0

- Add protocol option for SFTP destination - `supportsStatAfterUpload` - When set to false this will prevent `stat` being run after upload. This helps when certain custom SFTP servers do not allow you to see your uploaded file, or they move it out of the way as soon as it's written to.
- Minor update to SFTP transfer when uploading to `/` to prevent destination path starting with `//`

# No release

- Updated linting rules and some formatting in the tests
- Updated devcontainer config etc to reflect the new linting etc

# v24.14.0

- Replace existing `now` Jinja function with `utc_now`. This always returns the UTC time. `now` will always return the localtime of the machine running the task instead.

# v24.13.1

- Fix an issue where local transfers were still deleting the source directory when tidying up the staging area, causing post copy actions to fail too

# v24.13.0

- Add PGP encryption to transfers - N.B. This is only possible where the files are being pulled onto the worker first, and then transferred to the destination. This is because the PGP encryption is done on the worker, and not on the source machine.
- Fixed an issue where files pushed from local worker would transfer more than just the files that matched the regex if they lived in the source directory
- BREAKING: Due to the above. `push_files_from_worker` now requires a file list to be passed when the source protocol is `local`. This is because the worker doesn't have the same context as the source machine, so it doesn't know what files are in the source directory. This is a breaking change, but it's necessary to ensure that the worker only pushes the files that are required.
- Added new option to SFTP destination in case `posix-rename` feature is not supported by the server. This prevents files being uploaded with a `.partial` extension, and instead uploads directly as the final filename. This is done by setting `supportsPosixRename` to `false` in the destination protocol definition.

# v24.11.0

- Fix an issue with batches not killing transfers when the task times out

# v24.10.0

- Update otflogging to be more thread safe when closing log file
- Fix [#60](https://github.com/adammcdonagh/open-task-framework/issues/60) by ensuring log file creation doesn't rely on OTF_TASK_ID env var, which is different between threads when running a batch task

# v24.9.0

- Fix timed out batch and transfer logging to ensure that the log file is closed correctly
- Reorder log format to bring log level to the front
- Add retry logic to SSH based connections
- Prevent local based transfers from using the staging directory

# v24.8.0

- Update `--noop` to work correctly for batch
- Add a simple batch config validator. This checks that there are consecutive tasks, tasks definitions exist, and dependencies are valid

# v24.5.1

- Add ability to specify a key string for SSH type connections

# v24.5.0

- Change versioning format
- Fixed file transfers to ensure that only files matching the regex are actually transferred

# v0.15.2

- Fix issue loading modules too fast with multiple steps in a batch

# v0.15.1

- Fix issue with logs not renaming correctly when an exception is thrown that's not caught
- Fix issue where `"error": false` for a transfer still caused the transfer to exit with a non-zero exit code

# v0.15.0

- Fix issue with chmods not actually working as intended
- Ensure valid test for chmod exists
- NEW: Allow independent environment variable based override of variables file while using same config file.
- NEW: Add `--noop` argument. This allows you to validate the config without executing anything.

# v0.14.3

- Fix issue with local file move when cross filesystem.

# v0.14.2

- Minor log verbosity update

# v0.14.1

- Fix issue where port number is being ignored because the schema definition doesn't match the code that uses it.

# v0.14.0

- Add mode override docs to `--help`
- Allow task definitions to use a whole templated object within them. e.g a protocol definition could be defined as a global variable to define SFTP connectivity to a commonly used source/destination. This is done using `.j2` task definition file instead of `.json`

# v0.13.1

- Fix protocol schemas to allow protocols other that SSH to actually be used for transfers
- Add some more documentation to the `--help` output

# v0.13.0

- Add additional tests to improve coverage
- Fix some SSH code to use SFTP client whenever possible
- Improve logging for batch tasks
- Fix a bug in local executions where timeouts were failing to parse the process listing, and run the `kill` command correctly
- Altered log format to include `filename` and `lineno` for log messages
- Remove `transfer.py` script. All transfer related commands for SSH protocol are now done natively using the SSH connection or SFTP commands

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
