## Python Scripts to interact with Alfresco Repository
[![Build Status](https://travis-ci.org/uw-it-edm/acs-python-scripts.svg?branch=develop)](https://travis-ci.org/uw-it-edm/acs-python-scripts)
[![Coverage Status](https://coveralls.io/repos/github/uw-it-edm/acs-python-scripts/badge.svg?branch=develop)](https://coveralls.io/github/uw-it-edm/acs-python-scripts?branch=develop)

## Run script 
This python script requires python2 and a few dependencies. 
Easiest way to run is by creating a python virtual environment : 

1. If you haven't installed it before, run `pip2 install virtualenv`
2. Activate the venv : `virtualenv --python=/usr/local/bin/python2 venv`
3. Activate the virutal environment : `source venv/bin/activate` 
4. Install dependencies : `pip install -r requirements.txt`
5. Execute one of the scripts : `python acs.py`

## Create Site

#### To create a new site:
1. Create `acs.yml` and `rules.yml` files (See the corresponding example files)
2. `python ./acs.py`

#### To run tests 
* `pip install responses` 
* `python AcsClientTestCase.py`


## Migration
```
usage: migrate.py [-h] -i INPUT [--csv CSV] [--printToScreen] -o OUTPUT
                  [-n NUMBERTOPROCESS] [-m CONTENTMODELDEFINITION] -p PROFILE
                  [-s SAMPLEFILESDIR] [--seqStart SEQSTART] [--seqEnd SEQEND]
                  [-c COUNTFILE] [--validate]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        The input directory
  --csv CSV             An optional csv file for output of all the migrated
                        data
  --printToScreen       Print output xml to screen
  -o OUTPUT, --output OUTPUT
                        The output directory for xml files
  -n NUMBERTOPROCESS, --numberToProcess NUMBERTOPROCESS
                        The number of documents to process per hda file, defaults to all
  -m CONTENTMODELDEFINITION, --contentModelDefinition CONTENTMODELDEFINITION
                        The definition of the content model
  -p PROFILE, --profile PROFILE
                        The profile to load from the content model definition
  -s SAMPLEFILESDIR, --sampleFilesDir SAMPLEFILESDIR
                        The sample files directory, when associating fake content with the data
  --seqStart SEQ1       Starting sequence number
  --seqEnd SEQ2         Ending sequence number
  -c COUNTFILE, --countFile COUNTFILE
                        name_field_value_count file to use for sequence 1
  --validate            Validate data based on field type, and print to screen

```

examples
 * one hda file: `python ./migrate.py -i ./hda_files/ --contentModelDefinition=./content_models.yml --csv=./export.csv  -o ./acs_import -p PROFILE_1  --seqStart 1 --seqEnd 1`
 * all hda files in directory: `python ./migrate.py -i ./hda_files/ --contentModelDefinition=./content_models.yml --csv=./export.csv  -o ./acs_import -p PROFILE_1`
 * all hda files in directory, replacing the content with sample files: `python ./migrate.py -i ./hda_files/ --contentModelDefinition=./content_models.yml --csv=./export.csv  -o ./acs_import -p PROFILE_1 -s ./sample-files`
 
