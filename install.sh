#!/bin/bash

python3 -m venv venv
. venv/bin/activate

pip install --upgrade pip
pip install --upgrade setuptools wheel
pip install *.whl

ln -s $(realpath ./jzhb) ~/bin/jzhbck

echo -e "Script [jzhb] was installed to ~/bin ."
echo -e "Done."
