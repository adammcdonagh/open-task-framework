import argparse
import json
import os
import re
import logging
import pwd
import grp

# Remote script intended to serve as a utility to the main script for dealing with file transfers


def list_files(pattern, details=False):
    file_regex = os.path.basename(pattern)
    directory = os.path.dirname(pattern)
    files = None
    try:
        files = [
            f"{directory}/{f}" for f in os.listdir(directory) if re.match(file_regex, f)]
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
            result[file]['size'] = size
            result[file]['modified_time'] = modified_time
        return result

    return files


parser = argparse.ArgumentParser()
parser.add_argument(
    "-l", "--listFiles", help="Regex of files to look for", type=str, required=False)
parser.add_argument(
    "-d", "--details", help="Include file details in output", action='store_true', required=False)
parser.add_argument(
    "-m", "--moveFiles", help="List of source files to move from one directory to another", required=False)
parser.add_argument(
    "--deleteFiles", help="List of source files to delete as a post copy action", required=False)
parser.add_argument(
    "--destination", help="Destination directory to move files into", required=False)
parser.add_argument(
    "--owner", help="Owner to set on files to be moved", required=False)
parser.add_argument(
    "--group", help="Group to set on files to be moved", required=False)
parser.add_argument(
    "--mode", help="Mode to set on files to be moved", required=False)
parser.add_argument(
    "--renameRegex", help="Regex expression to apply to filenames", required=False)
parser.add_argument(
    "--renameSub", help="Regex substitution to apply to filenames", required=False)

args = parser.parse_args()

if args.listFiles:
    print(json.dumps(list_files(args.listFiles, args.details)))

if args.deleteFiles:
    files = args.deleteFiles.split()
    for file in list(files):
        print(f"Deleting {file}")
        os.unlink(file)

if args.moveFiles:
    # Split the moveFiles arg into a list
    files = args.moveFiles.split()
    for file in list(files):

        file = os.path.expanduser(file)
        print(f"Handling {file}")

        # Change ownership and permissions
        if args.owner:
            uid = pwd.getpwnam(args.owner).pw_uid
            print(f"Setting owner to {args.owner}")
            os.chown(file, uid, -1)

        if args.group:
            gid = grp.getgrnam(args.group).gr_gid
            print(f"Setting group to {args.group}")
            os.chown(file, -1, gid)

        if args.mode:
            print(f"Setting mode to {args.mode}")
            os.chmod(file, int(args.mode, 8))

        # Apply any regex substitution if needed
        if args.renameRegex:

            orig_filename = os.path.basename(file)
            orig_dirname = os.path.dirname(file)
            new_filename = f"{orig_dirname}/{re.sub(args.renameRegex, args.renameSub, orig_filename)}"
            print(f"Renaming: {file} to {new_filename}")
            os.rename(file, new_filename)
            file = new_filename

        # Now we can move the file into it's final location
        filename = os.path.basename(file)
        print(f"Moving {file} to {args.destination}/{filename}")
        os.rename(file, f"{args.destination}/{filename}")
