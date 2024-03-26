"""Email handler to send files via email."""

import glob
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import opentaskpy.otflogging
from opentaskpy.remotehandlers.remotehandler import RemoteTransferHandler

MAX_OBJECTS_PER_QUERY = 100


class EmailTransfer(RemoteTransferHandler):
    """A remote handler for email transfers."""

    TASK_TYPE = "T"

    def __init__(self, spec: dict):
        """Initialise the handler."""
        self.protocol_vars: dict

        self.logger = opentaskpy.otflogging.init_logging(
            __name__, spec["task_id"], self.TASK_TYPE
        )

        super().__init__(spec)

    def supports_direct_transfer(self) -> bool:
        """Return whether this handler supports direct transfers."""
        return False

    def set_handler_vars(self, protocol_vars: dict) -> None:
        """Set the handler variables.

        Set any custom variables that are specifically needed for this handler.

        The schema defines the following variables:
        - smtp_server - The SMTP server to use
        - smtp_port - The SMTP port to use
        - sender - The sender of the email
        - credentials - A dictionary containing the following:
            - username - The username used to authenticate
            - password - The password used to authenticate

        Args:
            protocol_vars (dict): The protocol variables.

        """
        self.protocol_vars = protocol_vars

        # Also pull variables that have been set on the spec level
        # Replace/Append anything defined in self.protocol_vars with anything in self.spec["protocol"]
        for key, value in self.spec["protocol"].items():
            self.protocol_vars[key] = value
        # Remove name
        del self.protocol_vars["name"]

    def push_files_from_worker(
        self, local_staging_directory: str, file_list: dict | None = None
    ) -> int:
        """Push files from the worker to the email recipients.

        Args:
            local_staging_directory (str): The local staging directory.
            file_list (dict, optional): A dictionary of files to transfer. Defaults to None.

        Returns:
            int: The result of the transfer.
        """
        result = 0
        if file_list:
            files = list(file_list.keys())
        else:
            files = glob.glob(f"{local_staging_directory}/*")

        for email_address in self.spec["recipients"]:
            # Create an email message
            msg = MIMEMultipart()

            # Attach the files to the message
            for file in files:
                # Strip the directory from the file
                file_name = file.split("/")[-1]
                self.logger.debug(f"Emailing file: {files} to {email_address}")
                try:
                    with open(file, "rb") as file_handle:
                        part = MIMEApplication(file_handle.read(), Name=file_name)
                    # After the file is closed
                    part["Content-Disposition"] = f'attachment; filename="{file_name}"'
                    msg.attach(part)
                except Exception as ex:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to attach file: {file}")
                    self.logger.error(ex)
                    result = 1

            # Get comma separated list of files
            attachment_file_list = ", ".join([file.split("/")[-1] for file in files])

            # Add a plaintext body to the email
            msg.attach(
                MIMEText(
                    self.spec.get(
                        "message", f"Please find attached: {attachment_file_list}"
                    )
                )
            )
            # Set the email subject
            if "subject" in self.spec:
                msg["Subject"] = self.spec["subject"]

            msg["From"] = self.protocol_vars["sender"]

            # Send the email using a provided SMTP server
            try:
                self.logger.debug(f"Sending email to {email_address}")
                smtp = smtplib.SMTP(
                    self.protocol_vars["smtp_server"],
                    port=self.protocol_vars["smtp_port"],
                )
                smtp.starttls()

                # Authenticate
                smtp.login(
                    self.protocol_vars["credentials"]["username"],
                    self.protocol_vars["credentials"]["password"],
                )

                smtp.sendmail(
                    self.protocol_vars["sender"], email_address, msg.as_string()
                )
                smtp.quit()
            except Exception as ex:  # pylint: disable=broad-exception-caught
                self.logger.error(f"Failed to send email to {email_address}")
                self.logger.error(ex)
                result = 1

        return result

    def pull_files_to_worker(self, local_staging_directory: str) -> int:
        """Not implemented for this handler."""
        raise NotImplementedError

    def handle_post_copy_action(self, files: list) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def list_files(
        self, directory: str | None = None, file_pattern: str | None = None
    ) -> dict:
        """Not implemented for this handler."""
        raise NotImplementedError

    def move_files_to_final_location(self, files: list) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def pull_files(self, files: list) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def transfer_files(
        self, files: dict, remote_spec: dict, dest_remote_handler: dict | None = None
    ) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError
