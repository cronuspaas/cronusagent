#!/bin/bash

rm -rf target_cronus

DIR=$(cd "$(dirname "$0")"; pwd)
appname="myapp"
version="0.1.`date +%Y%m%d%H%M`"
pkgsrc=`ls $DIR`

wget -qO- 'http://cronuspaas.github.io/downloads/package_cronus' | DIR=$DIR appname=$appname version=$version pkgsrc=$pkgsrc bash

mkdir target_cronus
mv *.cronus *.cronus.prop target_cronus/

