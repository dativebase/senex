Senex
================================================================================

Senex is a web application for high-level administration of
`Online Linguistic Database (OLD)`_ applications.

With Senex installed, you can do the following (either from a web interface or
via the command line on your server):

- install the OLD software and its dependencies
- create new OLD instances (e.g., for particular lanaguages)
- start and stop existing OLD instances


Requirements
--------------------------------------------------------------------------------

Right now Senex will only work with Ubuntu servers. Versions 10.04 and 14.04
are being targeted.

The following must be installed in order for Senex to work. It can install the
rest of its requirements and the rest of the OLD's requirements on its own.

- Python 2.6 or 2.7
- MySQL server
- Apache 2
- git


TODO
--------------------------------------------------------------------------------

Create a bash install script for Senex itself.


Creating a Development Setup for Senex
--------------------------------------------------------------------------------

If you don't have Python setuptools installed in your system Python, install it.::

    $ sudo apt-get install python-setuptools

If you don't have Python's virtualenv installed in your system Python, then
install it using easy_install from setuptools.::

    $ sudo easy_install virtualenv

Create and activate a virtual environment.::

    $ virtualenv env
    $ source env/bin/activate

Download the Senex repo and install its dependencies.::

    $ git clone https://github.com/jrwdunham/senex.git
    $ cd senex
    $ python setup.py develop

Create Senex's database tables and serve it.::

    $ initialize_senex_db development.ini
    $ pserve development.ini


..: _`Online Linguistic Database (OLD)`: `http://www.onlinelinguisticdatabase.org`

