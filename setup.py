# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='jzhb',
    version='1.0',
    url='https://zahradil.info/git/jzhb',
    author='Jiri Zahradil',
    author_email='jz@zahradil.info',
    py_modules=['jzhb'],
    # data_files=[
    #     ('.', ['install.sh', 'jzhb']),
    # ],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        jzhb=jzhb:cli
    ''',
)
