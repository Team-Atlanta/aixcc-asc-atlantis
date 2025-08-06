#!/bin/bash

crsjoerndir=$1
joerndir=$2

rootdir=$(realpath "$(dirname "${BASH_SOURCE[0]}")"/..)
tooldir=$rootdir/tool
joerndir=${joerndir:-$tooldir/Joern}
sbtarchive=$tooldir/sbt-1.8.0.zip
sbt=$tooldir/sbt/bin/sbt


mkdir -p $(dirname $joerndir)
# Prepare Joern Source Code
if [ ! -d $joerndir ]; then
    if [ -d $crsjoerndir ]; then
        echo "Copy joern source code in CRS"
        cp -r $crsjoerndir $joerndir 
        rm $joerndir/.git
    else
        echo "Download joern source code from github"
        git clone git@github.com:Team-Atlanta/Joern.git $joerndir || exit 1
    fi
fi

# Prepare sbt
if command -v sbt &> /dev/null
then
    echo "sbt is already installed."
    sbt=$(which sbt)
elif [ ! -f $sbt ]; then
    echo "A1: $sbtarchive"
    if [ ! -f $sbtarchive ]; then
        echo "Download sbt"
        wget https://github.com/sbt/sbt/releases/download/v1.8.0/sbt-1.8.0.zip -O $sbtarchive
    fi
    echo "Install sbt"
    unzip $sbtarchive -d $tooldir
fi

# Build joern
echo "Building Joern"
cd $joerndir && SBT_OPTS="-Xmx12G" $sbt stage