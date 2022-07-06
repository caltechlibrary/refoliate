# Refoliate

REstore FOLIo sAved insTance rEcords.

[![License](https://img.shields.io/badge/License-BSD--like-lightgrey.svg?style=flat-square)](https://github.com/caltechlibrary/refoliate/LICENSE)
[![Latest release](https://img.shields.io/github/v/release/caltechlibrary/refoliate.svg?style=flat-square&color=b44e88)](https://github.com/caltechlibrary/refoliate/releases)


## Table of contents

* [Introduction](#introduction)
* [Installation](#installation)
* [Usage](#usage)
* [Known issues and limitations](#known-issues-and-limitations)
* [Getting help](#getting-help)
* [Contributing](#contributing)
* [License](#license)
* [Acknowledgments](#authors-and-acknowledgments)


## Introduction

This is a command-line program that will take a folder of JSON files (assumed to be instance, holdings and item records previously downloaded from FOLIO) and (re)creates them in FOLIO via the API.


## Usage

```
REstore FOLIo sAved insTance rEcords.

This program takes a directory of JSON files previously downloaded from FOLIO
by a program such as Foliage.  The files are assumed to represent instance,
holdings, and item records that have been deleted from FOLIO. This program
proceeds to put the records back into FOLIO as-is, using the same UUID's
and all other fields.

If given the argument --continue, then errors involving the inability to
create a record (e.g., due to the record already existing in FOLIO) will make
this program continue execution; otherwise, by default, this program will
stop at the first error.

If given the -@ argument (/@ on Windows), this program will output a detailed
trace of what it is doing.  The debug trace will be sent to the given
destination, which can be '-' to indicate console output, or a file path to
send the output to a file.

If given the -V option (/V on Windows), this program will print the version
and other information, and exit without doing anything else.

Command-line arguments summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

positional arguments:
  source_dir           directory containing JSON files

options:
  -h, --help           show this help message and exit
  -c, --continue       continue, don't stop, if an error occurs
  -V, --version        print version info and exit
  -@ OUT, --debug OUT  log debug output to "OUT" ("-" is console)
```


## Known issues and limitations

... Forthcoming ...


## Getting help

... Forthcoming ...


## Contributing

... Forthcoming ...


## License

Software produced by the Caltech Library is Copyright © 2022 California Institute of Technology.  This software is freely distributed under a BSD-style license.  Please see the [LICENSE](LICENSE) file for more information.


## Acknowledgments

This work was funded by the California Institute of Technology Library.

<div align="center">
  <br>
  <a href="https://www.caltech.edu">
    <img width="100" height="100" src="https://raw.githubusercontent.com/caltechlibrary/refoliate/main/.graphics/caltech-round.png">
  </a>
</div>
