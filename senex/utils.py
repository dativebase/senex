import platform
import os
import sys
from subprocess import Popen, PIPE, STDOUT
from .installold import (
    which,
    shell,
    mysql_python_installed,
    old_installed,
    importlib_installed,
    pil_installed,
    get_python_path
    )


def get_old_version(params):
    """Return the version of the installed OLD, if possible.

    """

    stmts = ('import onlinelinguisticdatabase;'
        'print getattr(onlinelinguisticdatabase, "__version__", "")')
    stdout = shell([get_python_path(params), '-c', stmts])
    if stdout.strip():
        return stdout.strip()
    return ''


def get_easy_install_version(params):
    stdout = shell(['easy_install', '--version']).decode('utf-8')
    if stdout.strip():
        try:
            return stdout.strip().split(' ')[1]
        except:
            return ''
    return ''


def get_virtualenv_version(params):
    stdout = shell(['virtualenv', '--version']).decode('utf-8')
    if stdout.strip():
        return stdout.strip()
    return ''


def get_mysql_python_version(params):
    stmts = 'import MySQLdb; print MySQLdb.__version__'
    stdout = shell([get_python_path(params), '-c', stmts])
    if stdout.strip():
        return stdout.strip()
    return ''


def get_pil_version(params):
    stmts = 'import Image; print Image.VERSION'
    stdout = shell([get_python_path(params), '-c', stmts])
    if stdout.strip():
        return stdout.strip()
    return ''


def get_platform():
    _platform = platform.system()
    return {'Darwin': 'Mac OS X'}.get(_platform, _platform)


def get_platform_version():
    if platform.system() == 'Darwin':
        return platform.mac_ver()[0]
    else:
        return platform.release()


def apache_installed():
    if platform.system() == 'Darwin':
        return bool(which('apachectl'))
    else:
        return bool(which('apache2'))


def get_apache_version():
    stdout = shell(['apachectl', '-v'])
    if stdout.strip():
        try:
            resp = stdout.strip()
            return resp.split('\n')[0].split(' ')[2].replace('Apache/', '')
        except:
            return ''
    return ''


def get_foma_version():
    stdout = shell(['foma', '-v'])
    if stdout.strip():
        try:
            return stdout.replace('foma', '').strip()
        except:
            return ''
    return ''


def get_mitlm_version():
    stdout = shell(['estimate-ngram', '-h'])
    if stdout.strip():
        try:
            for line in stdout.split('\n'):
                if 'MIT Language Modeling Toolkit' in line:
                    return filter(None, line.split(' '))[-2].strip()
            return ''
        except:
            return ''
    return ''


def get_ffmpeg_version():
    stdout = shell(['ffmpeg', '-version'])
    if stdout.strip():
        try:
            return stdout.split('\n')[0].split(' ')[2]
        except:
            return ''
    return ''


def libmagic_installed():
    return bool(shell(['man', 'libmagic']))


def get_server():
    return {
        'os': get_platform(),
        'os_version': get_platform_version(),
        'disk_space_available': None,
        'ram': None
        }


def get_python_version():
    """Check the Python version. It should be 2.6 or 2.7.

    """

    return sys.version.split(' ')[0]


def get_dependencies(params):

    old_installed_resp = old_installed(params)
    old_version = ''
    if old_installed_resp:
        old_version = get_old_version(params)

    easy_install_installed = bool(which('easy_install'))
    easy_install_version = ''
    if easy_install_installed:
        easy_install_version = get_easy_install_version(params)

    virtualenv_installed = bool(which('virtualenv'))
    virtualenv_version = ''
    if virtualenv_installed:
        virtualenv_version = get_virtualenv_version(params)

    mysql_python_installed_resp = mysql_python_installed(params)
    mysql_python_version = ''
    if mysql_python_installed_resp:
        mysql_python_version = get_mysql_python_version(params)

    apache_installed_resp = apache_installed()
    apache_version = ''
    if apache_installed_resp:
        apache_version = get_apache_version()

    foma_installed = bool(which('foma') and which('flookup'))
    foma_version = ''
    if foma_installed:
        foma_version = get_foma_version()

    mitlm_installed = bool(which('estimate-ngram') and which('evaluate-ngram'))
    mitlm_version = ''
    if mitlm_installed:
        mitlm_version = get_mitlm_version()

    ffmpeg_installed = bool(which('ffmpeg'))
    ffmpeg_version = ''
    if ffmpeg_installed:
        ffmpeg_version = get_ffmpeg_version()

    pil_installed_resp = pil_installed(params)
    pil_version = ''
    if pil_installed_resp:
        pil_version = get_pil_version(params)

    return [
        {
            'name': 'Python',
            'installed': True,
            'version': get_python_version()
        },

        {
            'name': 'OLD',
            'installed': old_installed_resp,
            'version': old_version
        },

        {
            'name': 'easy_install',
            'installed': easy_install_installed,
            'version': easy_install_version
        },

        {
            'name': 'virtualenv',
            'installed': virtualenv_installed,
            'version': virtualenv_version
        },

        {
            'name': 'MySQL-python',
            'installed': mysql_python_installed_resp,
            'version': mysql_python_version
        },

        {
            'name': 'importlib',
            'installed': importlib_installed(params),
            'version': None
        },

        {
            'name': 'Apache',
            'installed': apache_installed_resp,
            'version': apache_version
        },

        {
            'name': 'foma',
            'installed': foma_installed,
            'version': foma_version
        },

        {
            'name': 'MITLM',
            'installed': mitlm_installed,
            'version': mitlm_version
        },

        {
            'name': 'Ffmpeg',
            'installed': ffmpeg_installed,
            'version': ffmpeg_version
        },

        {
            'name': 'LaTeX',
            'installed': bool(which('pdflatex') and which('xelatex')),
            'version': None
        },

        {
            'name': 'PIL',
            'installed': pil_installed_resp,
            'version': pil_version
        },

        {
            'name': 'libmagic',
            'installed': libmagic_installed(),
            'version': None
        }
    ]

