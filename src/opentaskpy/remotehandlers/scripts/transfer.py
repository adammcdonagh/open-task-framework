import argparse
import grp
import json
import logging
import os
import pwd
import re
import shutil

logger = logging.getLogger("opentaskpy.remotehandlers.scripts.transfer")

# Remote script intended to serve as a utility to the main script for dealing with file transfers


def list_files(pattern, details=False):
    file_regex = os.path.basename(pattern)
    directory = os.path.dirname(pattern)
    files = None
    try:
        files = [
            f"{directory}/{f}" for f in os.listdir(directory) if re.match(file_regex, f)
        ]
    except FileNotFoundError:
        files = []

    # For each file get the file age and size (incase we need then for file watches)
    if details:
        result = dict()
        for file in files:
            file_stat = os.stat(file)
            modified_time = file_stat.st_mtime
            size = file_stat.st_size
            result[file] = dict()
            result[file]["size"] = size
            result[file]["modified_time"] = modified_time
        return result

    return files


def delete_files(files, delimiter):
    files = files.split(delimiter)
    for file in list(files):
        logger.info(f"Deleting {file}")
        os.unlink(file)


def move_files(
    files,
    delimiter,
    destination,
    create_dest_dir,
    owner,
    group,
    mode,
    rename_regex,
    rename_sub,
):
    # Split the moveFiles arg into a list
    files = files.split(delimiter)
    for file in list(files):
        file = os.path.expanduser(file)
        logger.info(f"Handling {file}")

        # Change ownership and permissions
        if owner:
            uid = pwd.getpwnam(owner).pw_uid
            logger.info(f"Setting owner to {owner}")
            os.chown(file, uid, -1)

        if group:
            gid = grp.getgrnam(group).gr_gid
            logger.info(f"Setting group to {group}")
            os.chown(file, -1, gid)

        if mode:
            logger.info(f"Setting mode to {mode}")
            os.chmod(file, int(mode, 8))

        # Apply any regex substitution if needed
        if rename_regex:
            orig_filename = os.path.basename(file)
            orig_dirname = os.path.dirname(file)
            new_filename = (
                f"{orig_dirname}/{re.sub(rename_regex, rename_sub, orig_filename)}"
            )
            logger.info(f"Renaming: {file} to {new_filename}")
            os.rename(file, new_filename)
            file = new_filename

        # Verify the destination directory exists
        if not os.path.exists(destination) and create_dest_dir:
            logger.info(f"Creating destination directory: {destination}")
            os.makedirs(destination)
        elif not os.path.exists(destination):
            logger.error(
                f"ERROR: Destination directory does not exist: {destination}, and not requested to create it"
            )
            raise FileNotFoundError

        # Now we can move the file into it's final location
        filename = os.path.basename(file)
        logger.info(f"Moving {file} to {destination}/{filename}")

        # Save the existing permissions on the file
        file_stat = os.stat(file)
        # Copy the file, and then remove it
        shutil.copy(file, f"{destination}/{filename}")
        os.remove(file)
        # Move doesn't preserve ownership, so we need to do that manually

        # chown cannot set gid unless the current user is a member of that group
        # so we need to check if the current user is a member of the group
        # and if not, set the gid to -1
        # Check if the current user is a member of the group from file_stat.st_gid
        set_group = file_stat.st_gid
        if file_stat.st_gid not in os.getgroups():
            set_group = -1

        os.chown(f"{destination}/{filename}", file_stat.st_uid, set_group)
        os.chmod(f"{destination}/{filename}", file_stat.st_mode)


def main():
    logging.basicConfig(
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        level=logging.INFO,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--listFiles", help="Regex of files to look for", type=str, required=False
    )
    parser.add_argument(
        "-d",
        "--details",
        help="Include file details in output",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-m",
        "--moveFiles",
        help="List of source files to move from one directory to another",
        required=False,
    )
    parser.add_argument(
        "--deleteFiles",
        help="List of source files to delete as a post copy action",
        required=False,
    )
    parser.add_argument(
        "--destination", help="Destination directory to move files into", required=False
    )
    parser.add_argument(
        "--owner", help="Owner to set on files to be moved", required=False
    )
    parser.add_argument(
        "--group", help="Group to set on files to be moved", required=False
    )
    parser.add_argument(
        "--mode", help="Mode to set on files to be moved", required=False
    )
    parser.add_argument(
        "--renameRegex", help="Regex expression to apply to filenames", required=False
    )
    parser.add_argument(
        "--renameSub", help="Regex substitution to apply to filenames", required=False
    )
    parser.add_argument(
        "--delimiter",
        help="Character(s) used to separate filenames",
        required=False,
        type=str,
        default="|||",
    )
    parser.add_argument(
        "--createDestDir",
        help="Whether to create the destination directory, if it doesn't exist",
        required=False,
        action="store_true",
    )

    args = parser.parse_args()

    if args.listFiles:
        print(json.dumps(list_files(args.listFiles, args.details)))

    if args.deleteFiles:
        delete_files(args.deleteFiles, args.delimiter)

    if args.moveFiles:
        move_files(
            args.moveFiles,
            args.delimiter,
            args.destination,
            args.createDestDir,
            args.owner,
            args.group,
            args.mode,
            args.renameRegex,
            args.renameSub,
        )


if __name__ == "__main__":
    main()
