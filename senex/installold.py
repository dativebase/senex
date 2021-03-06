#!/usr/bin/python

"""
================================================================================
  Install OLD
================================================================================

This file is both a module containing components for installing the OLD as well
as a command-line utility for installing the OLD. It was created using a fresh
Ubuntu 10.04 server install (with only MySQL, Apache, Python 2.6.5, git and
curl already installed). The OLD is the Online Linguistic Database, a
Python/Pylons, RESTful, JSON-communicating web service application for
collaborative linguistic fieldwork.

- OLD source code: https://github.com/jrwdunham/old
- OLD documentation: http://online-linguistic-database.readthedocs.org/en/latest/
- OLD on PyPI: https://pypi.python.org/pypi/onlinelinguisticdatabase
- OLD web site: http://www.onlinelinguisticdatabase.org


Usage
================================================================================

To install the OLD on your Ubuntu (or Debian?) server, run::

    $ ./installold.py

All downloaded source will be saved to ./tmp/. All stdout and stderr will be
saved to .log files in ./log/.


Summary
================================================================================

This tool installs the OLD in a Python virtual environment in ~/env/. It also
attempts to install PIL, FFmpeg, foma, and MITLM. Outputs to stdout and stderr
are combined and saved to descriptively named .log files in ./log/.

Listed below is a series of shell commands that you could execute manually and,
if all works, you should have the same result as running this script.::

    $ cd ~
    $ sudo apt-get -y install python-setuptools
    $ sudo easy_install virtualenv
    $ virtualenv --no-site-packages env
    $ env/bin/easy_install onlinelinguisticdatabase
    $ sudo apt-get -y install libmysqlclient-dev python-dev
    $ env/bin/easy_install MySQL-python
    $ env/bin/easy_install importlib
    $ sudo apt-get -y install libjpeg-dev libfreetype6 libfreetype6-dev zlib1g-dev
    $ wget http://effbot.org/downloads/Imaging-1.1.7.tar.gz
    $ tar -zxvf Imaging-1.1.7.tar.gz
    $ cd Imaging-1.1.7
    $ ~/env/bin/python setup.py build_ext -i
    $ ~/env/bin/python selftest.py
    $ ~/env/bin/python setup.py install
    $ cd ..
    $ sudo apt-get -y install libavcodec-extra-52 libavdevice-extra-52 libavfilter-extra-0 libavformat-extra-52 libavutil-extra-49 libpostproc-extra-51 libswscale-extra-0
    $ sudo apt-get -y install ffmpeg
    $ wget ftp://ftp.gnu.org/gnu/m4/m4-1.4.10.tar.gz
    $ tar -xvzf m4-1.4.10.tar.gz
    $ cd m4-1.4.10
    $ ./configure --prefix=/usr/local/m4
    $ make
    $ sudo make install
    $ cd ..
    $ wget http://ftp.gnu.org/gnu/bison/bison-2.3.tar.gz
    $ tar -xvzf bison-2.3.tar.gz
    $ cd bison-2.3
    $ PATH=$PATH:/usr/local/m4/bin/
    $ ./configure --prefix=/usr/local/bison
    $ make
    $ sudo make install
    $ cd ..
    $ sudo apt-get -y install flex
    $ sudo apt-get -y install subversion
    $ svn co http://foma.googlecode.com/svn/trunk/foma/
    $ PATH=$PATH:/usr/local/bison/bin/
    $ sudo apt-get -y install libreadline6 libreadline6-dev
    $ cd foma
    $ make
    $ sudo make install
    $ cd ..
    $ sudo apt-get -y install autoconf automake libtool gfortran
    $ wget https://mitlm.googlecode.com/files/mitlm-0.4.1.tar.gz
    $ tar -zxvf mitlm-0.4.1.tar.gz
    $ cd mitlm-0.4.1
    $ ./configure
    $ make
    $ sudo make install
    $ sudo ldconfig
    $ cd ..

"""

import re
import os
import sys
import shutil
import urllib
import optparse
import getpass
import pprint
import json
import datetime
import tarfile
import platform
from subprocess import Popen, PIPE, STDOUT

from buildold import create_directory_safely

# ANSI escape sequences for formatting command-line output.
ANSI_HEADER = '\033[95m'
ANSI_OKBLUE = '\033[94m'
ANSI_OKGREEN = '\033[92m'
ANSI_WARNING = '\033[93m'
ANSI_FAIL = '\033[91m'
ANSI_ENDC = '\033[0m'
ANSI_BOLD = '\033[1m'
ANSI_UNDERLINE = '\033[4m'


# Utils
################################################################################

def shell(cmd_list, cwd=None):
    """Execute `cmd_list` as a shell command, pipe stderr to stdout and return
    stdout. Specify the dir where the command should be run in `cwd`.

    """

    sp = Popen(cmd_list, cwd=cwd, stdout=PIPE, stderr=STDOUT)
    stdout, nothing = sp.communicate()
    return stdout


def aptgetupdate():
    """Run `sudo apt-get update`

    """

    if get_linux_id() == 'Ubuntu':
        shell(['sudo', 'apt-get', '-y', 'update'])


def aptget(lib_list):
    """Run `sudo apt-get -y install` on the libraries in `lib_list`. The -y
    option answers 'y' to interactive prompts.

    """

    return shell(['sudo', 'apt-get', '-y', 'install'] + lib_list)


def flush(string):
    """Print `string` immediately, and with no carriage return.

    """

    print string,
    sys.stdout.flush()


def log(fname, text):
    """Write `text` to a file named `fname` in ./log/.

    """

    if text.strip():
        path = os.path.join(get_log_path(), fname)
        with open(path, 'w') as f:
            f.write(text)


def clear_log():
    """Remove all files in ./log/

    """
    for fname in os.listdir(get_log_path()):
        if fname[0] != '.':
            path = os.path.join(get_log_path(), fname)
            if os.path.isfile(path):
                os.remove(path)


def clear_tmp():
    """Remove all files in ./tmp/

    """
    for fname in os.listdir(get_tmp_path()):
        if fname[0] != '.':
            path = os.path.join(get_tmp_path(), fname)
            if os.path.isfile(path):
                os.remove(path)


def which(program):
    """Return the path to `program` if it is an executable; otherwise return
    `None`. From
    http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python.

    """

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def get_linux_id():
    return shell(['lsb_release', '-is']).strip()


def get_linux_release():
    return shell(['lsb_release', '-rs']).strip()


def library_installed(name):
    """Return `True` if the Linux library identifiable by `name` is installed.

    """

    stdout = shell(['ldconfig', '-p', '|', 'grep', name])
    if stdout.strip():
        return True
    return False


def add_optparser_options(parser):
    """Add options to the optparser parser.

    """

    parser.add_option("--env-dir", dest="env_dir",
        metavar="ENV_DIR",
        help="The name of the virtual environment directory that the OLD"
            " is/will be installed in (in your home directory). Defaults"
            " to 'env'.")


def get_params():
    """Get parameters based on the arg and/or options entered at the command
    line.

    """

    usage = "usage: ./%prog [options]"
    parser = optparse.OptionParser(usage)
    add_optparser_options(parser)
    (options, args) = parser.parse_args()
    params = {
        'env_dir': options.env_dir or 'env-old'
    }
    return params


def get_home():
    """Return an absolute path to the user's home directory.

    """

    return os.path.expanduser('~')


def get_easy_install_path(params):
    """Return an absolute path to the easy_install binary in the virtual environment.

    """

    return os.path.join(get_home(), params['env_dir'], 'bin', 'easy_install')


def get_pip_path(params):
    """Return an absolute path to the pip binary in the virtual environment.

    """

    return os.path.join(get_home(), params['env_dir'], 'bin', 'pip')


def get_python_path(params):
    """Return an absolute path to python in the virtual environment.

    """

    return os.path.join(get_home(), params['env_dir'], 'bin', 'python')


def get_script_dir_path():
    """Return an absolute path to the directory containing this script.

    """

    return os.path.dirname(os.path.abspath(__file__))


def get_tmp_path():
    """Return an absolute path to ./tmp/.

    """

    return os.path.join(get_script_dir_path(), 'tmp')


def get_log_path():
    """Return an absolute path to ./log/.

    """

    return os.path.join(get_script_dir_path(), 'log')


# Installed Checkers
################################################################################

def old_installed(params):
    """Return `True` if OLD is installed in ~/env/.

    """

    python_path = get_python_path(params)
    if not os.path.isfile(python_path):
        return False
    stdout = shell([python_path, '-c', 'import onlinelinguisticdatabase'])
    if stdout.strip():
        return False
    return True


def importlib_installed(params):
    """Return `True` if importlib is installed in ~/env/.

    """

    python_path = get_python_path(params)
    if not os.path.isfile(python_path):
        return False
    stdout = shell([python_path, '-c', 'import importlib'])
    if stdout.strip():
        return False
    return True


def mysql_python_installed(params):
    """Return `True` if MySQL-python is installed in ~/env/.

    """

    python_path = get_python_path(params)
    if not os.path.isfile(python_path):
        return False
    stdout = shell([python_path, '-c', 'import MySQLdb'])
    if stdout.strip():
        return False
    return True


def pil_installed(params):
    """Return `True` if PIL (or Pillow) is installed in ~/env/.

    """

    python_path = get_python_path(params)
    if not os.path.isfile(python_path):
        return False
    if (platform.system() == 'Linux' and get_linux_id() == 'Ubuntu' and
            get_linux_release() == '14.04'):
        stdout = shell([python_path, '-c', 'from PIL import Image'])
    else:
        stdout = shell([python_path, '-c', 'import Image'])
    if stdout.strip():
        return False
    return True


# Installers
################################################################################

def get_system_python_version():
    """Check the Python version. If it's in major version 2 but is not 2.6 or
    2.7, exit. Also exit if it's major version 3.

    """

    version = sys.version.split(' ')[0]
    v_list = version.split('.')
    maj = v_list[0]
    min = v_list[1]
    if maj == '2':
        if min not in ['7', '6']:
            sys.exit('%sWarning, the OLD was developed on Python 2.6 and 2.7.'
                ' Your system Python is version %s. Please install Python 2.6 or'
                ' 2.7 using .pyenv prior to using this install script.'
                ' Aborting.%s' % (ANSI_FAIL, version, ANSI_ENDC))
    else:
        sys.exit('%sWarning, the OLD was developed on Python 2.6 and 2.7.'
            ' Your system Python is version %s. Please install Python 2.6 or'
            ' 2.7 using .pyenv prior to using this install script.'
            ' Aborting.%s' % (ANSI_FAIL, version, ANSI_ENDC))


def install_easy_install():
    """sudo apt-get install python-setuptools

    """

    if which('easy_install'):
        print 'easy_install is already installed.'
        return
    flush('Installing easy_install ...')
    stdout = aptget(['python-setuptools'])
    log('install-easy-install.log', stdout)
    if which('easy_install'):
        print 'Done.'
    else:
        sys.exit('%sFailed to install easy_install. Aborting.%s' % (
            ANSI_FAIL, ANSI_ENDC))


def install_virtualenv():
    """sudo easy_install virtualenv

    """

    if which('virtualenv'):
        print 'virtualenv is already installed.'
        return
    flush('Installing virtualenv ...')
    stdout = shell(['sudo', 'easy_install', 'virtualenv'])
    log('install-virtualenv.log', stdout)
    if which('virtualenv'):
        print 'Done.'
    else:
        sys.exit('%sFailed to install virtualenv. Aborting.%s' % (
            ANSI_FAIL, ANSI_ENDC))


def create_env(params):
    """virtualenv --no-site-packages ~/env

    """

    path = os.path.join(get_home(), params['env_dir'])
    if os.path.isfile(os.path.join(path, 'bin', 'python')):
        print 'A virtual environment already exists at %s.' % path
        return
    flush('Creating a virtual environment in %s ...' % path)
    stdout = shell(['virtualenv', '--no-site-packages', path])
    log('create-env.log', stdout)
    if os.path.isfile(os.path.join(path, 'bin', 'python')):
        print 'Done.'
    else:
        sys.exit('%sFailed to create a new virtual environment in'
            ' %s.%s' % (ANSI_FAIL, path, ANSI_ENDC))


def install_old(params):
    """~/env/bin/easy_install onlinelinguisticdatabase

    """

    if old_installed(params):
        print 'OLD is already installed.'
        return
    flush('Installing OLD ...')
    stdout = shell([get_easy_install_path(params), 'onlinelinguisticdatabase'])
    log('install-old.log', stdout)
    if old_installed(params):
        print 'Done.'
    else:
        sys.exit('%sFailed to install the OLD.%s' % (ANSI_FAIL, ANSI_ENDC))


def install_mysql_python(params):
    """Method::

        $ sudo apt-get -y install libmysqlclient-dev python-dev
        $ ~/env/bin/easy_install MySQL-python

    """

    if mysql_python_installed(params):
        print 'MySQL-python is already installed.'
        return
    flush('Installing MySQL-python ...')
    aptget(['libmysqlclient-dev', 'python-dev'])
    stdout = shell([get_easy_install_path(params), 'MySQL-python'])
    log('install-mysql-python.log', stdout)
    if mysql_python_installed(params):
        print 'Done.'
    else:
        sys.exit('%s.Failed to install MySQL-python.%s' % (
            ANSI_FAIL, ANSI_ENDC))


def install_importlib(params):
    """~/env/bin/easy_install importlib

    """

    if importlib_installed(params):
        print 'importlib is already installed.'
        return
    flush('Installing importlib ...')
    stdout = shell([get_easy_install_path(params), 'importlib'])
    log('install-importlib.log', stdout)
    if importlib_installed(params):
        print 'Done.'
    else:
        sys.exit('%sFailed to install importlib.%s' % (ANSI_FAIL,
            ANSI_ENDC))


def install_PIL_dependencies():
    """sudo apt-get install libjpeg-dev libfreetype6 libfreetype6-dev zlib1g-dev

    If we're using Ubuntu 12.04, we need to run::

        $ sudo ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/
        $ sudo ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/
        $ sudo ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/

    """

    if get_linux_id() == 'Ubuntu' and get_linux_release() == '14.04':
        stdout = aptget(['python-dev', 'libtiff5-dev', 'libjpeg8-dev',
            'zlib1g-dev', 'libfreetype6-dev', 'liblcms2-dev', 'libwebp-dev',
            'tcl8.6-dev', 'tk8.6-dev', 'python-tk'])
    elif get_linux_id() == 'Ubuntu' and get_linux_release() == '12.04':
        stdout = aptget(['libjpeg-dev', 'libfreetype6', 'libfreetype6-dev',
            'zlib1g-dev', 'libjpeg8-dev'])
        shell(['sudo', 'ln', '-s', '/usr/lib/`uname -i`-linux-gnu/libfreetype.so',
            '/usr/lib/'])
        shell(['sudo', 'ln', '-s', '/usr/lib/`uname -i`-linux-gnu/libjpeg.so',
            '/usr/lib/'])
        shell(['sudo', 'ln', '-s', '/usr/lib/`uname -i`-linux-gnu/ligz.so',
            '/usr/lib/'])
    else:
        stdout = aptget(['libjpeg-dev', 'libfreetype6', 'libfreetype6-dev',
            'zlib1g-dev'])
    log('install-PIL-dependencies.log', stdout)


def install_Pillow(params):
    stdout = shell([get_easy_install_path(params), 'Pillow'])
    log('install-Pillow.log', stdout)


def install_PIL(params):
    """Install PIL or Pillow.

    Method for installing PIL::

        $ wget http://effbot.org/downloads/Imaging-1.1.7.tar.gz
        $ tar -zxvf Imaging-1.1.7.tar.gz
        $ cd Imaging-1.1.7
        $ ~/env/bin/python setup.py build_ext -i
        $ ~/env/bin/python selftest.py
        $ ~/env/bin/python setup.py install

    """

    if pil_installed(params):
        print 'PIL is already installed.'
        return
    flush('Installing PIL ...')
    install_PIL_dependencies()
    if get_linux_id() == 'Ubuntu' and get_linux_release() == '14.04':
        install_Pillow(params)
    else:
        pilpath = os.path.join(get_tmp_path(), 'Imaging-1.1.7.tar.gz')
        pildirpath = os.path.join(get_tmp_path(), 'Imaging-1.1.7')
        fname, headers = urllib.urlretrieve(
            'http://effbot.org/downloads/Imaging-1.1.7.tar.gz', pilpath)
        if not os.path.isfile(pilpath):
            print ('%sUnable to download PIL. Aborting.%s' % (ANSI_FAIL,
                ANSI_ENDC))
            return
        tar = tarfile.open(pilpath, mode='r:gz')
        tar.extractall(path=get_tmp_path())
        tar.close()
        if not os.path.isdir(pildirpath):
            print ('%sUnable to extract PIL. Aborting.%s' % (ANSI_FAIL,
                ANSI_ENDC))
            return
        logtext = ['Ran `setup.py build_ext -i` in PIL\n\n']
        stdout = shell([get_python_path(params), 'setup.py', 'build_ext', '-i'],
            pildirpath)
        logtext.append(stdout)
        logtext.append('\n\nRan `selftext.py` in PIL\n\n')
        stdout = shell([get_python_path(params), 'selftest.py'], pildirpath)
        logtext.append(stdout)
        stdout = shell([get_python_path(params), 'setup.py', 'install'],
            pildirpath)
        logtext.append(stdout)
        log('install-PIL.log', '\n'.join(logtext))
    if pil_installed(params):
        print 'Done.'
    else:
        print 'Failed.'


def get_pil_tests(script_dir_path): 
    return  ("""
try:
    import Image
except ImportError:
    from PIL import Image

im = Image.open('%s/media/sample.jpg')
im.thumbnail((200, 200), Image.ANTIALIAS)
im.save('%s/media/small_sample.jpg')

im = Image.open('%s/media/sample.png')
im.thumbnail((200, 200), Image.ANTIALIAS)
im.save('%s/media/small_sample.png')

im = Image.open('%s/media/sample.gif')
im.thumbnail((200, 200), Image.ANTIALIAS)
im.save('%s/media/small_sample.gif')
""" % (script_dir_path,
       script_dir_path,
       script_dir_path,
       script_dir_path,
       script_dir_path,
       script_dir_path)).strip()


def test_PIL(params):
    """Test whether PIL is working correctly by creating thumbnails of a .jpg,
    a .gif, and a .png.

    """

    if pil_installed(params):
        flush('Testing PIL ...')
        pil_tests_dir = os.path.join(get_script_dir_path(), 'tests')
        create_directory_safely(pil_tests_dir)
        pil_tests_path = os.path.join(pil_tests_dir, 'pil.py')
        with open(pil_tests_path, 'w') as f:
            f.write(get_pil_tests(get_script_dir_path()))
        stdout = shell([get_python_path(params), pil_tests_path])
        print stdout
        try:
            for ext in ('gif', 'png', 'jpg'):
                orignm = 'sample.%s' % ext
                origpth = os.path.join(get_script_dir_path(), 'media', orignm)
                convnm = 'small_sample.%s' % ext
                convpth = os.path.join(get_script_dir_path(), 'media', convnm)
                assert os.path.isfile(convpth)
                assert os.path.getsize(convpth) < os.path.getsize(origpth)
            print 'PIL is working correctly.'
        except AssertionError:
            print ('%sWarning: the PIL installation does not seem to be able to'
                ' correctly reduce the size of .jpg, .png and/or .gif'
                ' files.%s' % (ANSI_WARNING, ANSI_ENDC))
        for ext in ('gif', 'png', 'jpg'):
            convnm = 'small_sample.%s' % ext
            convpth = os.path.join(get_script_dir_path(), 'media', convnm)
            if os.path.isfile(convpth):
                os.remove(convpth)
    else:
        print 'No tests possible: PIL not installed'


def install_FFmpeg_dependencies():
    """sudo apt-get -y install libavcodec-extra-52 libavdevice-extra-52 libavfilter-extra-0 libavformat-extra-52 libavutil-extra-49 libpostproc-extra-51 libswscale-extra-0

    """

    stdout = aptget(['libavcodec-extra-52', 'libavdevice-extra-52',
        'libavfilter-extra-0', 'libavformat-extra-52', 'libavutil-extra-49',
        'libpostproc-extra-51', 'libswscale-extra-0'])
    log('install-ffmpeg-dependencies.log', stdout)


def install_FFmpeg():
    """sudo apt-get -y install ffmpeg

    """

    if which('ffmpeg'):
        print 'FFmpeg is already installed.'
        return
    flush('Installing FFmpeg ...')
    if get_linux_id() == 'Ubuntu' and get_linux_release() == '14.04':
        shell(['sudo', 'add-apt-repository', '-y', 'ppa:mc3man/trusty-media'])
        shell(['sudo', 'apt-get', '-y', 'update'])
    else:
        install_FFmpeg_dependencies()
    stdout = aptget(['ffmpeg'])
    log('install-ffmpeg.log', stdout)
    if which('ffmpeg'):
        print 'Done.'
    else:
        print 'Failed.'


def test_FFmpeg():
    """Test to make sure that FFmpeg can convert .wav to both .mp3 and .ogg.

    """

    if not which('ffmpeg'):
        print 'No tests possible: FFmpeg not installed.'
        return
    flush('Testing FFmpeg ...')
    wavpth = os.path.join(get_script_dir_path(), 'media', 'sample.wav')
    mp3pth = os.path.join(get_script_dir_path(), 'media', 'sample.mp3')
    oggpth = os.path.join(get_script_dir_path(), 'media', 'sample.ogg')
    if os.path.isfile(mp3pth):
        os.remove(mp3pth)
    if os.path.isfile(oggpth):
        os.remove(oggpth)
    shell(['ffmpeg', '-i', wavpth, mp3pth])
    shell(['ffmpeg', '-i', wavpth, oggpth])
    try:
        assert os.path.isfile(mp3pth)
        assert os.path.isfile(oggpth)
        assert os.path.getsize(mp3pth) < os.path.getsize(wavpth)
        assert os.path.getsize(oggpth) < os.path.getsize(wavpth)
        print 'FFmpeg is working correctly.'
    except AssertionError:
        print ('%sWarning: the FFmpeg install does not appear to be able to'
            ' convert .wav files to .mp3 and/or .ogg formats.%s' % (
            ANSI_WARNING, ANSI_ENDC))
    if os.path.isfile(mp3pth):
        os.remove(mp3pth)
    if os.path.isfile(oggpth):
        os.remove(oggpth)


def install_m4():
    """Install m4, a bison dep, which is a foma dep::

        $ wget ftp://ftp.gnu.org/gnu/m4/m4-1.4.10.tar.gz
        $ tar -xvzf m4-1.4.10.tar.gz
        $ cd m4-1.4.10
        $ ./configure --prefix=/usr/local/m4
        $ make
        $ sudo make install

    """

    if which('m4'):
        print 'm4 is already installed.'
        return
    flush('Installing m4 ...')
    m4path = os.path.join(get_tmp_path(), 'm4-1.4.10.tar.gz')
    m4dirpath = os.path.join(get_tmp_path(), 'm4-1.4.10')
    fname, headers = urllib.urlretrieve(
        'ftp://ftp.gnu.org/gnu/m4/m4-1.4.10.tar.gz', m4path)
    if not os.path.isfile(m4path):
        print ('%sUnable to download m4. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    tar = tarfile.open(m4path, mode='r:gz')
    tar.extractall(path=get_tmp_path())
    tar.close()
    if not os.path.isdir(m4dirpath):
        print ('%sUnable to extract m4. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    logtext = ['./configure run in m4\n\n']
    stdout = shell(['./configure', '--prefix=/usr/local/m4'], m4dirpath)
    logtext.append(stdout)
    stdout = shell(['make'], m4dirpath)
    logtext.append('\n\nmake run in m4\n\n')
    logtext.append(stdout)
    stdout = shell(['sudo', 'make', 'install'], m4dirpath)
    logtext.append('\n\nsudo make install run in m4\n\n')
    logtext.append(stdout)
    log('install-m4.log', '\n'.join(logtext))
    if which('m4'):
        print 'Done.'
    else:
        print 'Failed.'


def install_bison():
    """Method::

        $ wget http://ftp.gnu.org/gnu/bison/bison-2.3.tar.gz
        $ tar -xvzf bison-2.3.tar.gz
        $ cd bison-2.3
        $ PATH=$PATH:/usr/local/m4/bin/
        $ ./configure --prefix=/usr/local/bison
        $ make
        $ sudo make install

    """

    if os.path.isdir('/usr/local/bison/'):
        print 'bison is already installed.'
        return
    flush('Installing bison ...')
    bisonpath = os.path.join(get_tmp_path(), 'bison-2.3.tar.gz')
    bisondirpath = os.path.join(get_tmp_path(), 'bison-2.3')
    fname, headers = urllib.urlretrieve(
        'http://ftp.gnu.org/gnu/bison/bison-2.3.tar.gz', bisonpath)
    if not os.path.isfile(bisonpath):
        print ('%sUnable to download bison. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    tar = tarfile.open(bisonpath, mode='r:gz')
    tar.extractall(path=get_tmp_path())
    tar.close()
    if not os.path.isdir(bisondirpath):
        print ('%sUnable to extract bison. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    os.environ["PATH"] += os.pathsep + '/usr/local/m4/bin/'
    logtext = ['./configure run in bison\n\n']
    stdout = shell(['./configure', '--prefix=/usr/local/bison'], bisondirpath)
    logtext.append(stdout)
    stdout = shell(['make'], bisondirpath)
    logtext.append('\n\n`make` run in bison\n\n')
    logtext.append(stdout)
    stdout = shell(['sudo', 'make', 'install'], bisondirpath)
    logtext.append('\n\n`sudo make install` run in bison\n\n')
    logtext.append(stdout)
    log('install-bison.log', '\n'.join(logtext))
    if os.path.isdir('/usr/local/bison/'):
        print 'Done.'
    else:
        print 'Failed.'


def install_flex():
    """sudo apt-get install flex

    """

    if which('flex'):
        print 'flex is already installed.'
        return
    flush('Installing flex ...')
    stdout = aptget(['flex'])
    log('install-flex.log', stdout)
    if which('flex'):
        print 'Done.'
    else:
        print 'Failed.'


def install_subversion():
    """sudo apt-get install subversion

    """

    if which('svn'):
        print 'subversion is already installed.'
        return
    flush('Installing subversion ...')
    stdout = aptget(['subversion'])
    log('install-subversion.log', stdout)
    if which('svn'):
        print 'Done.'
    else:
        print 'Failed.'


def install_foma():
    """Method::

        $ svn co http://foma.googlecode.com/svn/trunk/foma/
        $ cd foma
        $ PATH=$PATH:/usr/local/bison/bin/
        $ sudo apt-get install libreadline6 libreadline6-dev
        $ make
        $ sudo make install

    """

    if which('foma') and which('flookup'):
        print 'foma is already installed.'
        return
    if not which('svn'):
        print 'Subversion not installed; can\'t install foma. Aborting.'
        return
    flush('Installing foma ...')
    logtext = ['Downloading foma\n\n']
    stdout = shell(['svn', 'co', 'http://foma.googlecode.com/svn/trunk/foma/'],
        get_tmp_path())
    logtext.append(stdout)
    fomadir = os.path.join(get_tmp_path(), 'foma')
    if not os.path.isdir(fomadir):
        print ('%sFailed to download foma to %s. Aborting.%s' % (ANSI_FAIL, fomadir,
            ANSI_ENDC))
        return
    bisondir = '/usr/local/bison/bin/'
    if os.path.isdir(bisondir):
        os.environ["PATH"] += os.pathsep + bisondir
    else:
        print ('%sbison is not installed. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    stdout = aptget(['libreadline6', 'libreadline6-dev'])
    logtext.append('\n\nInstalling libreadline6 and libreadline6-dev\n\n')
    logtext.append(stdout)
    stdout = shell(['make'], fomadir)
    logtext.append('\n\nRunning `make` in foma\n\n')
    logtext.append(stdout)
    stdout = shell(['sudo', 'make', 'install'], fomadir)
    logtext.append('\n\nRunning `sudo make install` in foma\n\n')
    logtext.append(stdout)
    if which('foma') and which('flookup'):
        print 'Done.'
    else:
        print 'Failed.'


def install_mitlm():
    """Method::

        $ sudo apt-get install autoconf automake libtool gfortran
        $ wget https://mitlm.googlecode.com/files/mitlm-0.4.1.tar.gz
        $ tar -zxvf mitlm-0.4.1.tar.gz
        $ cd mitlm-0.4.1
        $ ./configure
        $ make
        $ sudo make install
        $ sudo ldconfig

    """

    if which('estimate-ngram') and which('evaluate-ngram'):
        print 'MITLM is already installed.'
        return
    flush('Installing MITLM ...')
    stdout = aptget(['g++', 'autoconf', 'automake', 'libtool', 'gfortran'])
    log('install-mitlm-libraries.log', stdout)
    mitlmpath = os.path.join(get_tmp_path(), 'mitlm-0.4.1.tar.gz')
    mitlmdirpath = os.path.join(get_tmp_path(), 'mitlm-0.4.1')
    fname, headers = urllib.urlretrieve(
        'https://mitlm.googlecode.com/files/mitlm-0.4.1.tar.gz', mitlmpath)
    if not os.path.isfile(mitlmpath):
        print ('%sUnable to download MITLM. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    tar = tarfile.open(mitlmpath, mode='r:gz')
    tar.extractall(path=get_tmp_path())
    tar.close()
    if not os.path.isdir(mitlmdirpath):
        print ('%sUnable to extract MITLM. Aborting.%s' % (ANSI_FAIL,
            ANSI_ENDC))
        return
    stdout = shell(['./configure'], mitlmdirpath)
    log('configure-mitlm.log', stdout)
    stdout = shell(['make'], mitlmdirpath)
    log('make-mitlm.log', stdout)
    stdout = shell(['sudo', 'make', 'install'], mitlmdirpath)
    log('sudo-make-install-mitlm.log', stdout)
    stdout = shell(['sudo', 'ldconfig'], mitlmdirpath)
    log('sudo-ldconfig-mitlm.log', stdout)
    if which('estimate-ngram') and which('evaluate-ngram'):
        print 'Done.'
    else:
        print ('MITLM was not installed correctly. Please see'
            ' https://code.google.com/p/mitlm/ for instructions on how to'
            ' install it on your system.')


def install_libmagic():
    """sudo apt-get install libmagic-dev

    TODO: test for success.

    """

    flush('Installing libmagic ...')
    stdout = aptget(['libmagic-dev'])
    log('install-libmagic.log', stdout)
    print 'Done.'


def install(params):
    """Install the OLD and all of its dependencies.

    Someday: install latex/xetex: `sudo apt-get install texlive-xetex`

    """

    print 'in install of installold'

    get_system_python_version()

    create_directory_safely(get_tmp_path())
    create_directory_safely(get_log_path())
    clear_log()
    clear_tmp()

    #sys.exit('IN INSTALL OF INSTALLOLD SYS EXIT')

    # Core dependencies: these must be installed in order for the OLD to be
    # minimally functional.
    aptgetupdate()
    install_easy_install()
    install_virtualenv()
    create_env(params)
    install_old(params)
    install_mysql_python(params)
    install_importlib(params)

    # Soft dependencies: failing to install these is ok, but the OLD won't be
    # fully functional unless all of them are installed.
    install_PIL(params)
    test_PIL(params)
    install_FFmpeg()
    test_FFmpeg()
    install_m4()
    install_bison()
    install_flex()
    install_subversion()
    install_foma()
    install_mitlm()
    install_libmagic()


def main():
    params = get_params()
    install(params)


if __name__ == '__main__':
    main()


