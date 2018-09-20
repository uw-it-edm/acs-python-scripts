#!/usr/bin/python
# Refresh Alfresco Repository and Search Index for dev environment.
# WARNING: This is a powerful tool and it has the potential to do
# serious damage if it is used against a prod environment by mistake.
# I included a few safety valves but needed to strike a balance
# between safety and usability. 
#
# Python packages required:
# * pip install boto3  (for connecting to S3 to empty S3 bucket)
# * pip install mysql-connector-python (for connecting to DB to drop repository tables)
# * pip install fabric (for running commands on repo and indexer servers remotely)
#
# Configuration files
# * acs-refresh-dev.yml - repo and index hosts, admin group, import directories etc.
# * acs.yml - ACS site configurations, used by acs.py
# * rules.yml - rule configurations, used by acs.py
# * filePlan.yml - file plan configurations, used by acs.py
# * mysql.cnf - mysql configuration to connect to repo DB.
#
# Additional set up
# * Tunnel to RDS and ACS repo
#   ssh -L3306:dbhost:3306 -L8070:localhost:8070 acs_repo_host
# where dbhost is the RDS cluster endpoint
# * Add the following to /etc/hosts to work around SSL host verification
#  127.0.0.1 <connonical name (CN) of repo certificate>
# * sudo privilege is required on the repo and index hosts
#
# It takes several minutes to refresh the repo, without bulk import.
# It takes about 3 minutes for the repo to start the first time.
# The time for bulk import depends on the amount of data to be imported.

import argparse
import json
import logging
from os.path import isfile

import yaml

import sys 
import time
import boto3
import getpass
import mysql.connector
from fabric import Connection, Config

from AcsClient import AcsClient
import acs

#############################################
def clear_indexes(connection):
    logging.info('Deleting ACS indexes')
    connection.sudo('rm -rf /data/solr/indexes/alfresco')
    connection.sudo('rm -rf /data/solr/indexes/archive')
    connection.sudo('rm -rf /var/solr/contentstore')
    connection.sudo('rm -rf /var/solr/data/alfrescoModels')
    logging.info('Deleted indexes')

#############################################
def create_sites():
    logging.info('Creating sites')
    client = acs.main()
    logging.info('Created sites')
    return client

#############################################
def delete_alfresco_tables(optionfile, group='dev'):
    logging.info('Deleting Alfresco tables')
    stmt = """SET FOREIGN_KEY_CHECKS = 0;
               SET GROUP_CONCAT_MAX_LEN=32768;
               SET @tables = NULL;
               SELECT GROUP_CONCAT('`', table_name, '`') INTO @tables
               FROM information_schema.tables
               WHERE table_schema = 'acs';

               SELECT IFNULL(@tables,'dummy') INTO @tables;
               SET @tables = CONCAT('DROP TABLE IF EXISTS ', @tables);

               PREPARE stmt FROM @tables;
               EXECUTE stmt;
               DEALLOCATE PREPARE stmt;
               SET FOREIGN_KEY_CHECKS = 1;
            """
    cnx = None
    try:
        cnx = mysql.connector.connect(option_files=optionfile, option_groups=group)
        cur = cnx.cursor()
        cur.execute(stmt)
    finally:
        cnx and cnx.close()

    logging.info('Deleted Alfresco tables')

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
def upload_content(acsClient, conf):
    logging.info('Uploading content')

    # get ACS client if necessary
    if not acsClient:
        # get commandline arguments
        args = acs.getArgs()
        acsConf = {}
        if args.conf:
            acsConf = acs.getConfig(args.conf, args.stage)

        acsClient = acs.getAcsClient(args, acsConf)

    # start bulk import
    imports = conf and conf['bulkImport']
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

    logging.info('Uploaded content')

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
    # TODO get log file and level from config file
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO
                        )
    logging.info('start')

    # load refresh config file - hardcode config file name for now 
    conf = acs.getConfig('acs-refresh-dev.yml')
    sanityCheck(conf)

    bucketName = conf['s3bucket']
    print('WARNING: drop all ACS tables, empty S3 bucket ' + bucketName + ', and delete existing indexes.') 
    answer = raw_input('Type "yes" to continue and any other key to exit: ')

    if answer != 'yes':
        sys.exit()

    acsClient = None

    sudoPass = getpass.getpass("What's your sudo password?")
    pwConfig = Config(overrides={'sudo': {'password': sudoPass}})
    repoHost = Connection(conf['repoHost'], config=pwConfig)
    indexerHost = Connection(conf['indexerHost'], config=pwConfig)
    stop_indexer(indexerHost)
    clear_indexes(indexerHost)
    stop_repo(repoHost)
    delete_alfresco_tables('mysql.cnf', 'dev')
    empty_s3_bucket(bucketName)
    start_repo(repoHost)
    start_indexer(indexerHost)
    acsClient = create_sites()
    upload_content(acsClient, conf)

    logging.info('end')

#############################################
if __name__ == "__main__":
    main()
