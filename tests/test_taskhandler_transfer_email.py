# pylint: skip-file
# ruff: noqa
import json
import os

from pytest_shell import fs

from opentaskpy.config.loader import ConfigLoader
from opentaskpy.taskhandlers import transfer
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

# Create a task definition
email_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*emailhandler.*\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "recipients": ["test@example.com", "test1@example.com"],
            "subject": "Test Email Subject",
            "protocol": {
                "name": "email",
                "credentials": {
                    "username": "{{ lookup('file', path='/tmp/smtp_username') }}",
                    "password": "{{ lookup('file', path='/tmp/smtp_password') }}",
                },
                "sender": "Test Sender <test@example.com>",
            },
        },
    ],
}

email_dummy_source_task_definition = {
    "type": "transfer",
    "source": {
        "protocol": {"name": "dummy"},
    },
    "destination": [
        {
            "recipients": ["test@example.com"],
            "subject": "Test Email Subject DUMMY SOURCE",
            "message": "This has not an attachment, but a custom body",
            "protocol": {
                "name": "email",
                "credentials": {
                    "username": "{{ lookup('file', path='/tmp/smtp_username') }}",
                    "password": "{{ lookup('file', path='/tmp/smtp_password') }}",
                },
                "sender": "Test Sender <test@example.com>",
            },
        },
    ],
}

email_html_dummy_source_task_definition = {
    "type": "transfer",
    "source": {
        "protocol": {"name": "dummy"},
    },
    "destination": [
        {
            "recipients": ["test@example.com"],
            "subject": "Test Email Subject DUMMY SOURCE",
            "messageContentType": "text/html",
            "message": (
                'This has not attachment, but a <b>custom body</b> with some <p style="color: red;">red text in a paragraph.</p>'
            ),
            "protocol": {
                "name": "email",
                "credentials": {
                    "username": "{{ lookup('file', path='/tmp/smtp_username') }}",
                    "password": "{{ lookup('file', path='/tmp/smtp_password') }}",
                },
                "sender": "Test Sender <test@example.com>",
            },
        },
    ],
}

email_plain_dummy_source_task_definition = {
    "type": "transfer",
    "source": {
        "protocol": {"name": "dummy"},
    },
    "destination": [
        {
            "recipients": ["test@example.com"],
            "subject": "Test Email Subject DUMMY SOURCE",
            "messageContentType": "text/plain",
            "message": "This has not attachment, but a plain message",
            "protocol": {
                "name": "email",
                "credentials": {
                    "username": "{{ lookup('file', path='/tmp/smtp_username') }}",
                    "password": "{{ lookup('file', path='/tmp/smtp_password') }}",
                },
                "sender": "Test Sender <test@example.com>",
            },
        },
    ],
}

email_task_definition_message_content_filename = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*emailhandler.*\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "recipients": ["test@example.com"],
            "subject": "Test Email Subject",
            "protocol": {
                "name": "email",
                "credentials": {
                    "username": "{{ lookup('file', path='/tmp/smtp_username') }}",
                    "password": "{{ lookup('file', path='/tmp/smtp_password') }}",
                },
                "sender": "Test Sender <test@example.com>",
            },
            "messageContentFilename": "/tmp/email-message.txt",
        },
    ],
}


def test_remote_handler():
    # Validate that given a transfer with email protocol, that we get a remote handler of type EmailTransfer

    transfer_obj = transfer.Transfer(None, "email-basic", email_task_definition)

    transfer_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert transfer_obj.source_remote_handler.__class__.__name__ == "SSHTransfer"

    # dest_remote_handler should be an array
    assert isinstance(transfer_obj.dest_remote_handlers, list)
    assert len(transfer_obj.dest_remote_handlers) == 1
    #  of SSHTransfer objects
    assert transfer_obj.dest_remote_handlers[0].__class__.__name__ == "EmailTransfer"


def test_remote_handler_vars(env_vars):
    # Load the global config
    config_loader = ConfigLoader("test/cfg")
    global_variables = config_loader.get_global_variables()
    global_variables["global_protocol_vars"] = [
        {"name": "email", "smtp_port": 587, "smtp_server": "smtp.gmail.com"}
    ]

    transfer_obj = transfer.Transfer(
        global_variables, "email-basic", email_task_definition
    )
    transfer_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert transfer_obj.source_remote_handler.__class__.__name__ == "SSHTransfer"

    # dest_remote_handler should be an array
    assert isinstance(transfer_obj.dest_remote_handlers, list)
    assert len(transfer_obj.dest_remote_handlers) == 1
    #  of SSHTransfer objects
    assert transfer_obj.dest_remote_handlers[0].__class__.__name__ == "EmailTransfer"

    # Check that the transfer object has an SMTP server config from the global config
    assert (
        transfer_obj.dest_remote_handlers[0].protocol_vars["smtp_server"]
        == "smtp.gmail.com"
    )


def test_email_transfer(env_vars, setup_ssh_keys, root_dir):

    import logging

    import opentaskpy.otflogging

    logger = opentaskpy.otflogging.init_logging(
        __name__, "email-transfer", level=logging.DEBUG, override_root_logger=True
    )

    # In GitHub Actions, the variables we need are in the environment
    # Pull those and write them to the config files first
    if os.getenv("GITHUB_ACTIONS"):
        # Get SMTP_USERNAME and SMTP_PASSWORD from environment and write them to files under /tmp
        fs.create_files(
            [
                {
                    "/tmp/smtp_username": {
                        "content": os.getenv("SMTP_USERNAME"),
                    }
                },
                {
                    "/tmp/smtp_password": {
                        "content": os.getenv("SMTP_PASSWORD"),
                    }
                },
            ]
        )

    # Create a file to transfer
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/emailhandler.txt": {"content": "test1234"}}]
    )

    # Write the email_task_definition to a file which we will read in to resolve the templated values for username and password
    task_definition_file = f"{root_dir}/cfg/transfers/email-transfer.json"
    # Delete the file if it exists
    if os.path.exists(task_definition_file):
        os.remove(task_definition_file)

    fs.create_files(
        [{task_definition_file: {"content": json.dumps(email_task_definition)}}]
    )

    # Load the global config
    config_loader = ConfigLoader("test/cfg")
    global_variables = config_loader.get_global_variables()
    global_variables["global_protocol_vars"] = [
        {"name": "email", "smtp_port": 587, "smtp_server": "smtp.gmail.com"}
    ]

    # Load the task definition using the config_loader
    imported_task_def = config_loader.load_task_definition("email-transfer")
    os.remove(task_definition_file)

    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    assert transfer_obj.run()

    # Check that files have been tidied up on the worker
    assert not os.path.exists(transfer_obj.local_staging_dir)

    # Now test the dummy source
    # Write the email_task_definition to a file which we will read in to resolve the templated values for username and password
    task_definition_file = f"{root_dir}/cfg/transfers/email-transfer-dummy.json"
    # Delete the file if it exists
    if os.path.exists(task_definition_file):
        os.remove(task_definition_file)

    fs.create_files(
        [
            {
                task_definition_file: {
                    "content": json.dumps(email_dummy_source_task_definition)
                }
            }
        ]
    )

    imported_task_def = config_loader.load_task_definition("email-transfer-dummy")
    os.remove(task_definition_file)

    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer-dummy", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    assert transfer_obj.run()


def test_email_transfer_message_content_filename(env_vars, setup_ssh_keys, root_dir):

    import logging

    import opentaskpy.otflogging

    logger = opentaskpy.otflogging.init_logging(
        __name__, "email-transfer-message-content-filename", level=logging.DEBUG
    )

    # In GitHub Actions, the variables we need are in the environment
    # Pull those and write them to the config files first
    if os.getenv("GITHUB_ACTIONS"):
        # Get SMTP_USERNAME and SMTP_PASSWORD from environment and write them to files under /tmp
        fs.create_files(
            [
                {
                    "/tmp/smtp_username": {
                        "content": os.getenv("SMTP_USERNAME"),
                    }
                },
                {
                    "/tmp/smtp_password": {
                        "content": os.getenv("SMTP_PASSWORD"),
                    }
                },
            ]
        )

    # Create a file to transfer
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/emailhandler.txt": {"content": "test1234"}}]
    )

    # Write the email_task_definition to a file which we will read in to resolve the templated values for username and password
    task_definition_file = (
        f"{root_dir}/cfg/transfers/email-transfer-message-content-filename.json"
    )
    # Delete the file if it exists
    if os.path.exists(task_definition_file):
        os.remove(task_definition_file)

    fs.create_files(
        [
            {
                task_definition_file: {
                    "content": json.dumps(
                        email_task_definition_message_content_filename
                    )
                },
            },
            {
                "/tmp/email-message.txt": {
                    "content": "This is the email message from a file"
                },
            },
        ]
    )

    # Load the global config
    config_loader = ConfigLoader("test/cfg")
    global_variables = config_loader.get_global_variables()
    global_variables["global_protocol_vars"] = [
        {"name": "email", "smtp_port": 587, "smtp_server": "smtp.gmail.com"}
    ]

    # Load the task definition using the config_loader
    imported_task_def = config_loader.load_task_definition(
        "email-transfer-message-content-filename"
    )
    os.remove(task_definition_file)

    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer-message-content-filename", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    assert transfer_obj.run()

    # Check that files have been tidied up on the worker
    assert not os.path.exists(transfer_obj.local_staging_dir)

    # Check that the message file has been deleted too
    assert not os.path.exists("/tmp/email-message.txt")

    # Write the email message file again, and this time send the email but explicitl specify not to delete the file
    fs.create_files(
        [
            {
                "/tmp/email-message.txt": {
                    "content": "This is the email message from a file"
                },
            },
        ]
    )

    imported_task_def["destination"][0]["deleteContentFileAfterTransfer"] = False
    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer-message-content-filename", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    assert transfer_obj.run()

    # Check that files have been tidied up on the worker
    assert not os.path.exists(transfer_obj.local_staging_dir)

    # Check that the message file has not been deleted
    assert os.path.exists("/tmp/email-message.txt")

    # Add a message to the task definition and validate that it failed because the message and messageContentFilename are both defined
    imported_task_def["destination"][0]["message"] = "This is the email message"
    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer-message-content-filename", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    with pytest.raises(Exception) as ex:
        transfer_obj.run()


def test_email_content_type(env_vars, setup_ssh_keys, root_dir):

    import logging

    import opentaskpy.otflogging

    logger = opentaskpy.otflogging.init_logging(
        __name__,
        "email-transfer-content-type",
        level=logging.DEBUG,
        override_root_logger=True,
    )

    # In GitHub Actions, the variables we need are in the environment
    # Pull those and write them to the config files first
    if os.getenv("GITHUB_ACTIONS"):
        # Get SMTP_USERNAME and SMTP_PASSWORD from environment and write them to files under /tmp
        fs.create_files(
            [
                {
                    "/tmp/smtp_username": {
                        "content": os.getenv("SMTP_USERNAME"),
                    }
                },
                {
                    "/tmp/smtp_password": {
                        "content": os.getenv("SMTP_PASSWORD"),
                    }
                },
            ]
        )

    # Now test the dummy source
    # Write the email_task_definition to a file which we will read in to resolve the templated values for username and password
    task_definition_file = f"{root_dir}/cfg/transfers/email-transfer-dummy-html.json"
    # Delete the file if it exists
    if os.path.exists(task_definition_file):
        os.remove(task_definition_file)

    fs.create_files(
        [
            {
                task_definition_file: {
                    "content": json.dumps(email_html_dummy_source_task_definition)
                }
            }
        ]
    )

    config_loader = ConfigLoader("test/cfg")
    global_variables = config_loader.get_global_variables()
    global_variables["global_protocol_vars"] = [
        {"name": "email", "smtp_port": 587, "smtp_server": "smtp.gmail.com"}
    ]

    imported_task_def = config_loader.load_task_definition("email-transfer-dummy-html")
    os.remove(task_definition_file)

    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer-dummy-html", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    assert transfer_obj.run()

    # Now test the dummy source
    # Write the email_task_definition to a file which we will read in to resolve the templated values for username and password
    task_definition_file = f"{root_dir}/cfg/transfers/email-transfer-dummy-plain.json"
    # Delete the file if it exists
    if os.path.exists(task_definition_file):
        os.remove(task_definition_file)

    fs.create_files(
        [
            {
                task_definition_file: {
                    "content": json.dumps(email_plain_dummy_source_task_definition)
                }
            }
        ]
    )

    config_loader = ConfigLoader("test/cfg")
    global_variables = config_loader.get_global_variables()
    global_variables["global_protocol_vars"] = [
        {"name": "email", "smtp_port": 587, "smtp_server": "smtp.gmail.com"}
    ]

    imported_task_def = config_loader.load_task_definition("email-transfer-dummy-plain")
    os.remove(task_definition_file)

    transfer_obj = transfer.Transfer(
        global_variables, "email-transfer-dummy-plain", imported_task_def
    )
    transfer_obj._set_remote_handlers()

    # Run the transfer
    assert transfer_obj.run()
