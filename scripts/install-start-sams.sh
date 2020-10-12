#!/usr/bin/env sh

# Make the SAMS directory and pushd into it
mkdir ../sams
pushd ../sams

# Download SAMS
git clone -b develop --single-branch https://github.com/superdesk/sams.git sams

# Install Python packages
cd sams/src/server
time pip install -e .

cd ../clients/python
time pip install -e .

# Start the service
cd ../../server
export STORAGE_DESTINATION_1="MongoGridFS,Default,mongodb://localhost/sams"
honcho start &

started=0
while [ $started -eq 0 ]
do
    curl -s "http://localhost:5700" 2>&1 > /dev/null && started=1 || echo 'Waiting for SAMS...'
    sleep 5
done
echo 'SAMS now running'

# Change directory back to previous before this script
popd
