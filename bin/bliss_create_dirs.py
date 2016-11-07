#!/usr/bin/env python

'''
Usage:
    bliss_create_dirs.py [options]

Arguments:
    -c FILE, --config=<file>    YAML config file that contains a dictionary
                                of paths. Defaults to BLISS_CONFIG.gds_paths.

                                i.e.
                                    path1: /path/to/path1
                                    path2: /path/to/path2
                                    path3: /path/to/path3

    -s DAYS, --slack=<days> Number of slack days in advance of today's
                            date to create the directory structure.
                            Dependent on DDD or YYYY being specified in
                            configuration.

                            i.e. If today is 09/01/2016, slack=1, then this
                            script will create directories for 09/02/2016.
                            [default: 1]

    -l LENGTH, --length=<days>  Number of days of directories to create
                                [default: 1]

    -v, --verbose   Verbose output [default: False]

Description:

  BLISS Create Directory Structure

  Create daily directories for the GDS with paths specified via a YAML
  configuration file. Defaults to 'gds_paths' in BLISS_CONFIG .

  For example,

      path1: path/to/create/1
      path2: path/to/create/2
      path3: path/to/create/3

'''

from docopt import docopt
import bliss
import yaml
import sys

# One day in seconds
SECONDS=86400

if __name__ == '__main__':
    arguments = docopt(__doc__)

    paths = None
    config = arguments.pop('--config')

    if config:
        with open(config, 'rb') as f:
            paths = yaml.load(f)

    slack = int(arguments.pop('--slack'))

    length = int(arguments.pop('--length'))

    verbose = arguments.pop('--verbose')

try:

    start = slack
    end = slack + length

    print start
    print end

    for d in range(start, end):
        utc = bliss.dmc.getUTCDatetimeDOY(d * SECONDS)

        doy = utc.split(':')
        bliss.log.info('Creating GDS directories for %s:%s' % (doy[0], doy[1]))

        bliss.cm.createDirStruct(paths, utc, verbose)

except KeyboardInterrupt:
    bliss.log.info('Received Ctrl-C.  Stopping BLISS Create Directories.')

except Exception as e:
    print e
    bliss.log.error('BLISS Create Directories error: %s' % str(e))