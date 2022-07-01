'''
__main__.py: main function for refoliate.

Copyright
---------

Copyright (c) 2022 by the California Institute of Technology.  This code
is open-source software released under a BSD-type license.  Please see the
file "LICENSE" for more information.
'''

import sys
if sys.version_info <= (3, 8):
    print('refoliate requires Python version 3.8 or higher,')
    print('but the current version of Python is ' +
          str(sys.version_info.major) + '.' + str(sys.version_info.minor) + '.')
    sys.exit(1)

from   collections import namedtuple
from   commonpy.file_utils import readable
from   commonpy.network_utils import net
import os
from   os import path
import plac
from   sidetrack import set_debug, log


# Internal data structures.
# .............................................................................

Record = namedtuple('Record', 'json type')


# Main program.
# .............................................................................

# For more info about how plac works see https://plac.readthedocs.io/en/latest/
@plac.annotations(
    version    = ('print version info and exit',                'flag',   'V'),
    debug      = ('log debug output to "OUT" ("-" is console)', 'option', '@'),
    source_dir = 'directory containing JSON files'
)

def main(version = False, debug = 'OUT', *source_dir):
    '''REstore FOLIo sAved insTance rEcords'''

    # Set up debug logging as soon as possible, if requested ------------------

    if debug != 'OUT':
        config_debug(debug)
    else:
        debug = False

    # Preprocess arguments and handle early exits -----------------------------

    if version:
        print_version_info()
        sys.exit()

    source_dir = source_dir[0] if source_dir else None
    if source_dir is None:
        alert('Need to be given a source directory containing JSON files.')
        sys.exit(1)
    if not readable(source_dir) or not path.isdir(source_dir):
        alert(f'Not a directory or not readable: {source_dir}')
        sys.exit(1)
    if not read_credentials():
        alert('Failed to get complete FOLIO credentials.')
        sys.exit(1)
    if not folio_accessible():
        alert('Unable to connect to FOLIO.')
        sys.exit(1)

    # Do the real work --------------------------------------------------------

    records = {}

    # Read all json files and stored them in a dict indexed by id.
    import glob
    import json
    for filename in glob.iglob(source_dir + '**/*.json', recursive = True):
        with open(filename) as fp:
            log('reading file ' + str(fp))
            data = json.load(fp)
            records[data['id']] = Record(json = data, type = record_type(data))
    inform(f'Read a total of {len(records)} JSON files')

    instances = {id_: rec for (id_, rec) in records.items()
                 if rec.type == 'instance'}




# Miscellaneous helper functions.
# .............................................................................

def config_debug(debug_arg):
    log(f'debug arg = {debug_arg}')
    set_debug(True, debug_arg)
    import faulthandler
    faulthandler.enable()
    if os.name != 'nt':                 # Can't use next part on Windows.
        import signal
        from boltons.debugutils import pdb_on_signal
        pdb_on_signal(signal.SIGUSR1)


def print_version_info():
    # Precaution: add parent dir in case user is running from our source dir.
    from os import path
    sys.path.append(path.join(path.dirname(path.abspath(__file__)), '..'))
    from refoliate import print_version
    print_version()


def read_credentials():
    log('reading credentials from settings file in ' + os.getcwd())
    import decouple
    try:
        url       = decouple.config('FOLIO_OKAPI_URL', default = None)
        token     = decouple.config('FOLIO_OKAPI_TOKEN', default = None)
        tenant_id = decouple.config('FOLIO_OKAPI_TENANT_ID', default = None)
    except Exception as ex:
        log('error reading settings file: ' + str(ex))
        return False

    if not all([url, tenant_id, token]):
        log('credentials are incomplete')
        return False

    os.environ['FOLIO_OKAPI_URL']       = url
    os.environ['FOLIO_OKAPI_TOKEN']     = token
    os.environ['FOLIO_OKAPI_TENANT_ID'] = tenant_id
    return True


def folio_accessible():
    url       = os.environ['FOLIO_OKAPI_URL']
    token     = os.environ['FOLIO_OKAPI_TOKEN']
    tenant_id = os.environ['FOLIO_OKAPI_TENANT_ID']

    from validators.url import url as valid_url
    if not valid_url(url):
        log('FOLIO_OKAPI_URL value is not a valid URL')
        return False
    try:
        log('testing if FOLIO credentials appear valid')
        headers = {
            "x-okapi-token": token,
            "x-okapi-tenant": tenant_id,
            "content-type": "application/json",
        }
        request_url = url + '/instance-statuses?limit=0'
        (resp, _) = net('get', request_url, headers = headers)
        return (resp and resp.status_code < 400)
    except Exception as ex:
        log('FOLIO credentials test failed with ' + str(ex))
        return False
    return True


def record_type(record_json):
    if 'barcode' in record_json:
        return 'item'
    elif 'holdingsItems' in record_json:
        return 'holdings'
    elif 'instanceTypeId' in record_json:
        return 'instance'
    else:
        warn('Unrecognized item type for ' + record_json['id'])


def print_text(text, color, borders = True):
    from rich import print
    import shutil
    if borders:
        from rich.panel import Panel
        from rich.style import Style
        terminal_width = shutil.get_terminal_size().columns or 79
        panel_width = terminal_width - 4
        width = panel_width if len(text) > panel_width else (len(text) + 4)
        print(Panel(text, style = Style.parse(color), width = width))
    else:
        from rich.console import Console
        from textwrap import wrap
        width = (shutil.get_terminal_size().columns - 2) or 78
        console = Console(width = width)
        console.print('\n'.join(wrap(text, width = width)), style = color)


def inform(text):
    print_text(text, 'green', borders = False)


def warn(text):
    print_text(text, 'orange3')


def alert(text):
    print_text(text, 'bold red')


# Main entry point.
# .............................................................................

# The following entry point definition is for the console_scripts keyword
# option to setuptools.  The entry point for console_scripts has to be a
# function that takes zero arguments.
def console_scripts_main():
    plac.call(main)


# The following allows users to invoke this using "python3 -m handprint".
if __name__ == '__main__':
    # Print help if the user supplied no command-line arguments.
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == 'help'):
        plac.call(main, ['-h'])
    else:
        plac.call(main)
