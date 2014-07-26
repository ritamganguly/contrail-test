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

class TestSubnets(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestSubnets, cls).setUpClass()

    def runTest(self):
        pass

    @classmethod
    def tearDownClass(cls):
        super(TestSubnets, cls).tearDownClass()

#    @test.attr(type='abcd')
    @preposttest_wrapper
    def test_subnet_host_routes(self):
        '''Validate host_routes parameter in subnet
        Create a VN with subnet having a host-route
        Create a VM using that subnet
        Check the route table in the VM
        
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = self.get_gateway(vn1_subnets[0])
        dest_ip = '8.8.8.8'
        destination = dest_ip + '/32'
        # nh IP does not matter, it will always be the default gw
        nh = '30.1.1.10'
        vn1_subnets = [{'cidr': vn1_subnets[0],
                       'host_routes': [{'destination': destination,
                                       'nexthop': nh},
                                       {'destination': '0.0.0.0/0',
                                       'nexthop': vn1_gateway}],
                       }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        route_output = output.values()[0]
        assert dest_ip in route_output, 'Route pushed from DHCP is not \
                         present in Route table of the VM'
        self.logger.info('Route pushed from DHCP is present in route-table '
                        ' of the VM..OK')
    # end test_subnet_host_routes
