# ruff: noqa
import os
import shutil

import gnupg

TMPDIR = "/tmp/gpgtest"

shutil.rmtree(TMPDIR, ignore_errors=True)
os.makedirs(TMPDIR, exist_ok=True, mode=0o700)


def test_encryption():
    gpg = gnupg.GPG(gnupghome=f"{TMPDIR}")

    # Create a public/private key pair
    input_data = gpg.gen_key_input(
        key_type="RSA", key_length=4096, name_real="Test key", no_protection=True
    )
    key = gpg.gen_key(input_data)

    private_keys = gpg.list_keys(True)

    # Check there's 1 private key
    assert len(private_keys) == 1

    # Encrypt a file
    # Create a random file
    with open(f"{TMPDIR}/test.encryption.txt", "wb") as f:
        f.write(b"test1234")

    status = gpg.encrypt_file(
        f"{TMPDIR}/test.encryption.txt",
        always_trust=True,
        recipients=key.fingerprint,
        output=f"{TMPDIR}/test.encryption.txt.gpg",
    )

    assert status.ok
    assert os.path.exists(f"{TMPDIR}/test.encryption.txt.gpg")

    # Decrypt it
    with open(f"{TMPDIR}/test.encryption.txt.gpg", "rb") as encrypted_file:
        decryption_data = gpg.decrypt_file(
            encrypted_file,
            output=f"{TMPDIR}/test.decryption.txt",
        )
    assert decryption_data.ok
    assert decryption_data.returncode == 0

    # Validate the file contents match the original
    with open(f"{TMPDIR}/test.decryption.txt", "rb") as f:
        assert f.read() == b"test1234"

    print("###################################################################")
    print("Encryption test passed")
    print("###################################################################")


if __name__ == "__main__":
    test_encryption()
