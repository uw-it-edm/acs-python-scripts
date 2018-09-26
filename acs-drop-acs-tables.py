#!/usr/bin/python2.7
# drop ACS tables.
# WARNING: DROP ACS Tables.
#
# * pip install mysql-connector-python (for connecting to DB to drop repository tables)
# * mysql.cnf - mysql configuration to connect to repo DB.
#
import argparse
import logging

import sys 
import mysql.connector

#############################################
def drop_alfresco_tables(optionfile, group='dev'):
    logging.info('Dropping Alfresco tables')
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

    logging.info('Dropped Alfresco tables')

#############################################
# main
def main():
    # config logging
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO
                        )
    # require command line arg 'DROP ACS TABLES' as a safety guard
    if len(sys.argv)<2 or sys.argv[1] != 'DROP-ACS-TABLES':
        print >>sys.stderr, "please include command line argument 'DROP-ACS-TABLES' to confirm that you want to drop ACS tables"
        exit(0)
    
    logging.info('start ' + sys.argv[0])

    drop_alfresco_tables('mysql.cnf', 'dev')

    logging.info('end ' + sys.argv[0])

#############################################
if __name__ == "__main__":
    main()
