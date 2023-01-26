#!/bin/bash

# Get current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# If there's no id_rsa file already, create one
if [ ! -f $DIR/testFiles/id_rsa ]; then
    ssh-keygen -t rsa -N "" -f $DIR/testFiles/id_rsa
fi

# Copy the file into the test directory
# cp $DIR/testFiles/id_rsa $DIR/testFiles/ssh_1/ssh/id_rsa
# cp $DIR/testFiles/id_rsa $DIR/testFiles/ssh_2/ssh/id_rsa
# cp $DIR/testFiles/id_rsa.pub $DIR/testFiles/ssh_1/ssh/authorized_keys
# cp $DIR/testFiles/id_rsa.pub $DIR/testFiles/ssh_2/ssh/authorized_keys

mkdir -p ~/.ssh
cp $DIR/testFiles/id_rsa ~/.ssh/
chown -R $USER ~/.ssh
chmod -R 700 ~/.ssh

docker exec ssh_1 /bin/sh -c "usermod -G operator -a application"
docker exec ssh_2 /bin/sh -c "usermod -G operator -a application"
docker exec ssh_1 /bin/sh -c "mkdir -p ~application/.ssh"
docker exec ssh_2 /bin/sh -c "mkdir -p ~application/.ssh"

docker cp $DIR/testFiles/id_rsa ssh_1:/home/application/.ssh 
docker cp $DIR/testFiles/id_rsa.pub ssh_1:/home/application/.ssh/authorized_keys
docker exec ssh_1 /bin/sh -c "chown -R application ~application/.ssh && chmod -R 700 ~application/.ssh"

docker cp $DIR/testFiles/id_rsa ssh_2:/home/application/.ssh 
docker cp $DIR/testFiles/id_rsa.pub ssh_2:/home/application/.ssh/authorized_keys
docker exec ssh_2 /bin/sh -c "chown -R application ~application/.ssh && chmod -R 700 ~application/.ssh"
