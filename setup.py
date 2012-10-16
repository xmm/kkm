# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import re, os

version = re.search(
    "VERSION.*'(.+)'",
    open(os.path.join('kkm', '__init__.py')).read()).group(1)

try:
    license = open('LICENSE').read()
except:
    license = None

try:
    readme = open('README.rst').read()
except:
    readme = None

setup(
    name = 'kkm',
    version = version,
    packages = find_packages(),
    author = 'Marat Khayrullin',
    author_email = 'xmm.dev@gmail.com',
    description = 'библиотека для работы с контрольно-кассовыми машинами (фискальными регистраторами)',
    license=license,
    keywords = 'фискальный, регистратор, контрольно, кассовая, машина, ккм',
    url = 'https://github.com/xmm/kkm/',
    long_description = readme,
    install_requires = ['pySerial'],
    scripts = [],
)
