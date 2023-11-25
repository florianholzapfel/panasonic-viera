from distutils.core import setup

setup(
    name = 'panasonic_viera',
    packages = ['panasonic_viera'],
    version = '0.4.0',
    description = 'Library to control Panasonic Viera TVs',
    author = 'Florian Holzapfel',
    author_email = 'flo.holzapfel@gmail.com',
    url = 'https://github.com/florianholzapfel/panasonic-viera',
    download_url = 'https://github.com/florianholzapfel/panasonic-viera/archive/master.zip',
    keywords = ['panasonic', 'viera'],
    classifiers = [],
    install_requires = ['async-timeout', 'pycryptodome', 'xmltodict'],
)
