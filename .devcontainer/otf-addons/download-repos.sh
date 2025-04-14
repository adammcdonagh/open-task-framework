#!/bin/bash

# Download each of the otf-addons repositories

for repo in $(cat otf-addons.txt); do
    echo "Downloading $repo"
    git clone https://github.com/adammcdonagh/otf-addons-$repo.git /workspaces/otf-addons-$repo
done
