#!/usr/bin/env python
# -- encoding: utf-8 --
#
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U
#
# This file is part of FI-Core project.
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
#
__author__ = 'chema'

import json
import re
import os
import sys
from skuld.change_password import PasswordChanger

from keystoneclient.exceptions import NotFound

from utils.osclients import OpenStackClients


# default JSON template. Variables are expanded with environment
default_region_json = """{
"region": "$REGION",
"update_passwords": false,
"users": [
    {"username": "glance", "password": "$GLANCE_PASS"},
    {"username": "nova", "password": "$NOVA_PASS"},
    {"username": "cinder", "password": "$CINDER_PASS"},
    {"username": "neutron", "password": "$NEUTRON_PASS"},
    {"username": "swift", "password": "$SWIFT_PASS"},
    {"username": "admin-$REGION", "password": "$ADMIN_REGION_PASS"}
  ],
"services": [
    { "name": "glance", "type": "image", "public": "http://127.0.0.1:9292",
      "admin": "http://127.0.0.1:9292", "internal": "http://127.0.0.1:9292" },
    { "name": "nova", "type": "compute", "public": "http://127.0.0.1:8774/v2/%(tenant_id)s",
      "admin": "http://127.0.0.1:8774/v2/%(tenant_id)s", "internal": "http://127.0.0.1:8774/v2/%(tenant_id)s" },
    { "name": "cinder", "type": "volume", "public": "http://127.0.0.1:8776/v1/%(tenant_id)s",
      "admin": "http://127.0.0.1:8776/v1/%(tenant_id)s", "internal": "http://127.0.0.1:8776/v1/%(tenant_id)s" },
    { "name": "cinderv2", "type": "volumev2", "public": "http://127.0.0.1:8776/v2/%(tenant_id)s",
      "admin": "http://127.0.0.1:8776/v2/%(tenant_id)s", "internal": "http://127.0.0.1:8776/v2/%(tenant_id)s" },
    { "name": "neutron", "type": "network", "public": "http://127.0.0.1:9696",
      "admin": "http://127.0.0.1:9696", "internal": "http://127.0.0.1:9696" },
    { "name": "neutron", "type": "network", "public": "http://127.0.0.1:9696",
      "admin": "http://127.0.0.1:9696", "internal": "http://127.0.0.1:9696" },
    { "name": "swift", "type": "object-store", "public": "http://127.0.0.1:8080/v1/AUTH_%(tenant_id)s",
      "admin": "http://127.0.0.1:8080/v1/AUTH_%(tenant_id)s", "internal": "http://127.0.0.1:8080/v1/AUTH_%(tenant_id)s"}
  ]
}"""


class RegisterRegion(object):
    """Class to register users with role assignments, services and endpoints"""
    def __init__(self):
        """constructor"""
        self.osclients = OpenStackClients()
        self.keystone = self.osclients.get_keystoneclient()
        self.password_changer = PasswordChanger(self.osclients)

    def service_exists(self, service_name, service_type):
        """

        :param service_name:
        :param service_type:
        :return:
        """
        try:
            service = self.keystone.services.find(name=service_name)
        except NotFound:
            service = self.keystone.services.create(name=service_name, type=service_type)
        return service.id


    def region_exists(self, region_id):
        """

        :param region_id:
        :return:
        """
        try:
            self.keystone.regions.find(id=region_id)
        except NotFound:
            self.keystone.regions.create(region_id)

    def project_exists(self, tenant_name, domain_id='default'):
        """

        :param tenant_name:
        :param domain_id:
        :return:
        """
        try:
            project = self.keystone.projects.find(name=tenant_name)
        except NotFound:
            project = self.keystone.projects.create(tenant_name, domain_id)
        return project.id

    def user_exists(self, username, password, set_passwords=False):
        """check that user exists, create him/her otherwise. If the user
        exists and set_password is True, it sets the password.

        :param username: the username of the user
        :param password: the password of the user
        :param set_passwords: if True and the user exists, change the password
        :return: the user object
        """
        try:
            user = self.keystone.users.find(name=username)
            if set_passwords:
                self.password_changer.change_password(user, password)
        except NotFound:
            user = self.keystone.users.create(name=username, password=password)
        return user

    def endpoint_exists(self, service_id, interface, url, region):
        """

        :param service_id:
        :param interface:
        :param url:
        :param region:
        :return:
        """
        result = self.keystone.endpoints.list(service=service_id, interface=interface, region=region)
        if not result:
            result = self.keystone.endpoints.create(service=service_id, interface=interface,
                                                    url=url, region=region)
        else:
            result = result[0]
            if result.url != url:
                self.keystone.endpoints.update(result.id, url=url)
        return result.id

    def register_region(self, region, set_passwords=False):
        region_name = region['region']
        self.region_exists(region_name)

        for user in region['users']:
            userobj = self.user_exists(user['username'], user['password'])
            admin_role = self.keystone.roles.find(name='admin')
            if user['username'].startswith('admin-'):
                # admin users use their own tenant instead of the service one
                project = self.project_exists(user['username'])
            else:
                project = self.project_exists('service')

            self.keystone.roles.grant(admin_role, user=userobj, project=project)

        for s in region['services']:
            service_id = self.service_exists(s['name'], s['type'])
            self.endpoint_exists(service_id, 'public', s['public'], region_name)
            self.endpoint_exists(service_id, 'admin', s['admin'], region_name)
            self.endpoint_exists(service_id, 'internal', s['internal'], region_name)

    @staticmethod
    def transform_json(data, env):
        """Utility method, to expand ${VAR} and $VAR in data, using env
        variables

        :param data: the template to process
        :param env: array with the variables
        :return: the template with the variables expanded
        """
        var_shell_pattern_c = re.compile(r'\${{(\w+)}}')
        var_shell_pattern = re.compile(r'\$(\w+)')
        data = data.replace('{', '{{')
        data = data.replace('}', '}}')
        data = var_shell_pattern_c.sub(r'{\1}', data)
        data = var_shell_pattern.sub(r'{\1}', data)
        return data.format(**env)

    def register_regions(self, regions_json=default_region_json, env=os.environ):
        """

        :param regions_json:
        :param env:
        :return:
        """
        regions_json = self.transform_json(regions_json, env)
        region = json.loads(regions_json)
        if 'SET_OPENSTACK_PASSWORDS' in env:
            set_passwords = True
        else:
            set_passwords = False
        if 'regions' in region:
            # This is an array of regions
            for r in region:
                self.register_region(r, set_passwords)
        else:
            # This is an only region
            self.register_region(region, set_passwords)

if __name__ == '__main__':
    register = RegisterRegion()
    if len(sys.argv) == 2:
        json_data = open(sys.argv[1]).read()
        register.register_regions(json_data)
    else:
        register.register_regions()