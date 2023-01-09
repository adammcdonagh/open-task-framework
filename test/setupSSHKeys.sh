#!/bin/bash

# Get current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# If there's no id_rsa file already, create one
if [ ! -f $DIR/testFiles/id_rsa ]; then
    ssh-keygen -t rsa -N "" -f $DIR/testFiles/id_rsa
fi

# Copy the file into the test directory
cp $DIR/testFiles/id_rsa $DIR/testFiles/ssh_1/ssh/id_rsa 
cp $DIR/testFiles/id_rsa $DIR/testFiles/ssh_2/ssh/id_rsa
cp $DIR/testFiles/id_rsa.pub $DIR/testFiles/ssh_1/ssh/authorized_keys 
cp $DIR/testFiles/id_rsa.pub $DIR/testFiles/ssh_2/ssh/authorized_keys

mkdir -p ~/.ssh
cp $DIR/testFiles/id_rsa ~/.ssh/
chown -R $USER ~/.ssh
chmod -R 700 ~/.ssh