import unittest

import requests
import responses

from AcsClient import AcsClient

from pprint import pprint

class AcsClientTestCase(unittest.TestCase):
    def setUp(self):
        self.acsClient = AcsClient('http://localhost:8080', 'fake', 'fake')

    def tearDown(self):
        self.acsClient = None

    @responses.activate
    def testGetNode(self):
        url = 'http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1/nodes/1234'
        json = {'entry': 
                {'modifiedByUser': {'displayName': 'Test User', 'id': 'testuser'},
                  'nodeType': 'ct:TestCustomType', 'name': 'td.txt',
                  'aspectNames': ['rn:renditioned', 'cm:versionable', 'cm:titled', 'cm:auditable', 'cm:author'],
                  'isFolder': False,
                  'properties': {'ct:docType': 'Test', 'cm:versionType': 'MAJOR', 'cm:versionLabel': '1.0', 'cm:title': 'test title', 'cm:author': 'testuser'},
                  'content': {'mimeType': 'text/plain', 'sizeInBytes': 462, 'mimeTypeName': 'Plain Text', 'encoding': 'UTF-8'},
                  'createdByUser': {'displayName': 'Test User', 'id': 'testuser'},
                  'modifiedAt': '2018-04-20T21:46:09.659+0000',
                  'parentId': '12345678-4771-4bb9-986a-64be26bd1c4a',
                  'isFile': True,
                  'id': '12345678-ccdb-4a97-a823-9315ebea500a',
                  'createdAt': '2018-03-20T21:46:09.659+0000'
                }
               }

        responses.add(responses.GET, url, json=json, status=200)
        ret = self.acsClient.getNode('1234')
        self.assertTrue(ret)
        self.assertEqual(ret['id'], '12345678-ccdb-4a97-a823-9315ebea500a')

    @responses.activate
    def testGetSite(self):
        url = 'http://localhost:8080/alfresco/api/-default-/public/alfresco/versions/1/sites/mysite'
        json = {'entry': {'description': 'My Site', 'title': 'My Site', 'visibility': 'PRIVATE', 'preset': 'site-dashboard',
                          'role': 'SiteManager', 'guid': '12345678-25d9-40ef-96cf-0bb16350dc0d', 'id': 'mysite'}} 

        responses.add(responses.GET, url, json=json, status=200)

        ret = self.acsClient.getSite('mysite')
        self.assertTrue(ret)
        self.assertEqual(ret['id'], 'mysite')

    @responses.activate
    def testGetSiteGroup(self):
        url = 'http://localhost:8080/alfresco/s/api/sites/mysite/memberships/GROUP_test_group'
        json = {'url': '/alfresco/s/api/sites/mysite/memberships/GROUP_test_group', 'role': 'SiteConsumer',
                'authority': {'fullName': 'GROUP_test_group', 'url': '/alfresco/s/api/groups/test_group',
                              'authorityType': 'GROUP', 'displayName': 'Test Group', 'shortName': 'test_group'}}

        responses.add(responses.GET, url, json=json, status=200)

        ret = self.acsClient.getSiteGroup('mysite', 'test_group')
        self.assertTrue(ret)
        self.assertEqual(ret['role'], 'SiteConsumer')
        self.assertEqual(ret['authority']['shortName'], 'test_group')

    @responses.activate
    def testAddSiteGroup(self):
        url = 'http://localhost:8080/alfresco/s/api/sites/mysite/memberships'
        json = {'url': '/alfresco/s/api/sites/financialaid/memberships/GROUP_test_group', 'role': 'SiteConsumer',
                'authority': {'fullName': 'GROUP_test_group', 'url': '/alfresco/s/api/groups/test_group',
                              'authorityType': 'GROUP', 'displayName': 'Test Group', 'shortName': 'test_group'}}

        responses.add(responses.POST, url, json=json, status=200)

        ret = self.acsClient.addSiteGroup('mysite', 'test_group', 'SiteConsumer')
        self.assertTrue(ret)
        self.assertEqual(ret['role'], 'SiteConsumer')
        self.assertEqual(ret['authority']['shortName'], 'test_group')

###########################
# main
if __name__ == '__main__':
    unittest.main()
