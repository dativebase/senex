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

The MySQL user specified via Senex's interface must exist and must have been
granted full privileges::

    mysql> CREATE USER 'newuser'@'localhost' IDENTIFIED BY 'password';
    mysql> GRANT ALL PRIVILEGES ON *.* TO 'newuser'@'localhost';
    mysql> FLUSH PRIVILEGES;


TODO
--------------------------------------------------------------------------------

- Create a bash install script for Senex itself.

- Add Python-crontab as a dependency in setup.py. From buildold:

    Python-crontab (https://pypi.python.org/pypi/python-crontab) should be
    installed if you want the OLD-restart cronjob to be created for you. But the
    script will still work without it.


Installing Senex
--------------------------------------------------------------------------------

First, if you don't have Python 2.7 as your system Python (which is the case
with Ubuntu 10.04), then install it using the instructions in `Install Python
2.7 on Ubuntu 10.04` below.

If Python 2.7 is your system python and you don't have Python setuptools
installed in it, then install it::

    $ sudo apt-get install python-setuptools

If you don't have Python's virtualenv installed in your system Python, then
install it using easy_install from setuptools::

    $ sudo easy_install virtualenv

Create a virtual environment::

    $ cd ~
    $ virtualenv env-senex

Download Senex's source from GitHub and install its dependencies::

    $ git clone https://github.com/jrwdunham/senex.git
    $ cd senex
    $ ~/env-senex/bin/python setup.py develop

Install the OLD and its dependencies::

    $ sudo ~/env-senex/bin/python senex/installold.py

Create Senex's database tables and serve it::

    $ ~/env-senex/bin/initialize_senex_db development.ini
    $ ~/env-senex/bin/pserve development.ini




Install Python 2.7 on Ubuntu 10.04
--------------------------------------------------------------------------------

Install it::

    $ sudo apt-get install python-software-properites
    $ sudo add-apt-repository ppa:fkrull/deadsnakes
    $ sudo apt-get update
    $ sudo apt-get install python2.7 python2.7-dev

Install setuptools for Python2.7::

    $ wget --no-check-certificate https://bootstrap.pypa.io/ez_setup.py -O - | sudo python2.7

If you don't have Python's virtualenv installed in your system Python, then
install it using easy_install from setuptools::

    $ sudo easy_install-2.7 virtualenv




Creating a Development Setup for Senex
--------------------------------------------------------------------------------

If you don't have Python setuptools installed in your system Python, install it::

    $ sudo apt-get install python-setuptools

If you don't have Python's virtualenv installed in your system Python, then
install it using easy_install from setuptools::

    $ sudo easy_install virtualenv

Create and activate a virtual environment::

    $ virtualenv env
    $ source env/bin/activate

Download the Senex repo and install its dependencies::

    $ git clone https://github.com/jrwdunham/senex.git
    $ cd senex
    $ python setup.py develop

Create Senex's database tables and serve it::

    $ initialize_senex_db development.ini
    $ pserve development.ini


.. _`Online Linguistic Database (OLD)`: http://www.onlinelinguisticdatabase.org

