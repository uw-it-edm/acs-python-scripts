#!/usr/bin/python2.7
# start bulk import, monitor status, and wait for import to complete.
# acs-bulk-import.yml - define import directory and target path
# The time for bulk import depends on the amount of data to be imported.

import sys 
import time
import argparse
import logging
import util
from AcsClient import AcsClient

#############################################
# get commandline arguments
def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf', default='acs.yml', help='conf file')
    parser.add_argument('-b', '--biconf', default='acs-bulk-import.yml', help='bulk import conf file')
    parser.add_argument('-s', '--stage', choices=['dev', 'local', 'test', 'prod'], default='dev')
    return parser.parse_args()

#############################################
def startBulkImport(acsClient, conf):
    # start bulk import
    imports = conf
    if imports:
        for imp in imports:
            sourceDirectoryBase = imp['sourceDirectoryBase']
            sourceDirectories = imp['sourceDirectories']
            targetPath = imp['targetPath']
            for srcdir in sourceDirectories:
                sourceDirectory = sourceDirectoryBase + '/' + srcdir
                logging.info('Uploading content from ' + sourceDirectory + ' to ' + targetPath)
                acsClient.startBulkImport(sourceDirectory, targetPath)

                # alfresco allow one bulk import at a time, wait for bulk load to complete
                status = acsClient.getBulkImportStatus()
                while status['currentStatus'].lower() != 'idle':
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    time.sleep(1)
                    status = acsClient.getBulkImportStatus()
                print("")  # new line

                if status['lastResult'].lower() == 'succeeded':
                    logging.info('Uploaded content from ' + sourceDirectory + ' to ' + targetPath)
                else:
                    logging.info('Failed to upload content from ' + sourceDirectory + ' to ' + targetPath)

#############################################
# main
def main():
    # config logging
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO
                        )
    logging.info('Start ' + sys.argv[0])
    args = getArgs()
    acsClient = AcsClient.fromConfig(args.conf, args.stage)

    # load bulk import config file
    biconf = util.getConfig(args.biconf)

    startBulkImport(acsClient, biconf)

    logging.info('End ' + sys.argv[0])

#############################################
if __name__ == "__main__":
    main()