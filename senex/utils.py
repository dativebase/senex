import platform
import os
import sys
from subprocess import Popen, PIPE, STDOUT
from uuid import uuid4
from .installold import (
    which,
    shell,
    mysql_python_installed,
    old_installed,
    importlib_installed,
    pil_installed,
    get_python_path
    )


def generate_salt():
    return unicode(uuid4().hex)


def validate_mysql_credentials(params):
    """Check if we can actually access MySQL with the provided credentials;
    also check if we have sufficient privileges to do what we need to do.

    WARNING: requiring that the output to 'SHOW GRANTS;' contain "GRANT ALL
    PRIVILEGES ON *.* TO '<mysql-user>'" might be too stringent.

    """

    if not params.get('mysql_user') or not params.get('mysql_pwd'):
        return ('A MySQL username and password must be provided in order to'
            ' create and manage OLDs.')
    mysql_show_grants = Popen(['mysql', '-u', params['mysql_user'],
        '-p%s' % params['mysql_pwd'], '-e', 'show grants;'], stdout=PIPE,
        stderr=STDOUT)
    stdout, stderr = mysql_show_grants.communicate()
    if 'Access denied' in stdout:
        return ('Sorry, we cannot access MySQL with user %s and the provided'
            ' password.' % params['mysql_user'])
    elif "GRANT ALL PRIVILEGES ON *.* TO '%s'" % params['mysql_user'] not in stdout:
        return ('Sorry, user %s does not have sufficient MySQL privileges to'
            ' build an OLD.' % params['mysql_user'])
    else:
        return None


def get_old_version(params):
    """Return the version of the installed OLD, if possible.

    """

    stmts = ('import onlinelinguisticdatabase;'
        'print getattr(onlinelinguisticdatabase, "__version__", "")')
    python_path = get_python_path(params)
    if os.path.isfile(python_path):
        stdout = shell([python_path, '-c', stmts])
        if stdout.strip():
            return stdout.strip()
    return ''


def get_mysql_installed():
    stdout = shell(['mysql', '-V'])
    if 'Distrib' in stdout.strip():
        return True
    return False


def get_mysql_version():
    stdout = shell(['mysql', '-V'])
    if 'Distrib' in stdout.strip():
        try:
            return stdout.split()[4].replace(',', '')
        except:
            return ''
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
    python_path = get_python_path(params)
    if os.path.isfile(python_path):
        stdout = shell([python_path, '-c', stmts])
        if stdout.strip():
            return stdout.strip()
    return ''


def get_pil_version(params):
    stmts = 'import Image; print Image.VERSION'
    python_path = get_python_path(params)
    if os.path.isfile(python_path):
        stdout = shell([python_path, '-c', stmts])
        if stdout.strip():
            return stdout.strip()
    return ''


def get_os_and_version():
    _platform = platform.system()
    os = 'unknown'
    os_version = 'unknown'
    if _platform == 'Darwin':
        os = 'Mac OS X'
        os_version = platform.mac_ver()[0]
    if _platform == 'Linux':
        dist = platform.dist()
        os = '%s Linux' % dist[0]
        os_version = dist[1]
    return os, os_version


def get_available_memory():
    system = platform.system()
    if system == 'Darwin':
        stdout = shell(['sysctl', 'hw.memsize'])
        if stdout.strip():
            try:
                resp = stdout.strip()
                return pretty_print_bytes(int(resp.split()[1]))
            except:
                return ''
        return ''
    elif system == 'Linux':
        stdout = shell(['free', '-b'])
        if stdout.strip():
            try:
                resp = stdout.strip()
                for line in resp.split('\n'):
                    if line.startswith('Swap:'):
                        return pretty_print_bytes(int(line.split()[1]))
            except:
                return ''
        return ''
    else:
        return ''


def pretty_print_bytes(num_bytes):
    """Print an integer byte count to human-readable form.
    """
    if num_bytes is None:
        return 'File size unavailable.'
    KiB = 1024
    MiB = KiB * KiB
    GiB = KiB * MiB
    TiB = KiB * GiB
    PiB = KiB * TiB
    EiB = KiB * PiB
    ZiB = KiB * EiB
    YiB = KiB * ZiB
    if num_bytes > YiB:
        return '%.3g YiB' % (num_bytes / YiB)
    elif num_bytes > ZiB:
        return '%.3g ZiB' % (num_bytes / ZiB)
    elif num_bytes > EiB:
        return '%.3g EiB' % (num_bytes / EiB)
    elif num_bytes > PiB:
        return '%.3g PiB' % (num_bytes / PiB)
    elif num_bytes > TiB:
        return '%.3g TiB' % (num_bytes / TiB)
    elif num_bytes > GiB:
        return '%.3g GiB' % (num_bytes / GiB)
    elif num_bytes > MiB:
        return '%.3g MiB' % (num_bytes / MiB)
    elif num_bytes > KiB:
        return '%.3g KiB' % (num_bytes / KiB)


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
    os, os_version = get_os_and_version()
    return {
        'os': os,
        'os_version': os_version,
        # 'disk_space_available': None,
        'ram': get_available_memory()
        }


def get_python_version():
    """Check the Python version. It should be 2.6 or 2.7.

    """

    return sys.version.split(' ')[0]


def get_dependencies(params):
    """Inspect the server via various subprocess calls and introspection of the
    Python installation in our OLD virtual environment and return an array of
    objects representing our OLD dependencies and whether they are installed,
    including the version numbers, if possible, of installed dependencies.

    """

    mysql_installed = get_mysql_installed()
    mysql_version = ''
    if mysql_installed:
        mysql_version = get_mysql_version()

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
            'name': 'Apache',
            'installed': apache_installed_resp,
            'version': apache_version
        },

        {
            'name': 'MySQL',
            'installed': mysql_installed,
            'version': mysql_version
        },

        {
            'name': 'MySQL-python',
            'installed': mysql_python_installed_resp,
            'version': mysql_python_version
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
            'name': 'importlib',
            'installed': importlib_installed(params),
            'version': None
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

