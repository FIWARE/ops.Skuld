# -*- coding: utf-8 -*-

# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U
#
# This file is part of FIWARE project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For those usages not covered by the Apache version 2.0 License please
# contact with opensource@tid.es


from os import environ
from unittest import TestCase
from mock import patch, MagicMock
from fiwareskuld.utils.osclients import OpenStackClients
import cinderclient.v2.client
import cinderclient.v1.client
import neutronclient.v2_0.client
import novaclient.v2.client
import glanceclient.v1.client
import keystoneclient.v2_0.client
import keystoneclient.session
import keystoneclient.auth.identity.v3.tokens
from swiftclient.client import Connection
from collections import defaultdict

# catalog
service = {
    u'endpoints': [
        {u'url': u'http://83.26.10.2:8080/v1/AUTH_00000000000000000000000000000001', u'interface': u'public',
         u'region': u'Spain2', u'id': u'00000000000000000000000000000002'
         },
        {u'url': u'http://172.0.0.1:8080', u'interface': u'admin', u'region': u'Spain2',
         u'id': u'00000000000000000000000000000001'
         }
    ],
    u'type': u'object-store', u'id': u'00000000000000000000000000000044'
}


class MySessionMock(MagicMock):
    # Mock of a keystone Session

    def get_endpoint(self, service_type, region_name):
        """return a endpoint"""
        return "http://cloud.lab.fi-ware.org:4731/v2.0"

    def get_token(self):
        """return a token"""
        return "a12baba1ddde00000000000000000001"

    def get_access(self, session):
        """return a catalog"""

        d = defaultdict(list)
        d['catalog'].append(service)
        return d


class TestOSClients(TestCase):

    mock_session = MySessionMock()

    def setUp(self):
        """define environment"""
        self.OS_AUTH_URL = 'http://cloud.lab.fi-ware.org:4731/v2.0'
        self.OS_USERNAME = 'user'
        self.OS_PASSWORD = 'password'
        self.OS_TENANT_NAME = 'user cloud'
        self.OS_TENANT_ID = '00000000000000000000000000000001'
        self.OS_REGION_NAME = 'Spain2'
        self.OS_TRUST_ID = ''

        environ.setdefault('OS_AUTH_URL', self.OS_AUTH_URL)
        environ.setdefault('OS_USERNAME', self.OS_USERNAME)
        environ.setdefault('OS_PASSWORD', self.OS_PASSWORD)
        environ.setdefault('OS_TENANT_NAME', self.OS_TENANT_NAME)
        environ.setdefault('OS_TENANT_ID', self.OS_TENANT_ID)
        environ.setdefault('OS_REGION_NAME', self.OS_REGION_NAME)
        environ.setdefault('OS_TRUST_ID', self.OS_TRUST_ID)

    def test_implement_client(self):
        """test_implement_client check that we could implement an empty client."""

        osclients = OpenStackClients()
        self.assertIsNotNone(osclients)

    def test_implement_client_with_unknown_module(self):
        """test_implement_client_with_unknown_module check that we could not implement an empty client,
        raising an exception."""

        try:
            OpenStackClients(modules="fakeOpenstackModule")
        except Exception as ex:
            self.assertRaises(ex)

    def test_implement_client_with_all_modules(self):
        """test_implement_client_with_all_modules check that we could not implement an empty client,
        with all modules and a given auth_url"""

        OS_AUTH_URL = 'http://host.com:4731/v3'

        osclients = OpenStackClients(modules="all", auth_url=OS_AUTH_URL)
        self.assertIsNotNone(osclients)

    def test_implement_client_with_selected_module(self):
        """test_implement_client_with_selected_module check that we could not implement an empty client, with selected
         modules (keystone and cinder)"""
        selected_modules = "keystone,cinder,"

        osclients = OpenStackClients(modules=selected_modules)

        self.assertIsNotNone(osclients)

    def test_implement_client_with_env(self):
        """test_implement_client_with_env check that we could implement a client with data from the OS environment."""

        osclients = OpenStackClients()

        self.assertIsNotNone(osclients)

    def test_get_cinderclient(self):
        """test_get_cinderclient check that we could retrieve a Session client to work with cinder"""
        osclients = OpenStackClients(modules="cinder")
        cinderClient = osclients.get_cinderclient()

        # api_version = cinderClient.get_volume_api_version_from_endpoint() --> This should return "2" against a server
        self.assertIsInstance(cinderClient, cinderclient.v2.client.Client)

    def test_get_cinderclient_v1(self):
        """test_get_cinderclient_v1 check that we could retrieve a Session client to work with cinder using
        an older client (v1)."""
        osclients = OpenStackClients(modules="cinder")
        cinderClient = osclients.get_cinderclientv1()
        # api_version = cinderClient.get_volume_api_version_from_endpoint() --> This should return "1" against a server

        self.assertIsInstance(cinderClient, cinderclient.v2.client.Client)

    def test_get_cinderclient_unknown_module(self):
        """test_get_cinderclient_unknown_module check that we could not retrieve a Session client to work with cinder if
        there is no modules defined"""
        try:
            osclients = OpenStackClients(modules="")
            osclients.get_cinderclient()
        except Exception as ex:
            self.assertRaises(ex)

    def test_get_neutronclient_with_all_modules(self):
        """test_get_neutronclient_with_all_modules check that we could retrieve a Session client to work with neutron if
        osclients is created with all modules"""

        osclients = OpenStackClients(modules="auto")
        neutronClient = osclients.get_neutronclient()

        self.assertIsInstance(neutronClient, neutronclient.v2_0.client.Client)

    def test_get_novaclient(self):
        """test_get_novaclient check that we could retrieve a Session client to work with nova"""
        osclients = OpenStackClients(modules="nova")
        novaClient = osclients.get_novaclient()

        self.assertIsInstance(novaClient, novaclient.v2.client.Client)

    @patch('fiwareskuld.utils.osclients.session', mock_session)
    def test_get_glanceclient(self):
        """test_get_glanceclient check that we could retrieve a Session client to work with glance"""

        osclients = OpenStackClients(modules="glance")
        osclients.set_keystone_version(use_v3=False)
        glanceClient = osclients.get_glanceclient()

        self.assertIsInstance(glanceClient, glanceclient.v1.client.Client)

    @patch('fiwareskuld.utils.osclients.session', mock_session)
    def test_get_swiftclient(self):
        """test_get_swiftclient check that we could retrieve a Session client to work with swift using keystone v3"""

        osclients = OpenStackClients(modules="swift")
        swiftClient = osclients.get_swiftclient()

        self.assertIsInstance(swiftClient, Connection)

    @patch('fiwareskuld.utils.osclients.session', mock_session)
    def test_get_swiftclient_with_keystone_v2(self):
        """test_get_swiftclient check that we could retrieve a Session client to work with swift using keystone v2"""

        osclients = OpenStackClients(modules="swift")
        osclients.use_v3 = False
        swiftClient = osclients.get_swiftclient()

        self.assertIsInstance(swiftClient, Connection)

    def test_get_keystoneclient_v2(self):
        """test_get_keystoneclient_v2 check that we could retrieve a Session client to work with keystone v2"""
        osclients = OpenStackClients()
        osclients.use_v3 = False
        keystoneClient = osclients.get_keystoneclient()

        self.assertIsInstance(keystoneClient, keystoneclient.v2_0.client.Client)

    def test_get_keystoneclient_v2_with_trust_id(self):
        """test_get_keystoneclient_v2_with_trust_id check that we could retrieve a Session client to work
        with keystone v2 and using trust_id"""

        osclients = OpenStackClients()
        osclients.use_v3 = False
        trust_id = "randomid0000000000000000000000001"
        osclients.set_credential(self.OS_USERNAME, self.OS_PASSWORD, trust_id=trust_id)

        keystoneClient = osclients.get_keystoneclient()

        self.assertIsInstance(keystoneClient, keystoneclient.v2_0.client.Client)

    def test_get_keystoneclient_v2_with_tenant_name(self):
        """test_get_keystoneclient_v2_with_tenant_name check that we could retrieve a Session client to work
        with keystone v2 and using tenant_name"""

        osclients = OpenStackClients()
        osclients.use_v3 = False
        osclients.set_credential(self.OS_USERNAME, self.OS_PASSWORD, tenant_name=self.OS_TENANT_NAME)

        keystoneClient = osclients.get_keystoneclient()

        self.assertIsInstance(keystoneClient, keystoneclient.v2_0.client.Client)

    def test_get_keystoneclient_v2_with_tenant_id(self):
        """test_get_keystoneclient_v2_with_tenant_id check that we could retrieve a Session client to work
        with keystone v2 and using tenant_id"""

        osclients = OpenStackClients()
        osclients.use_v3 = False
        osclients.set_credential(self.OS_USERNAME, self.OS_PASSWORD, tenant_id=self.OS_TENANT_ID)

        keystoneClient = osclients.get_keystoneclient()

        self.assertIsInstance(keystoneClient, keystoneclient.v2_0.client.Client)

    def test_get_keystoneclient_v3(self):
        """test_get_keystoneclient_v3 check that we could retrieve a Session client to work with keystone v3"""
        osclients = OpenStackClients()
        keystoneClient = osclients.get_keystoneclient()

        self.assertIsInstance(keystoneClient, keystoneclient.v3.client.Client)

    def test_get_keystoneclient_v3_with_trust_id(self):
        """test_get_keystoneclient_v3_with_trust_id check that we could retrieve a Session client to work
        with keystone v3 and using trust_id"""
        osclients = OpenStackClients()
        trust_id = "randomid0000000000000000000000001"
        osclients.set_credential(self.OS_USERNAME, self.OS_PASSWORD, trust_id=trust_id)

        keystoneClient = osclients.get_keystoneclient()

        self.assertIsInstance(keystoneClient, keystoneclient.v3.client.Client)

    def test_set_credential_to_osclients(self):
        """test_set_credential_to_osclients check that we could set credentials using method set_credential"""
        username = "new_user"
        password = "new_password"
        tenant_name = "new_user cloud"
        tenant_id = "00000000000000000000000000000002"
        trust_id = "randomid0000000000000000000000001"

        # FIRST CHECK: Credentials from ENV
        osclients = OpenStackClients()
        self.assertEqual(osclients._OpenStackClients__username, self.OS_USERNAME)
        self.assertEqual(osclients._OpenStackClients__tenant_id, self.OS_TENANT_ID)

        # SECOND CHECK: updating Credentials with tenant_id
        osclients.set_credential(username, password, tenant_id=tenant_id)
        self.assertEqual(osclients._OpenStackClients__tenant_id, tenant_id)

        # THIRD CHECK: updating Credentials with tenant_name
        osclients.set_credential(username, password, tenant_name=tenant_name)
        self.assertEqual(osclients._OpenStackClients__tenant_name, tenant_name)

        # FOURTH CHECK: updating Credentials with trust_id
        osclients.set_credential(username, password, trust_id=trust_id)
        self.assertEqual(osclients._OpenStackClients__trust_id, trust_id)

        # FIFTH CHECK: updating Credentials without trust_id, tenant_id and tenant_name
        osclients.set_credential(username, password)
        self.assertIsNone(osclients._OpenStackClients__trust_id)
        self.assertIsNone(osclients._OpenStackClients__tenant_name)
        self.assertIsNone(osclients._OpenStackClients__tenant_id)

        # Creating a client to check that set_credential destroy the session with v3
        novaclient = osclients.get_novaclient()
        self.assertIsNotNone(osclients._session_v3)
        osclients.set_credential(username, password)
        self.assertIsNone(osclients._session_v3)

        # Creating a client to check that set_credential destroy the session with v2
        osclients.use_v3 = False
        novaclient = osclients.get_novaclient()
        self.assertIsNotNone(osclients._session_v2)
        osclients.set_credential(username, password)
        self.assertIsNone(osclients._session_v2)

    def test_set_region(self):
        """test_set_region check that we could change the region after create the client"""

        # FIRST CHECK: Region is recovered from ENV
        osclients = OpenStackClients()
        self.assertEqual(osclients.region, self.OS_REGION_NAME)

        # Check that region is updated to a new Value.
        region = "Budapest"
        osclients.set_region(region)
        self.assertEqual(osclients.region, region)

    def test_get_session_without_auth_url(self):
        """test_get_session_without_auth_url check that we could not retrieve a session without auth_url"""

        osclients = OpenStackClients()
        osclients.auth_url = None

        # Checking v3
        try:
            osclients.get_session()
        except Exception as ex:
            self.assertRaises(ex)

        # Checking v2
        osclients.use_v3 = False
        try:
            osclients.get_session()
        except Exception as ex:
            self.assertRaises(ex)

    def test_get_session_with_different_auth_url(self):
        """test_get_session_without_auth_url check that we could retrieve a session with auth_url formats"""

        auth_url_v2_1 = "http://cloud.lab.fi-ware.org:4731/v2.0"
        auth_url_v2_2 = "http://cloud.lab.fi-ware.org:4731/v2.0/"

        auth_url_v3_1 = "http://cloud.lab.fi-ware.org:4731/v3"
        auth_url_v3_2 = "http://cloud.lab.fi-ware.org:4731/v3/"

        osclients = OpenStackClients()

        # Checking v3
        osclients.auth_url = auth_url_v2_1
        session = osclients.get_session()
        self.assertIsInstance(session, keystoneclient.session.Session)

        session.invalidate()
        osclients._session_v3 = None

        osclients.auth_url = auth_url_v2_2
        session = osclients.get_session()
        self.assertIsInstance(session, keystoneclient.session.Session)

        session.invalidate()
        osclients._session_v3 = None

        # Checking v2
        osclients.use_v3 = False
        osclients.auth_url = auth_url_v3_1
        session = osclients.get_session()
        self.assertIsInstance(session, keystoneclient.session.Session)

        session.invalidate()
        osclients._session_v2 = None

        osclients.auth_url = auth_url_v3_2
        session = osclients.get_session()
        self.assertIsInstance(session, keystoneclient.session.Session)

        session.invalidate()
        osclients._session_v2 = None

    def test_get_session_without_username_nor_token(self):
        """test_get_session_without_username check that we could not retrieve a session without username"""

        osclients = OpenStackClients()

        osclients.set_credential("", self.OS_PASSWORD, tenant_id=self.OS_TENANT_ID)

        # Checking v3
        try:
            osclients.get_session()
        except Exception as ex:
            self.assertRaises(ex)

        # Checking v2
        osclients.use_v3 = False
        try:
            osclients.get_session()
        except Exception as ex:
            self.assertRaises(ex)

    def test_get_session_using_token(self):
        """test creating a session using a token instead of a password"""

        osclients = OpenStackClients()

        osclients.set_token('faketoken')
        session = osclients.get_session()
        self.assertIsInstance(session, keystoneclient.session.Session)
        self.assertTrue(type(session.auth) == keystoneclient.auth.identity.v3.token.Token)


class TestOSClientsOverrideEndpoint(TestCase):
    """Class to test the endpoint override feature"""

    def setUp(self):
        d = defaultdict(list)
        d['catalog'].append(service)
        self.access = d
        self.osclients = OpenStackClients()
        self.url = 'http://fake.org:9090'
        self.original_url = service['endpoints'][1]['url']

    def restore_catalog(self):
        """restore catalog"""
        service['endpoints'][1]['url'] = self.original_url

    def tearDown(self):
        """restore objects"""
        self.restore_catalog()

    def override_endpoint(self):
        """method that override the endpoint"""
        self.osclients.override_endpoint('object-store', 'Spain2', 'admin', self.url)

    def assertOverrideEndpoint(self):
        """check that the override has been done"""
        self.assertEquals(self.osclients.get_admin_endpoint('object-store', 'Spain2'), self.url)

    def test_override_endpoint_session(self):
        """test that invoking override endpoint does not create a session"""
        self.override_endpoint()

        self.assertFalse(self.osclients._session_v2)
        self.assertFalse(self.osclients._session_v3)

    def test_override_endpoint(self):
        """check that a session catalog is overriden"""
        mock = MagicMock()
        config = {'auth.get_access.return_value': self.access}
        mock.configure_mock(**config)
        self.osclients._session_v3 = mock
        self.override_endpoint()
        self.assertOverrideEndpoint()

    @patch('fiwareskuld.utils.osclients.session')
    def test_override_endpoint_multiple(self, mock):
        """test that override works with an already created session and then
        with a new one without invoking the method again"""
        config = {'Session.return_value.auth.get_access.return_value': self.access}
        mock.configure_mock(**config)
        session = self.osclients.get_session()
        self.override_endpoint()
        self.assertOverrideEndpoint()

        # invalidate and create a new session; ensure than catalog is again
        # the original. Setting a new token invalidate the session. The new
        # one is created at the invocation of get_admin_endpoint.
        self.restore_catalog()
        self.osclients.set_token('faketoken')

        # check again
        self.assertOverrideEndpoint()
