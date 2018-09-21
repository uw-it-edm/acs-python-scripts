#!/usr/bin/python
# Refresh Alfresco Repository and Search Index for dev environment.
# WARNING: This is a powerful tool and it has the potential to do
# serious damage if it is used against a prod environment by mistake.
# I included a few safety valves but needed to strike a balance
# between safety and usability. 
#
# Python packages required:
# * pip install boto3  (for connecting to S3 to empty S3 bucket)
# * pip install fabric (for running commands on repo and indexer servers remotely)
#
# Configuration files
# * acs-refresh-dev.yml - repo and index hosts, admin group, import directories etc.
#
# It takes several minutes to refresh the repo, without bulk import.
# It takes about 3 minutes for the repo to start the first time.
# The time for bulk import depends on the amount of data to be imported.

import argparse
import logging

import sys 
import time
import boto3
import getpass
from fabric import Connection, Config

import util

#############################################
def clear_indexes(connection):
    logging.info('Deleting ACS indexes')
    connection.sudo('rm -rf /data/solr/indexes/alfresco')
    connection.sudo('rm -rf /data/solr/indexes/archive')
    connection.sudo('rm -rf /var/solr/contentstore')
    connection.sudo('rm -rf /var/solr/data/alfrescoModels')
    logging.info('Deleted indexes')

#############################################
# empty S3 bucket
def empty_s3_bucket(bucketName):
    logging.info('Emptying S3 bucket ' + bucketName)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketName)
    objs = bucket.objects.all()
    objs.delete()
    logging.info('Emptied S3 bucket ' + bucketName)

#############################################
def start_indexer(connection):
    logging.info('Startting ACS indexer')
    connection.sudo('service tomcat-alfresco start')
    connection.sudo('service solr start')
    logging.info('Started ACS indexer')
#############################################
def start_repo(connection):
    logging.info('Startting ACS Repo, waiting 3 minutes for server to start...')
    connection.sudo('service tomcat-alfresco start')
    # wait 3 minutes for server to come up.
    for i in range(180):
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(1)
    print("")  # new line
    logging.info('Startting ACS Share')
    connection.sudo('service tomcat-share start')
    logging.info('Started ACS Repo')
#############################################
def stop_indexer(connection):
    logging.info('Stopping ACS indexer')
    connection.sudo('service solr stop')
    connection.sudo('service tomcat-alfresco stop')
    connection.sudo('rm -rf /data/acs/cachedcontent')
    logging.info('Stopped ACS indexer')
    
#############################################
def stop_repo(connection):
    logging.info('Stopping ACS repo')
    connection.sudo('service tomcat-share stop')
    connection.sudo('service tomcat-alfresco stop')
    connection.sudo('rm -rf /data/acs/cachedcontent')
    logging.info('Stopped ACS repo')
    
#############################################
# confirm dev env
def sanityCheck(conf):
    # check for s3 bucket name, host names to confirm dev env. 
    bucketName = conf['s3bucket']
    if '-dev-' not in bucketName: 
        logging.error('S3 bucket, ' + bucketName + ' has no "-dev-". Abort execution.')
        exit(1)

    repoHost = conf['repoHost']
    if not repoHost.startswith('10.100'):
        logging.error('repo host, ' + repoHost+ ' does not start with "10.100". Abort execution.')
        exit(1)

    indexerHost = conf['indexerHost']
    if not indexerHost.startswith('10.100'):
        logging.error('indexer host, ' + indexerHost+ ' does not start with "10.100". Abort execution.')
        exit(1)
#############################################
# main
def main():
    # config logging
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO
                        )
    logging.info('start ' + sys.argv[0])

    # load refresh config file - hardcode config file name for now 
    conf = util.getConfig('acs-refresh-dev.yml')
    sanityCheck(conf)

    bucketName = conf['s3bucket']
    print('WARNING: drop all ACS tables, empty S3 bucket ' + bucketName + ', and delete existing indexes.') 
    answer = raw_input('Type "yes" to continue and any other key to exit: ')

    if answer != 'yes':
        sys.exit()

    sudoPass = getpass.getpass("What's your sudo password?")
    pwConfig = Config(overrides={'sudo': {'password': sudoPass}})
    repoHost = Connection(conf['repoHost'], config=pwConfig)
    indexerHost = Connection(conf['indexerHost'], config=pwConfig)
    stop_indexer(indexerHost)
    clear_indexes(indexerHost)
    stop_repo(repoHost)
    repoHost.run('cd /data/acs/python-scripts; python acs-drop-acs-tables.py DROP-ACS-TABLES')
    empty_s3_bucket(bucketName)
    start_repo(repoHost)
    start_indexer(indexerHost)
    repoHost.run('cd /data/acs/python-scripts; python acs.py')
    repoHost.run('cd /data/acs/python-scripts; python acs-bulk-import.py')

    logging.info('end ' + sys.argv[0])

#############################################
if __name__ == "__main__":
    main()
