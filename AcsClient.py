import requests
from xml.etree import ElementTree
import util

######################################
# convenience (module) functions
# return full group Id
def fullGroupId(groupId):
    return groupId if groupId.startswith('GROUP_') else 'GROUP_' + groupId

#############################################
class AcsClient:
    ######################################
    # constructor
    def __init__(self, urlbase, user, pw):
        self.urlbase = urlbase
        self.api_prefix = urlbase + '/alfresco/api/-default-/public/alfresco/versions/1'
        self.gs_api_prefix = urlbase + '/alfresco/api/-default-/public/gs/versions/1'
        self.web_script_api_prefix = urlbase + '/alfresco/s/api'
        self.user = user
        self.pw = pw
        self.auth = (user, pw)
        self.session = requests.Session()

    @classmethod
    def fromConfig(cls, filename=None, stage='dev'):
        conf = util.getConfig(filename, stage)
        user = conf and conf['user']
        pw = conf and conf['password']
        urlbase = conf and (conf['url'] or conf['urlbase'])

        if user and pw and urlbase:
            return cls(urlbase, user, pw)
        else:
            return None

    ######################################
    # get, post and put
    def handleResponse(self, response):
        if response.ok:
            if response.headers['Content-Type'].startswith('application/json'):
                return response.json()
            elif response.headers['Content-Type'].startswith('text/xml'):
                return ElementTree.fromstring(response.text)
            elif response.headers['Content-Type'].startswith('text'):
                return response.text
            else:
                return response.raw
        else:
            response.raise_for_status()

    def _get(self, url):
        response = self.session.get(url, auth=self.auth)
        if response.status_code == requests.codes.not_found:
            return None
        else:
            return self.handleResponse(response)

    def _post(self, url, json=None, data=None, files=None):
        response = self.session.post(url, auth=self.auth, json=json, data=data, files=files)
        return self.handleResponse(response)

    def _put(self, url, json=None, data=None, files=None):
        response = self.session.put(url, auth=self.auth, json=json, data=data, files=files)
        return self.handleResponse(response)

    ######################################
    # groups API
    def getGroup(self, id):
        url = self.api_prefix + '/groups/' + fullGroupId(id)
        r = self._get(url)
        return r and r['entry']

    def createRootGroup(self, id, displayName):
        url = self.api_prefix + '/groups'
        data = {"id": id, "displayName": displayName}
        r = self._post(url, json=data)
        return r and r['entry']

    def createGroup(self, id, displayName, parentId='GROUP_uw_groups'):
        url = self.api_prefix + '/groups'
        data = {"id": id, "displayName": displayName, "parentIds":[fullGroupId(parentId)]}
        r = self._post(url, json=data)
        return r and r['entry']

    def getGroupMembers(self, groupId):
        url = self.api_prefix + '/groups/' + fullGroupId(groupId) + '/members'
        r = self._get(url)
        return r and r['list'] and r['list'].r['entries']

    def addGroupMember(self, groupId, memberId, memberType='GROUP'):
        url = self.api_prefix + '/groups/' + fullGroupId(groupId) + '/members'
        data = {"id": memberId, "memberType": memberType}
        r = None
        try:
            r = self._post(url, json=data)
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code != requests.codes.conflict:
                raise
            # else member alfready in group

        return r

    ######################################
    # nodes API
    def getNodeById(self, nodeId):
        url = self.api_prefix + '/nodes/' + nodeId
        r = self._get(url)
        return r and r['entry']

    def getNodeByPath(self, path):
        path = path if path.startswith('Sites/') else 'Sites/' + path
        url = self.api_prefix + '/nodes/-root-?relativePath=' + path
        r = self._get(url)
        return r and r['entry']

    def createFolder(self, parentId, folderName):
        url = self.api_prefix + '/nodes/' + parentId+ '/children'
        data = {"name": folderName, "nodeType": "cm:folder"}
        r = self._post(url, json=data)
        return r and r['entry']

    def uploadContent(self, folderId, files):
        url = self.api_prefix + '/nodes/' + folderId + '/children'
        r = self._post(url, files=files)
        return r and r['entry']

    def setPermissions(self, id, permissions):
        url = self.api_prefix + '/nodes/' + id
        data = {"permissions": permissions}
        r = self._put(url, json=data)
        return r

    ######################################
    # rules API
    def getRules(self, folderId):
        url = self.web_script_api_prefix + '/node/workspace/SpacesStore/' + folderId + '/ruleset/rules'
        result = self._get(url)
        return result and result['data']

    def createRule(self, folderId, ruleData):
        url = self.web_script_api_prefix + '/node/workspace/SpacesStore/' + folderId + '/ruleset/rules'
        result = self._post(url, json=ruleData)
        return result

    def updateRule(self, folderId, ruleId, ruleData):
        url = self.web_script_api_prefix + '/node/workspace/SpacesStore/' + folderId + '/ruleset/rules/' + ruleId
        result = self._put(url, json=ruleData)
        return result

    ######################################
    # people API
    def getUser(self, name):
        url = self.api_prefix + '/people/' + name
        result = self._get(url)
        return result and result['entry']

    # both firstName and email are required fields
    def createAdminAppUser(self, name, password):
        url = self.api_prefix + '/people'
        data = {"id": name, "password": password, "description": "app user",
                "firstName": name,"email":name, "emailNotificationsEnabled":"false"}
        r = self._post(url, json=data)
        return r and r['entry']

    ######################################
    # sites API
    def createSite(self, id, title, desc, visibility='PRIVATE'):
        url = self.api_prefix + '/sites'
        data = {"id": id, "title": title, "description": desc, "visibility": visibility}
        r = self._post(url, json=data)
        return r and r['entry']

    def getSite(self, siteId):
        url = self.api_prefix + '/sites/' + siteId
        r = self._get(url)
        return r and r['entry']

    def getSites(self):
        url = self.api_prefix + '/sites'
        r = self._get(url)
        return r and r['list'] and r['list']['entries']

    def addSiteUser(self, siteId, username, role='SiteConsumer'):
        url = self.api_prefix + '/sites/' + siteId + '/members'
        data = [{"role": role, "id": username}]
        r = self._post(url, json=data)
        return r and r['entry']

    def getSiteGroup(self, siteId, group):
        url = self.web_script_api_prefix + '/sites/' + siteId + '/memberships/' + fullGroupId(group)
        r = self._get(url)
        return r

    def addSiteGroup(self, siteId, group, role='SiteConsumer'):
        url = self.web_script_api_prefix + '/sites/' + siteId + '/memberships'
        if not self.getGroup(group):
            self.createGroup(group, group)
        data = {"role": role, "group": {"fullName": fullGroupId(group)}}
        r = self._post(url, json=data)
        return r

    def getSiteContainers(self, siteId):
        url = self.api_prefix + '/sites/' + siteId + '/containers'
        r = self._get(url)
        return r and r['list'] and r['list']['entries']

    def getSiteMembers(self, siteId):
        url = self.api_prefix + '/sites/' + siteId + '/members'
        r = self._get(url)
        return r and r['list'] and r['list']['entries']

    def getDocumentLibrary(self, siteId):
        url = self.api_prefix + '/sites/' + siteId + '/containers/documentLibrary'
        r = self._get(url)
        return r and r['entry']

    ######################################
    # bulk import API
    def startBulkImport(self, sourceDir, targetPath, batchSize=20, numThreads=10, existingFileMode='REPLACE'):
        url = self.urlbase + '/alfresco/s/bulkfsimport/initiate'
        data = {"sourceDirectory": sourceDir, "targetPath":targetPath, "batchSize":batchSize, "numThreads": numThreads, "existingFileMode":existingFileMode}
        r = self._post(url, data=data)

    def getBulkImportStatus(self):
        url = self.urlbase + '/alfresco/s/bulkfsimport/status.xml'
        r = self._get(url)
        currentStatus = r.find('CurrentStatus')
        resultOfLastExecution = r.find('ResultOfLastExecution')
        return {"currentStatus": currentStatus.text, "lastResult":resultOfLastExecution.text}

    ######################################
    # file plan APIs
    def getRmSite(self):
        url = self.gs_api_prefix + '/gs-sites/rm'
        r = self._get(url)
        return r and r['entry']

    def createRmSite(self, title='Records Management', description='Records Management Site', compliance='DOD5015'):
        url = self.gs_api_prefix + '/gs-sites'
        data = {"title": title, "description": description, "compliance":compliance}
        r = self._post(url, json=data)
        return r and r['entry']

    def getRootRecordCategories(self):
        url = self.gs_api_prefix + '/file-plans/-filePlan-/categories'
        r = self._get(url)
        return r and r['list'] and r['list']['entries']

    def createRootRecordCategory(self, name):
        url = self.gs_api_prefix + '/file-plans/-filePlan-/categories'
        data = {"name": name}
        r = self._post(url, json=data)
        return r and r['entry']

    def getRecordCategoriesAndFolders(self, parentId):
        url = self.gs_api_prefix + '/record-categories/' + parentId + '/children'
        r = self._get(url)
        return r and r['list'] and r['list']['entries']

    def createRecordCategory(self, parentId, name):
        url = self.gs_api_prefix + '/record-categories/' + parentId + '/children'
        data = {"name": name, "nodeType":"rma:recordCategory"}
        r = self._post(url, json=data)
        return r and r['entry']

    def createRecordFolder(self, parentId, name):
        url = self.gs_api_prefix + '/record-categories/' + parentId + '/children'
        data = {"name": name, "nodeType":"rma:recordFolder"}
        r = self._post(url, json=data)
        return r and r['entry']
