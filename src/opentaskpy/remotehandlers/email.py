import glob
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import opentaskpy.logging
from opentaskpy.remotehandlers.remotehandler import RemoteTransferHandler

MAX_OBJECTS_PER_QUERY = 100


class EmailTransfer(RemoteTransferHandler):
    TASK_TYPE = "T"

    def __init__(self, spec):
        self.spec = spec

        self.logger = opentaskpy.logging.init_logging(
            __name__, os.environ.get("OTF_TASK_ID"), self.TASK_TYPE
        )

    def set_handler_vars(self, protocol_vars):
        self.protocol_vars = protocol_vars

        # Also pull variables that have been set on the spec level
        # Replace/Append anything defined in self.protocol_vars with anything in self.spec["protocol"]
        for key, value in self.spec["protocol"].items():
            self.protocol_vars[key] = value
        # Remove name
        del self.protocol_vars["name"]

    def move_files_to_final_location(self, files):
        raise NotImplementedError()

    def list_files(self):
        raise NotImplementedError()

    def pull_files(self, files, remote_spec):
        raise NotImplementedError()

    def push_files_from_worker(self, local_staging_directory):
        result = 0
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
                    with open(file, "rb") as f:
                        part = MIMEApplication(f.read(), Name=file_name)
                    # After the file is closed
                    part["Content-Disposition"] = f'attachment; filename="{file_name}"'
                    msg.attach(part)
                except Exception as e:
                    self.logger.error(f"Failed to attach file: {file}")
                    self.logger.error(e)
                    result = 1

            # Get comma separated list of files
            file_list = ", ".join([file.split("/")[-1] for file in files])

            # Add a plaintext body to the email
            msg.attach(
                MIMEText(
                    self.spec["message"]
                    if "message" in self.spec
                    else f"Please find attached: {file_list }"
                )
            )
            # Set the email subject
            if "subject" in self.spec:
                msg["Subject"] = self.spec["subject"]

            msg["From"] = self.protocol_vars["sender"]

            # Send the email using a provided SMTP server
            try:
                self.logger.debug(f"Sending email to {email_address}")
                s = smtplib.SMTP(
                    self.protocol_vars["smtp_server"],
                    port=self.protocol_vars["smtp_port"],
                )
                s.starttls()

                # Authenticate
                s.login(
                    self.protocol_vars["credentials"]["username"],
                    self.protocol_vars["credentials"]["password"],
                )

                s.sendmail(self.protocol_vars["sender"], email_address, msg.as_string())
                s.quit()
            except Exception as e:
                self.logger.error(f"Failed to send email to {email_address}")
                self.logger.error(e)
                result = 1

        return result

    def pull_files_to_worker(self, files, local_staging_directory):
        raise NotImplementedError()

    def transfer_files(self, files, remote_spec, dest_remote_handler=None):
        raise NotImplementedError()

    def create_flag_files(self):
        raise NotImplementedError()

    def handle_post_copy_action(self, files):
        raise NotImplementedError()

    def tidy(self):
        pass
