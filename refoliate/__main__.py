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

import os
from   os import path
import plac
from   sidetrack import set_debug, log


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
    if not path.exists(source_dir):
        alert(f'Directory does not exist: {source_dir}')
        sys.exit(1)
    if not path.isdir(source_dir):
        alert(f'Not a directory: {source_dir}')
        sys.exit(1)
    if not read_credentials():
        alert('Failed to get complete FOLIO credentials.')
        sys.exit(1)
    if not folio_accessible():
        alert('Unable to connect to FOLIO.')
        sys.exit(1)

    # Do the real work --------------------------------------------------------

    # Create dictionary of all records (in json format) indexed by their UUIDs.
    records = {}
    try:
        import glob
        import json
        for filename in glob.iglob(source_dir + '**/*.json', recursive = True):
            with open(filename) as fp:
                rec = json.load(fp)
                uuid = rec['id']
                records[uuid] = rec
                log(f'read {record_type(rec)} record {uuid} from file {filename}')
    except Exception as ex:
        alert('Encountered problem reading JSON files: ' + str(ex))
        sys.exit(1)
    inform(f'Read a total of {len(records)} JSON files')

    # Now we need to bundle together the records that belong together: items,
    # holding records, and instance records. We have to follow pointers from
    # items to holdings to instances.

    # build dict of instances, which has dict of holdings rec, which has list of items

    from collections import defaultdict
    done = set()
    holdings_items = defaultdict(list)     # list of items, keyed by holdings id
    instance_holdings = defaultdict(list)  # list of holdings, keyed by instance id

    for record in filter(lambda r: record_type(r) == 'item_record', records.values()):
        item_id = record['id']
        holdings_id = record['holdingsRecordId']
        holdings_items[holdings_id].append(record)
        done.add(item_id)
        log(f'added item {item_id} under holdings {holdings_id}')
    for record in filter(lambda r: record_type(r) == 'holdings_record', records.values()):
        holdings_id = record['id']
        instance_id = record['instanceId']
        instance_holdings[instance_id].append(record)
        done.add(holdings_id)
        log(f'added holdings {holdings_id} under instance {instance_id}')
    for record in filter(lambda r: record_type(r) == 'instance_record', records.values()):
        instance_id = record['id']
        if instance_id not in instance_holdings:
            log(f'found instance with no holdings or items: {instance_id}')
            instance_holdings[instance_id] = []
        done.add(instance_id)

    # Check: have we filed everything we were given?
    if set(records.keys()) - done != set():
        alert('Failed to account for all records given.')
        sys.exit(1)

    # Submit things to Folio top-down:
    try:
        for instance_id in instance_holdings.keys():
            if folio_exists('instance', instance_id):
                warn(f'Instance UUID {instance_id} already exists in FOLIO')
            else:
                folio_new('instance', records[instance_id])
            for holdings in instance_holdings[instance_id]:
                holdings_id = holdings['id']
                if folio_exists('holdings', holdings_id):
                    warn(f'Holdings UUID {holdings_id} already exists in FOLIO')
                else:
                    folio_new('holdings', records[holdings_id])
                for item in holdings_items[holdings_id]:
                    item_id = item['id']
                    if folio_exists('item', item_id):
                        warn(f'Item UUID {item_id} already exists in FOLIO')
                    else:
                        folio_new('item', records[item_id])
    except Exception as ex:
        log('exception: ' + str(ex))
        breakpoint()


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
        from commonpy.network_utils import net
        request_url = url + '/instance-statuses?limit=0'
        (resp, _) = net('get', request_url, headers = headers)
        accessible = (resp and resp.status_code < 400)
        log(f'FOLIO {"is" if accessible else "is not"} accessible')
        return accessible
    except Exception as ex:
        log('FOLIO credentials test failed with ' + str(ex))
        return False
    return True


_ENDPOINT = {
    'item': '/item-storage/items',
    'holdings': '/holdings-storage/holdings',
    'instance': '/instance-storage/instances'
}

def folio_exists(record_type, record_id):
    url       = os.environ['FOLIO_OKAPI_URL']
    token     = os.environ['FOLIO_OKAPI_TOKEN']
    tenant_id = os.environ['FOLIO_OKAPI_TENANT_ID']

    headers = {
        "x-okapi-token": token,
        "x-okapi-tenant": tenant_id,
        "content-type": "application/json",
    }

    from commonpy.network_utils import net
    request_url = url + _ENDPOINT[record_type] + '/' + record_id
    (resp, _) = net('get', request_url, headers = headers)
    if resp and resp.status_code > 500:
        alert(f'FOLIO returned status code {resp.status_code} -- quitting.')
        sys.exit(1)
    exists = (resp and resp.status_code < 400)
    log(f'{record_type} record {record_id} {"exists" if exists else "does not exist"}')
    return exists


def folio_new(record_type, record):
    url       = os.environ['FOLIO_OKAPI_URL']
    token     = os.environ['FOLIO_OKAPI_TOKEN']
    tenant_id = os.environ['FOLIO_OKAPI_TENANT_ID']

    headers = {
        "x-okapi-token": token,
        "x-okapi-tenant": tenant_id,
        "content-type": "application/json",
    }

    record_id = record['id']
    inform(f'Creating new [bold]{record_type}[/] record with UUID {record_id}')
    request_url = url + _ENDPOINT[record_type]
    import json
    json_string = json.dumps(record)
    from commonpy.network_utils import net
    (resp, error) = net('post', request_url, headers = headers, data = json_string)
    if error or not resp or resp.status_code > 500:
        alert(f'FOLIO returned a server error code {resp.status_code}; aborting.')
        raise error
    succeeded = resp.status_code in [201, 204]
    if not succeeded:
        alert(f'Creation operation failed with code {resp.status_code}; aborting.')
        raise RuntimeError(f'Record creation failed with code {resp.status_code}')

    # Folio returns the newly created record. check if id is same.
    new_rec = json.loads(resp.text)
    if new_rec['id'] != record_id:
        alert(f'Newly created record does not have the same UUID; aborting.')
        raise RuntimeError(f'FOLIO did not create record with same UUID')
    return True


def record_type(record_json):
    if 'barcode' in record_json:
        return 'item_record'
    elif 'holdingsItems' in record_json:
        return 'holdings_record'
    elif 'instanceTypeId' in record_json:
        return 'instance_record'
    else:
        warn('Unrecognized item type for ' + record_json['id'])
        # FIXME need return someting


def print_text(text, color, borders = False):
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
    log('[inform] ' + text)
    print_text(text, 'green')


def warn(text):
    log('[warn] ' + text)
    print_text(text, 'orange3')


def alert(text):
    log('[alert] ' + text)
    print_text(text, 'bold red', borders = True)


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
