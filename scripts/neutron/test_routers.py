# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time

from vn_test import *
from vm_test import *
from connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from neutron.base import BaseNeutronTest
import test
from tcutils.util import *


class TestRouters(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestRouters, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRouters, cls).tearDownClass()

    @preposttest_wrapper
    def test_basic_router_behavior(self):
        '''Validate a router is able to route packets between two VNs
        Create a router
        Create 2 VNs, and a VM in each
        Add router port from each VN
        Ping between VMs
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[0], 1)
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]
        vn2_gateway = get_an_ip(vn2_subnets[0], 1)
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn2_vm1_name = get_random_name('vn2-vm1')
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn2_vm1_fixture = self.create_vm(vn2_fixture, vn2_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)

        router_dict = self.create_router(router_name)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        router_ports = self.quantum_fixture.get_router_interfaces(
            router_dict['id'])
<<<<<<< HEAD
        router_port_ips = [item['fixed_ips'][0]['ip_address']
                           for item in router_ports]
=======
        router_port_ips = [ item['fixed_ips'][0]['ip_address'] 
                            for item in router_ports]
>>>>>>> 445f2a43b959de7eb8b684b49a9863430a8fd7de
        assert vn1_gateway in router_port_ips and \
            vn2_gateway in router_port_ips,\
            'One or more router port IPs are not gateway IPs'\
            'Router ports : %s' % (router_ports)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)
    # end test_basic_router_behavior

    @preposttest_wrapper
    def test_router_rename(self):
        ''' Test router rename
        '''
        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_update_dict = {'name': "test_router"}
        router_rsp = self.quantum_fixture.update_router(
            router_dict['id'],
            router_update_dict)
        assert router_rsp['router'][
            'name'] == "test_router", 'Failed to update router name'

    @preposttest_wrapper
    def test_router_admin_state_up(self):
        ''' Routing should not work with router's admin_state_up set to False
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn2_vm1_name = get_random_name('vn2-vm1')
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn2_vm1_fixture = self.create_vm(vn2_fixture, vn2_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)

        router_dict = self.create_router(router_name)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)
        router_update_dict = {'admin_state_up': False}
        router_rsp = self.quantum_fixture.update_router(
            router_dict['id'],
            router_update_dict)
        assert router_rsp['router'][
            'admin_state_up'] == False, 'Failed to update router admin_state_up'
        assert vn1_vm1_fixture.ping_with_certainty(
            vn2_vm1_fixture.vm_ip, expectation=False), 'Routing works with admin_state_up set to False not expected'
        router_update_dict = {'admin_state_up': True}
        router_rsp = self.quantum_fixture.update_router(
            router_dict['id'],
            router_update_dict)
        assert router_rsp['router'][
            'admin_state_up'], 'Failed to update router admin_state_up'
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)

    def test_router_with_existing_ports(self):
        '''Validate routing works by using two existing ports
        Create a router
        Create 2 VNs, and a VM in each
        Create two ports in each of these VNs
        Attach these two ports to the router
        Ping between VMs
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn2_vm1_name = get_random_name('vn2-vm1')
        router_name = get_random_name('router1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn2_vm1_fixture = self.create_vm(vn2_fixture, vn2_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip,
                                                   expectation=False)

        port1_obj = self.quantum_fixture.create_port(
            net_id=vn1_fixture.vn_id)
        port2_obj = self.quantum_fixture.create_port(
            net_id=vn2_fixture.vn_id)
        router_dict = self.create_router(router_name)
        self.add_router_interface(router_dict['id'], port_id=port1_obj['id'])
        self.add_router_interface(router_dict['id'], port_id=port2_obj['id'])
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip),\
            'Ping between VMs across router failed!'
    # end test_router_with_existing_ports
