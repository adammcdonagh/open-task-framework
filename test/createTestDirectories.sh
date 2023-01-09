#!/bin/bash

# Get current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Delete existing test files
rm -fr $DIR/testFiles/ssh_1/src $DIR/testFiles/ssh_1/dest $DIR/testFiles/ssh_1/archive 2>/dev/null
rm -fr $DIR/testFiles/ssh_2/src $DIR/testFiles/ssh_2/dest $DIR/testFiles/ssh_2/archive  2>/dev/null

mkdir -p $DIR/testFiles/ssh_1/dest $DIR/testFiles/ssh_1/src $DIR/testFiles/ssh_1/archive $DIR/testFiles/ssh_1/ssh
mkdir -p $DIR/testFiles/ssh_2/dest $DIR/testFiles/ssh_2/src $DIR/testFiles/ssh_2/archive $DIR/testFiles/ssh_2/ssh
