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
author = 'chema'

import time
import logging

import impersonate
from osclients import OpenStackClients
from nova_resources import NovaResources
from glance_resources import GlanceResources
from cinder_resources import CinderResources
from neutron_resources import NeutronResources
from blueprint_resources import BluePrintResources
from swift_resources import SwiftResources


class UserResources(object):
    """Class to list, delete user resources. Also provides a method to stop all
    the VM of the tenant.

    This class works creating a instance with the credential of the user owner
    of the resources. It does not use an admin credential!!!"""
    def __init__(self, username, password, tenant_id=None, tenant_name=None,
                 trust_id=None):
        """
        Constructor of the class. Tenant-id or tenant_name or tust_id must be
        provided.

        :param username: the username of the user whose resources are deleted
          or from the user that impersonate them
        :param password: the password of the user whose resources are deleted
          or from the user that impersonate them
        :param tenant_id: the tenant id of the user whose resources must be
        deleted.
        :param tenant_name: the tenant name of the user whose reources must be
         deleted
        :param trust_id: the trust_id use to impersonate the user
        :return: nothing
        """

        self.logger = logging.getLogger(__name__)
        self.clients = OpenStackClients()
        if tenant_id:
            self.clients.set_credential(username, password,
                                        tenant_id=tenant_id)
        elif tenant_name:
            self.clients.set_credential(username, password,
                                        tenant_name=tenant_name)
        elif trust_id:
            self.clients.set_credential(username, password, trust_id=trust_id)
            self.trust_id = trust_id
        else:
            raise(
                'Either tenant_id or tenant_name or trust_id must be provided')

        self.user_id = self.clients.get_session().get_user_id()
        session = self.clients.get_session()
        self.user_name = session.auth.get_access(session)
        self.nova = NovaResources(self.clients)
        self.cinder = CinderResources(self.clients)
        self.glance = GlanceResources(self.clients)
        self.neutron = NeutronResources(self.clients)
        self.blueprints = BluePrintResources(self.clients)
        self.swift = SwiftResources(self.clients)
        # Images in use is a set used to avoid deleting formerly glance images
        # in use by other tenants
        self.imagesinuse = set()

    def delete_tenant_resources_pri_1(self):
        """Delete here all the elements that do not depend of others are
        deleted first"""

        try:
            self.nova.delete_user_keypairs()
        except Exception, e:
            self.logger.error('Deletion of keypairs failed')

        # Snapshots must be deleted before the volumes, because a snapshot
        # depends of a volume.
        try:
            self.cinder.delete_tenant_volume_snapshots()
        except Exception, e:
            self.logger.error('Deletion of volume snaphosts failed')

        # Blueprint instances must be deleted before VMs, instances before
        # templates
        try:
            self.blueprints.delete_tenant_blueprints()
        except Exception, e:
            self.logger.error('Deletion of blueprints failed')

        try:
            self.cinder.delete_tenant_backup_volumes()
        except Exception, e:
            self.logger.error('Deletion of backup volumes failed')

        try:
            self.swift.delete_tenant_containers()
        except Exception, e:
            self.logger.error('Deletion of swift containers failed')

    def delete_tenant_resources_pri_2(self):
        """Delete resources that must be deleted after p1 resources"""
        # VMs and blueprint templates should be deleted after blueprint
        # instances.

        count = 0
        while self.blueprints.get_tenant_blueprints() and count < 120:
            time.sleep(1)
            count += 1
        try:
            self.nova.delete_tenant_vms()
        except Exception, e:
            self.logger.error('Deletion of VMs failed')

        # Blueprint instances must be deleted after blueprint templates
        try:
            self.blueprints.delete_tenant_templates()
        except Exception, e:
            self.logger.error('Deletion of blueprint templates failed')

    def delete_tenant_resources_pri_3(self):
        """Delete resources that must be deleted after p2 resources"""
        count = 0
        while self.nova.get_tenant_vms() and count < 120:
            time.sleep(1)
            count += 1

        # security group, volumes, network ports, images, floating ips,
        # must be deleted after VMs
        try:
            self.nova.delete_tenant_security_groups()
        except Exception, e:
            self.logger.error('Deletion of security groups failed')

        # self.glance.delete_tenant_images()
        try:
            self.glance.delete_tenant_images_notinuse(self.imagesinuse)
        except Exception, e:
            self.logger.error('Deletion of images failed')

        # Before deleting volumes, snapshot volumes must be deleted
        while self.cinder.get_tenant_volume_snapshots():
            time.sleep(1)

        try:
            self.cinder.delete_tenant_volumes()
        except Exception, e:
            self.logger.error('Deletion of volumes failed')


        try:
            self.neutron.delete_tenant_ports()
        except Exception, e:
            self.logger.error('Deletion of network ports failed')

        try:
            self.neutron.delete_tenant_securitygroups()
        except Exception, e:
            self.logger.error('Deletion of network security groups failed')

        try:
            self.neutron.delete_tenant_floatingips()
        except Exception, e:
            self.logger.error('Deletion of floating ips failed')

        try:
            self.neutron.delete_tenant_subnets()
        except Exception, e:
            self.logger.error('Deletion of subnets failed')

        try:
            self.neutron.delete_tenant_networks()
        except Exception, e:
            self.logger.error('Deletion of networks failed')

        try:
            self.neutron.delete_tenant_routers()
        except Exception, e:
            self.logger.error('Deletion of routers failed')

    def delete_tenant_resources(self):
        """Delete all the resources of the tenant, and also the keypairs of the
        user"""
        self.delete_tenant_resources_pri_1()
        time.sleep(10)
        self.delete_tenant_resources_pri_2()
        self.delete_tenant_resources_pri_3()


    def stop_tenant_vms(self):
        """Stop all the active vms of the tenant"""
        self.nova.stop_tenant_vms()

    def unshare_images(self):
        """Make private all the tenant public images"""
        self.glance.unshare_images()

    def get_resources_dict(self):
        """return a dictionary of sets with the ids of the user's resources
        :return: a dictionary with the user's resources
        """
        resources = dict()
        resources['blueprints'] = set(self.blueprints.get_tenant_blueprints())
        resources['templates'] = set(self.blueprints.get_tenant_templates())
        resources['keys'] = set(self.nova.get_user_keypairs())
        resources['vms'] = set(self.nova.get_tenant_vms())
        resources['security_groups'] = set(
            self.nova.get_tenant_security_groups())
        resources['images'] = self.glance.get_tenant_images()
        resources['volumesnapshots'] = set(
            self.cinder.get_tenant_volume_snapshots())
        resources['volumes'] = set(self.cinder.get_tenant_volumes())
        resources['backupvolumes'] = set(
            self.cinder.get_tenant_backup_volumes())
        resources['floatingips'] = set(
            self.neutron.get_tenant_floatingips())
        resources['networks'] = set(
            self.neutron.get_tenant_networks())
        resources['nsecuritygroups'] = set(
            self.neutron.get_tenant_securitygroups())
        resources['routers'] = set(self.neutron.get_tenant_routers())
        resources['subnets'] = set(self.neutron.get_tenant_subnets())
        resources['ports'] = set(self.neutron.get_tenant_ports())
        resources['objects'] = set(self.swift.get_tenant_objects())
        return resources

    def print_tenant_resources(self):
        """print all the tenant's resources"""
        print 'Tenant id is: ' + self.clients.get_session().get_project_id()
        print 'User id is: ' + self.clients.get_session().get_user_id()

        print 'Tenant blueprint instances: '
        print self.blueprints.get_tenant_blueprints()
        print 'Tenant blueprint templates: '
        print self.blueprints.get_tenant_templates()

        print 'User keypairs:'
        print self.nova.get_user_keypairs()
        print 'Tenant VMs:'
        print self.nova.get_tenant_vms()
        print 'Tenant security groups (nova):'
        print self.nova.get_tenant_security_groups()

        print 'Tenant images:'
        print self.glance.get_tenant_images()

        print 'Tenant volume snapshots:'
        print self.cinder.get_tenant_volume_snapshots()
        print 'Tenant volumes:'
        print self.cinder.get_tenant_volumes()
        print 'Tenant backup volumes:'
        print self.cinder.get_tenant_backup_volumes()

        print 'Tenant floating ips:'
        print self.neutron.get_tenant_floatingips()
        print 'Tenant networks:'
        print self.neutron.get_tenant_networks()
        print 'Tenant security groups (neutron):'
        print self.neutron.get_tenant_securitygroups()
        print 'Tenant routers:'
        print self.neutron.get_tenant_routers()
        print 'Tenant subnets'
        print self.neutron.get_tenant_subnets()
        print 'Tenant ports'
        print self.neutron.get_tenant_ports()
        print 'Containers'
        print self.swift.get_tenant_containers()

    def free_trust_id(self):
        """Free trust_id, if it exists.

        :return: nothing
        """
        if self.trust_id:
            self.logger.info('Freeing trust-id')
            trust = impersonate.TrustFactory(self.clients)
            trust.delete_trust(self.trust_id)

