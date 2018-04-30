import requests 

#############################################
class AcsClient:
    ######################################
    # constructor
    def __init__(self, urlbase, user, pw):
        self.urlbase = urlbase
        self.apiprefix = urlbase + '/alfresco/api/-default-/public/alfresco/versions/1'
        self.sapiprefix = urlbase + '/alfresco/s/api'
        self.user = user
        self.pw = pw
        self.auth = (user, pw)

    ######################################
    # get, post and put
    def get(self, url):
        response = requests.get(url, auth=self.auth)
        if response.ok:
            return response.json()
        elif response.status_code == requests.codes.not_found:
            return None
        else:
            response.raise_for_status()

    def post(self, url, data=None, files=None):
        response = requests.post(url, auth=self.auth, json=data, files=files)
        if response.ok:
            return response.json()
        else:
            response.raise_for_status()

    def put(self, url, data=None, files=None):
        response = requests.put(url, auth=self.auth, json=data, files=files)
        if response.ok:
            return response.json()
        else:
            response.raise_for_status()

    ######################################
    # groups API 
    def createRootGroup(self, id, displayName):
        url = self.apiprefix + '/groups'
        data = {"id":id,"displayName":displayName}
        r = self.post(url, data=data)
        return r and r['entry']

    ######################################
    # nodes API 
    def getNode(self, nodeId):
        url = self.apiprefix + '/nodes/' + nodeId
        r = self.get(url)
        return r and r['entry']

    def uploadContent(self, folderId, files):
        url = self.apiprefix + '/nodes/' + folderId + '/children'
        r = self.post(url, files=files)
        return r and r['entry']
     
    def setPermissions(self, id, permissions):
        url = self.apiprefix + '/nodes/' + id
        data = {"permissions": permissions}
        r = self.put(url, data=data)
        return r
        
    ######################################
    # sites API 
    def createSite(self, id, title, desc, visibility='PRIVATE'):
        url = self.apiprefix + '/sites'
        data = {"id":id,"title":title, "description":desc, "visibility":visibility}
        r = self.post(url, data=data)
        return r and r['entry']
     
    def getSite(self, siteId):
        url = self.apiprefix + '/sites/' + siteId
        r = self.get(url)
        return r and r['entry']

    def getSites(self):
        url = self.apiprefix + '/sites'
        r = self.get(url)
        return r and r['list'] and r['list']['entries']

    def addSiteUser(self, siteId, username, role='SiteConsumer'):
        url = self.apiprefix + '/sites/' + siteId + '/members'
        data = [{"role":role,"id": username}]
        r = self.post(url, data=data)
        return r and r['entry']
     
    def getSiteGroup(self, siteId, group):
        fullName = group if group.startswith('GROUP_') else 'GROUP_' + group
        url = self.sapiprefix + '/sites/' + siteId + '/memberships/' + fullName
        r = self.get(url)
        return r
     
    def addSiteGroup(self, siteId, group, role='SiteConsumer'):
        url = self.sapiprefix + '/sites/' + siteId + '/memberships'
        fullName = group if group.startswith('GROUP_') else 'GROUP_' + group
        data = {"role":role, "group": {"fullName": fullName} }
        r = self.post(url, data=data)
        return r
     
    def getSiteContainers(self, siteId):
        url = self.apiprefix + '/sites/' + siteId + '/containers'
        r = self.get(url)
        return r and r['list'] and r['list']['entries']

    def getSiteMembers(self, siteId):
        url = self.apiprefix + '/sites/' + siteId + '/members'
        r = self.get(url)
        return r and r['list'] and r['list']['entries']

    def getDocumentLibrary(self, siteId):
        url = self.apiprefix + '/sites/' + siteId + '/containers/documentLibrary'
        r = self.get(url)
        return r and r['entry']
