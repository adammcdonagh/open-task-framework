# Full transfers expect that the remote host has a base install of python3
# We transfer over the wrapper script to the remote host and trigger it, which is responsible
# for doing the majority of the hard work

def run(transfer_definition):
    print("Running transfer")
