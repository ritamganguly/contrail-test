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
        '''Validate a router is able to route packets between tow VNs
        Create a router
        Create 2 VNs, and a VM in each
        Add router port from each VN
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

        router_dict = self.create_router(router_name)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        self.add_vn_to_router(router_dict['id'], vn2_fixture)
        assert vn1_vm1_fixture.ping_with_certainty(vn2_vm1_fixture.vm_ip)
    # end test_basic_router_behavior


