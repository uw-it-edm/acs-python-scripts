#!/usr/bin/python

import argparse
import json
import logging
from os.path import isfile

import yaml

from AcsClient import AcsClient


#############################################
# get commandline arguments
def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf', default='acs.yml', help='conf file')
    parser.add_argument('-f', '--filePlan', help='file plan', default='filePlan.yml')
    parser.add_argument('-r', '--rules', help='rules config file', default='rules.yml')
    parser.add_argument('-s', '--stage', choices=['dev', 'local', 'test', 'prod'], default='dev',
                        help='stage')
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
# load rules conf file (yml)
def load_yml_file(file_name):
    # sanity check
    if not file_name or not isfile(file_name):
        return None

    ret = {}
    with open(file_name, 'r') as file:
        ret = yaml.load(file)

    return ret


#############################################
# get ACS client
def getAcsClient(args, conf):
    user = args.user or conf['user']
    pw = args.password or (conf and conf['password'])
    urlbase = args.url or (conf and (conf['url'] or conf['urlbase']))

    if not (user and pw and urlbase):
        return None
    else:
        return AcsClient(urlbase, user, pw)

#############################################
# create or update Record Category or Folder
def createOrUpdateRCF(acs, rcf):
    if not (rule and rule['folders'] and rule['rule']):
        return

    folders = rule['folders']
    for folder in folders:
        if folder.find("/documentLibrary") < 0:
            folder = folder + '/documentLibrary'  # folder path
        createOrUpdateFolderRule(acs, folder, rule['rule'])

#############################################
# create or update rules
def createOrUpdateFolderRule(acs, folderPath, rule):
    folderNode = acs.getNodeByPath(folderPath)
    if not folderNode:
        logging.warn('folder ' + folderPath + ' does not exist')
        return

    folderId = folderNode['id']

    existingRules = acs.getRules(folderId)
    existingRuleIds = {rule['title']:rule['id'] for rule in existingRules}
    title = rule['title']
    if title in existingRuleIds:
        # it is a lot easier and cheap to always update than trying to find if the rule config has changed
        logging.info('updating rule "' + title +'"for folder ' + folderPath + "  " + existingRuleIds[title])
        result = acs.updateRule(folderId, existingRuleIds[title], rule)
    else:
        logging.info('Creating rule "' + title + '" for folder: ' + folderPath)
        result = acs.createRule(folderId, rule)

#############################################
# create or update rule
def createOrUpdateRule(acs, rule):
    if not (rule and rule['folders'] and rule['rule']):
        return

    folders = rule['folders']
    for folder in folders:
        if folder.find("/documentLibrary") < 0:
            folder = folder + '/documentLibrary'  # folder path
        createOrUpdateFolderRule(acs, folder, rule['rule'])

#############################################
# create and update sites
# TODO handle site update
def createOrUpdateSite(acs, site):
    # sanity check
    if not site:
        logging.warn('no site. noop')
        return

    # create site if it does not exist
    siteId = site['id']
    s = acs.getSite(siteId)
    if s:
        logging.info('site ' + siteId + ' already exists.')
    else:
        logging.info('create site ' + siteId)
        s = acs.createSite(siteId, site['title'], site['description']);

    # add group roles to site
    roles = site['roles'] if 'roles' in site else []
    for r in roles:
        if 'role' in r and 'group' in r:
            g = acs.getSiteGroup(siteId, r['group'])
            if g and 'role' in g and g['role'] == r['role']:
                logging.info(
                    'group ' + r['group'] + ' with role ' + r['role'] + ' already exists on site ' +
                    siteId)
            else:
                logging.info(
                    'add group ' + r['group'] + ' with role ' + r['role'] + ' to site ' + siteId)
                acs.addSiteGroup(siteId, r['group'], r['role'])

    # create folders
    folders = site['folders'] if 'folders' in site else []
    for folder in folders:
        folderName = folder['name']
        folderObj = acs.getNodeByPath(siteId + '/documentLibrary/' + folderName)
        if (folderObj):
            logging.info('folder ' + folderName + ' already exists')
        else:
            docLib = acs.getDocumentLibrary(s['id'])
            acs.createFolder(docLib['id'], folderName);
            logging.info('creating folder ' + folderName + ' in ' + siteId)

#############################################
# createOrUpdate category
def createOrUpdateChildCategories(acs, parentId, children):

    exitingChildren = acs.getRecordCategoriesAndFolders(parentId)
    exitingChildrenMap = {c['entry']['name']:{'id':c['entry']['id'], 'nodeType': c['entry']['nodeType']} for c in exitingChildren}

    for child in children:
        if child['name'] in exitingChildrenMap:
            logging.info('Category ' + child['name'] + ' already exists.')
            childCategory = exitingChildrenMap[child['name']]
        elif 'nodeType' in child and child['nodeType']=='recordFolder':
            logging.info('Creating folder ' + child['name'])
            childCategory = acs.createRecordFolder(parentId, child['name'])
        else:
            logging.info('Creating category ' + child['name'])
            childCategory = acs.createRecordCategory(parentId, child['name'])

        if 'children' in child and ('nodeType' not in child or child['nodeType'] != 'recordFolder'):
            createOrUpdateChildCategories(acs, childCategory['id'], child['children'])  # recursive call

#############################################
# process file plan
def createOrUpdateFilePlan(acs, filePlan):
    rootCategories = acs.getRootRecordCategories()
    rootCategoriesMap = {c['entry']['name']:{'id':c['entry']['id'], 'nodeType': c['entry']['nodeType']} for c in rootCategories}

    if filePlan:
        for rc in filePlan:
            category = None
            if rc['name'] in rootCategoriesMap:
                category = rootCategoriesMap[rc['name']]
                logging.info('Root category ' + rc['name'] + ' already exists.')
            else:
                logging.info('Creating root category ' + rc['name'])
                category = acs.createRootRecordCategory(rc['name'])

            if 'children' in rc:
                createOrUpdateChildCategories(acs, category['id'], rc['children']);

#############################################
# main
def main():
    # config logging
    # TODO get log file and level from config file
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO
                        )
    logging.info('start')

    # get commandline arguments
    args = getArgs()
    conf = {}
    if args.conf:
        conf = getConfig(args.conf, args.stage)

    # get ACS client
    acs = getAcsClient(args, conf)

    # create and update sites
    if conf and conf['sites']:
        for site in conf['sites']:
            createOrUpdateSite(acs, site);

    # create and update rules
    rules = None
    if args.rules:
        rules = load_yml_file(args.rules)

    if rules:
        for rule in rules:
            createOrUpdateRule(acs, rule);

    # file plan
    filePlan = None
    if args.filePlan:
        filePlan = load_yml_file(args.filePlan)
        createOrUpdateFilePlan(acs, filePlan)

    logging.info('end')

#############################################
if __name__ == "__main__":
    main()
