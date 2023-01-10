#!/bin/bash

# Create dummy variable for lookup command
echo "file_variable" > /tmp/variable_lookup.txt

# Get current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create test files
echo "test" > $DIR/testFiles/ssh_1/src/test.txt
echo "test" > $DIR/testFiles/ssh_2/src/test.txt

echo "012345678901" > $DIR/testFiles/ssh_1/src/log.1.gt10.lt20.test1234.log
echo "012345678901" > $DIR/testFiles/ssh_1/src/log.2.gt10.lt20.test1234.log
echo "01234567" > $DIR/testFiles/ssh_1/src/log.1.lt10.test1234.log
echo "012345678901234567890" > $DIR/testFiles/ssh_1/src/log.1.gt20.test1234.log

# Get the current year
YEAR=$(date +"%Y")
echo "someText" > $DIR/testFiles/ssh_1/src/log${YEAR}Watch.log