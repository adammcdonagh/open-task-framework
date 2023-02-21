
![unittest status](https://github.com/adammcdonagh/open-task-framework/actions/workflows/unittest.yml/badge.svg?event=push)


Open Task Framework (OTF) is a Python based framework to make it easy to run predefined file transfers and scripts/commands on remote machines.

Currently the framework is primarily based around being able to use SSH to communicate with remote hosts in order to manipulate files and run commands. This is done via the use of SSH keys, which must be set up in advance.

OTF has 3 main concepts for tasks. These are:
* Transfers
* Executions
* Batches

## **Transfers**
As the name suggests, these are just file transfers from a source system, to 1 or more destinations.
At present, this only supports transfer via SFTP/SSH, but in future the plan is to add S3 capabilities too.

In addition to a simple file transfer, transfers can poll for files, watch the contents of log files, only collect files based on age and size, and carry out post copy actions (archive or delete source file) once the transfer has completed.

## **Executions**
Again, fairly obvious, this will run commands on one or more remote hosts via SSH.

## **Batches**
A batch is a combination of the above 2 task types, and other batches too.

Batches can have dependencies between tasks, timeouts, and failure recovery e.g. rerunning from the last point of failure

# Configuration

There are several ways to customise the running of tasks. 

## Command Line Arguments

The following details the syntax of the `task-run` command:

```
usage: task-run [-h] -t TASKID [-r RUNID] [-v VERBOSITY] [-c CONFIGDIR]

options:
  -h, --help            show this help message and exit
  -t TASKID, --taskId TASKID
                        Name of the JSON config to run
  -r RUNID, --runId RUNID
                        Unique identifier to correlate logs with. e.g. if being triggered by an external scheduler
  -v VERBOSITY, --verbosity VERBOSITY
                        Increase verbosity
  -c CONFIGDIR, --configDir CONFIGDIR
                        Directory containing task configurations
```

**-t, --taskId**

This relates to the specific task that you want to run. It is the name of the configuration file to load (without the .json suffix), contained under the `CONFIGDIR`

**-r, --runId**

A log aggregation mechanism to bundle logs for several steps in a batch together. e.g. if you pass in `-r some_job_name`, the log files for all executions and transfers will be placed under `<logdir>/some_job_name/`

**-v, --verbosity**

There are 3 levels of logging, beyond the default INFO level. These are VERBOSE1 (1), VERBOSE2 (2), and DEBUG (3).

VERBOSITY is an integer; 1, 2 or 3

**-c, --configDir**

The directory containing all of the config files. These are the task definition JSON files, as well as the variables Jinja2 template file. 

In order for the process to run, you must have at least one task, and a `variables.json.j2` file, even if it's just an empty object definition
## Environment Variables

   * `OTF_NO_LOG` - Disable logging to file. Only log to stderr
   * `OTF_LOG_DIRECTORY` - Path under which log files are written
   * `OTF_RUN_ID` - An aggregator for log files. When set, all log files for a run will go under this sub directory. E.g. running a batch, all execution and transfer logs will be dropped into this sub directory, rather than a directory for each task name. This is equivalent to using `-r` or `--runId` command line arguments, which is generally preferred.

## Variables

Variables can exist at a global level, and also on a per-task basis.

You must always have a `variables.json.j2` file defined at the root of your `configDir`.

Variables can be used using the Jinja2 template syntax within task definitions. They can also be nested.

Individual tasks can have their own local variables too

### Example Variables

Below are examples of some useful variables to start with:

```json
"YYYY": "{{ now().strftime('%Y') }}",
"MM": "{{ now().strftime('%m') }}",
"DD": "{{ now().strftime('%d') }}",
"TODAY": "{{ YYYY }}{{ MM }}{{ DD }}",
"MONTH_SHORT": "{{ now().strftime('%b') }}",
"DAY_SHORT": "{{ now().strftime('%a') }}",
"PREV_DD": "{{ (now()|delta_days(-1)).strftime('%d') }}",
"PREV_MM": "{{ (now()|delta_days(-1)).strftime('%m') }}",
"PREV_YYYY": "{{ (now()|delta_days(-1)).strftime('%Y') }}"
```

Usage:

```json
"fileRegex": "somefile.*{{ YYYY }}\\.txt"
```

# Task Definitions

## Transfers

Transfers consist of a `source` definition, and an optional `destination`.

The easiest way to see usage is to look at the examples under the `examples` directory. In addition, the JSON schemas are defined in `src/opentaskpy/config/schemas.py`

Below is an example of all the options available for a transfer:

```json
{
  "type": "transfer",
  "source": {
    "hostname": "{{ HOST_A }}",
    "directory": "/tmp/testFiles/src",
    "fileRegex": ".*\\.txt",
    "fileWatch": {
      "timeout": 15,
      "directory": "/tmp/testFiles/src",
      "fileRegex": "fileWatch\\.txt"
    },
    "logWatch": {
      "timeout": 15,
      "directory": "/tmp/testFiles/src",
      "log": "log{{ YYYY }}Watch1.log",
      "contentRegex": "someText[0-9]",
      "tail": true
    },
    "conditionals": {
      "size": {
        "gt": 10,
        "lt": 20
      },
      "age": {
        "gt": 60,
        "lt": 600
      }
    },
    "postCopyAction": {
      "action": "move",
      "destination": "/tmp/testFiles/archive"
    },
    "protocol": {
      "name": "ssh",
      "credentials": {
        "username": "{{ SSH_USERNAME }}"
      }
    }
  },
  "destination": [
    {
      "hostname": "{{ HOST_B }}",
      "directory": "/tmp/testFiles/dest",
      "permissions": {
        "group": "operator"
      },
      "protocol": {
        "name": "ssh",
        "credentials": {
          "username": "{{ SSH_USERNAME }}"
        }
      }
    },
    {
      "hostname": "{{ HOST_B }}",
      "directory": "/tmp/testFiles/dest",
      "transferType": "pull",
      "rename": {
        "pattern": "^(.*)\\.txt$",
        "sub": "\\1-2.txt"
      },
      "protocol": {
        "name": "ssh",
        "credentials": {
          "username": "{{ SSH_USERNAME }}",
          "transferUsername": "{{ SSH_USERNAME }}"
        }
      }
    }
  ]
}
```

An explaination of what's going on in the order it will handled:

1. Tail the log file matching named: `/tmp/testFiles/src/log{{ YYYY }}Watch1.log` for lines matching containing the regex `someText[0-9]`, for up to 15 seconds, before giving up.
2. Poll for a file matching the regex `/tmp/testFiles/src/fileWatch\.txt` for up to 15 seconds.
3. Find all files matching the regex `/tmp/testFiles/src/.*\.txt`, with the conditions that the are >10B and <20B in size, as well as being older than 60 seconds, but newer than 600 seconds since last modification
4. Transfer the files that were found to 2 destinations. 
   1. The first destination is a simple SCP from `HOST_A` to `HOST_B` where the file is placed under `/tmp/testFiles/dest`. The group ownership of the file(s) is then set to `operator`
   2. The second destination is done via a pull from the destination server into the same directory. The SCP connects to `HOST_A` as `transferUsername`. Once the file has been retrieved, it is renamed using the following regex match `^(.*)\.txt$` and substitution `\1-2.txt`
5. Transferred files are moved into `/tmp/testFiles/archive` on `HOST_A`


## Executions

Executions are the simplest task to configure. They consist of a list of hosts to run on, the username to run/connect as, and the command to run.

Executions do not currently have a timeout, so can in theory run forever, or until they are killed. If a timeout is required, either use a wrapper script on the host the command is being executed on, or they should be wrapped inside a batch.

```json
{
  "type": "execution",
  "hosts": [
    "{{ HOST_A }}"
  ],
  "directory": "/tmp/testFiles/src",
  "command": "touch touchedFile.txt",
  "protocol": {
    "name": "ssh",
    "credentials": {
      "username": "{{ SSH_USERNAME }}"
    }
  }
}
```

The above is running the command `touch touchedFile.txt` on `{{ HOST_A }}`, from within the `/tmp/testFiles/src` directory.

If multiple `hosts` are defined, a thread is spawned in parallel for each host. If the command fails on any of the hosts in the list, it will cause the task run to fail, once all processes have returned a result.

## Batches 

Batches are a little more complex. They do not contain any task definitions, only the list, and order of excecution for each task.

A batch task can have multiple options set that determine the execution order and conditions, as well as how failures and task reruns are handled.

Each task in a batch has an `order_id`, this is a unique ID for each task, and is primarily used to define dependencies.

`dependencies` can be applied to any task, and are simply a list of other tasks that must be completed before it is triggered.

`continue_on_fail` is a boolean that defines whether a failure would cause the whole batch to fail immediately (after existing tasks have finished executing), or whether following steps get run. This defaults to false if not defined. 

`retry_on_rerun` is a boolean that determines whether a successful task is run a second time following a failed run. If a batch exits with a failure, and then the script is reun later on that same day, by default only the steps that failed will be run. All steps can be forced to run by setting this to true

`timeout` specifies the number of seconds a task is allowed to be running before it gets terminated. This counts as a failure. The default timeout, if not specified is 300 seconds.


# Development

This repo has been primarily configured to work with GitHub Codespaces devcontainers, though it can obviously be used directly on your machine too.

Dev and runtime packages are defined via pipenv, with a `requirements.txt` for the runtime package requirements

## Quickstart for development

* Clone this repo
* pip install pipenv
* pipenv --python 3.10 && pipenv install && cd src && pipenv install --editable .

### Building and uploading to PyPi

```bash
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```
