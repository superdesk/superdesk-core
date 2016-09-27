#!/bin/bash
INPUTFILE=$1
OUTPUTFILE=$INPUTFILE.new

# remove undesired Submodule and Module contents sections
sed -e '/^Submodules$/d' -e '/^----------$/d' -e '/^Module contents$/d' -e '/^---------------$/d' $INPUTFILE > $OUTPUTFILE

# Add any additional post generated formatting rules here

mv $OUTPUTFILE $INPUTFILE
