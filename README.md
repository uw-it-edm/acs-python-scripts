## Python Scripts to interact with Alfresco Repository

#### To run the scripts
* copy acs.yaml.example to acs.yaml
* enter your configuration values into acs.yaml
* `python ./acs.py`

#### To run tests 
* `pip install responses` 
* `python AcsClientTestCase.py`


## Migration
```
usage: migrate.py [-h] -i INPUT [--csv CSV] [--printToScreen] -o OUTPUT
                  [-n NUMBERTOPROCESS] -m CONTENTMODELDEFINITION -p PROFILE

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        The input .hda file
  --csv CSV             An optional csv output file
  --printToScreen       Print output xml to screen
  -o OUTPUT, --output OUTPUT
                        The output directory for xml files
  -n NUMBERTOPROCESS, --numberToProcess NUMBERTOPROCESS
                        The number of documents to process
  -m CONTENTMODELDEFINITION, --contentModelDefinition CONTENTMODELDEFINITION
                        The definition of the content model
  -p PROFILE, --profile PROFILE
                        The profile to load from the content model definition
```

example: `python ./migrate.py -i oracl_export.hda --contentModelDefinition=./content_models.yml --csv=./export.csv  -o ./acs_import -p PROFILE_1  --printToScreen -n 1
`