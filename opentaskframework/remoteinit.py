from paramiko import SSHClient, AutoAddPolicy

# Handles the validation of the remote hosts


def validate_remote_host(hostname, protocol):
    print("Remote setup")

    if protocol["name"] == "ssh":
        print("Using SSH")
        # Check that we can establish a connection to the remote host, and if so, return that connection
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(hostname, username=protocol["credentials"]
                       ["username"], password=protocol["credentials"]["password"])
        stdin, stdout, stderr = client.exec_command("ls -lart")
        with stdout as stdout_fh:
            print(stdout_fh.read().decode("UTF-8"))

        stdin, stdout, stderr = client.exec_command("date")
        with stdout as stdout_fh:
            print(stdout_fh.read().decode("UTF-8"))
        client.close()
