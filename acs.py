#!/usr/bin/python

import argparse
import logging
import yaml

from AcsClient import AcsClient

#############################################
# get commandline arguments
def getArgs():
   parser = argparse.ArgumentParser()
   parser.add_argument('-c', '--conf', default='acs.yml', help='conf file')
   parser.add_argument('-s',  '--stage',  choices=['dev', 'local', 'test', 'prod'], default='dev', help='stage')
   parser.add_argument('-p', '--password', help='password')
   parser.add_argument('-u', '--user', default='admin', help='username')
   parser.add_argument('--url', help='urlbase, e.g. http://localhost:8080')
   return parser.parse_args()

#############################################
# load conf file (yml)
def getConfig(filename, stage='dev'):
    # sanity check
    if not filename:
        return None

    ret = None
    with open(filename, 'r') as file:
        conf = yaml.load(file)
        ret = conf
        if conf['default']:
            ret = conf['default']
            if stage and stage in conf:  # override default
                for key in conf[stage]:
                    ret[key] = conf[stage][key]

    return ret;

#############################################
# get ACS client
def getAcsClient(args, conf):
    user = args.user or conf['user']
    pw   = args.password or (conf and conf['password'])
    urlbase  = args.url or (conf and (conf['url'] or conf['urlbase']))

    if not (user and pw and urlbase):
        return None
    else:
        return AcsClient(urlbase, user, pw)

#############################################
# create and update sites
# TODO handle site update
def createOrUpdateSite(acs, site):
    # sanity check
    if not site:
        logging.warn('no site. noop')   
        return

    # create site if it does not exist
    s = acs.getSite(site['id'])
    if s:
        logging.info('site ' + site['id'] + ' already exists.')
    else:
        logging.info('create site ' + site['id'])
        acs.createSite(site['id'], site['title'], site['description']);

    # add group roles to site
    roles = site['roles'] if 'roles' in site else []
    for r in roles:
        if 'role' in r and 'group' in r:
           g = acs.getSiteGroup(site['id'], r['group'])
           if g and 'role' in g and g['role'] == r['role']: 
              logging.info('group ' + r['group'] + ' with role ' + r['role'] + ' already exists on site ' + site['id'])
           else:
              logging.info('add group ' + r['group'] + ' with role ' + r['role'] + ' to site ' + site['id'])
              acs.addSiteGroup(site['id'], r['group'], r['role'])
           
#############################################
# main
def main():
    # get commandline arguments
    args = getArgs()
    conf = {}
    if args.conf:
        conf = getConfig(args.conf, args.stage)

    # config logging
    # TODO get log file and level from config file
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO
                       )
    logging.info('start')   

    # get ACS client
    acs = getAcsClient(args, conf)

    # create and update sites
    if conf and conf['sites']:
        sites = conf['sites']
        for site in conf['sites']:
            createOrUpdateSite(acs, site);

    logging.info('end')   

#############################################
if __name__ == "__main__":
    main()
