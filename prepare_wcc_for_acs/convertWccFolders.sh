#!/usr/bin/env bash


declare -r ORIGIN_FOLDER=$1
declare -r OUTPUT_FOLDER=$2
declare -r PROFILE=$3


if [[ ! -d "$ORIGIN_FOLDER" ]]; then
    echo "Argument 1 (ORIGIN_FOLDER) should be the path of an existing directory" 1>&2
    echo "Usage : ./convertWccFolders.sh /origin/folder /output/folder profile" 1>&2
    exit 1
fi

if [[ ! -d "$OUTPUT_FOLDER" ]]; then
    echo "Argument 2 (OUTPUT_FOLDER) should be the path of an existing directory" 1>&2
    echo "Usage : ./convertWccFolders.sh /origin/folder /output/folder profile" 1>&2
    exit 2
fi

if [[ -z "$PROFILE" ]]; then
    echo "Argument 3 (PROFILE) should be the name of the profile you want to use" 1>&2
    echo "Usage : ./convertWccFolders.sh /origin/folder /output/folder profile" 1>&2
    exit 3
fi

if [[ ! -f "../content_models.yml" ]]; then
    echo "content_models.yml should be present in parent folder" 1>&2
    echo "Usage : ./convertWccFolders.sh /origin/folder /output/folder profile" 1>&2
    exit 4
fi

echo
read -p "This script is going to delete everythin inside $OUTPUT_FOLDER.
Are you sure? " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1 # handle exits from shell or function but don't exit interactive shell
fi

rm -rf $OUTPUT_FOLDER/*

find $ORIGIN_FOLDER -name "*~*.hda" | while read hdaFile; do
    echo "$hdaFile"
    FOLDER_NUMBER=`echo "$hdaFile" | sed 's/.*~\(.*\).hda/\1/'`
    echo "$FOLDER_NUMBER"
    
    mkdir $OUTPUT_FOLDER/$FOLDER_NUMBER
    
    ACTUAL_ORIGIN_FOLDER=$ORIGIN_FOLDER/$FOLDER_NUMBER
    ACTUAL_OUTPUT_FOLDER=$OUTPUT_FOLDER/$FOLDER_NUMBER
    
    python2 ../migrate.py -i  $hdaFile --contentModelDefinition=../content_models.yml --csv=./export-$(date +%s).csv -o $ACTUAL_OUTPUT_FOLDER -p $PROFILE --validate
    
    find $ACTUAL_ORIGIN_FOLDER -type f -exec cp -i {} $ACTUAL_OUTPUT_FOLDER \;
done


