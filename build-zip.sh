#!/bin/bash

VERSION=jzhb-1.0

python setup.py bdist_wheel
rm -rf ./$VERSION
mkdir $VERSION
pushd $VERSION

cp ../dist/*whl ./
cp ../install.sh ./
cp ../jzhb ./
cp ../default.conf ./

popd

rm -f dist/$VERSION-bin.tgz
tar cvzf dist/$VERSION-bin.tgz ./$VERSION/
rm -rf ./$VERSION
ls -la dist/$VERSION*
