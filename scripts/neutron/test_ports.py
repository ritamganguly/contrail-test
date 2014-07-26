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
from util import *


class TestPorts(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestPorts, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPorts, cls).tearDownClass()

    @preposttest_wrapper
    def test_ports_attach_detach(self):
        '''Validate port attach/detach operations
        Create a port in a VN
        Create a VM using that port
        Detach the port
        
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        port_obj = self.quantum_fixture.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                        image_name='cirros-0.3.0-x86_64-uec',
                                        port_ids=[port_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                    image_name='cirros-0.3.0-x86_64-uec')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        if not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip):
            self.logger.error('Ping to a attached port %s failed' %
                              (vm1_fixture.vm_ip))
            result = result and False
        time.sleep(5)
        vm1_fixture.interface_detach(port_id=port_obj['id'])
        # No need to delete the port. It gets deleted on detach

        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error('VM %s is not ACTIVE(It is %s) after port-detach' % (
                vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False

        if not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip, expectation=False):
            self.logger.error('Ping to a detached port %s passed!' %
                              (vm1_fixture.vm_ip))
            result = result and False
        else:
            self.logger.info('Unable to ping to a detached port.. OK')

        # Now attach the interface again
        port_obj = self.quantum_fixture.create_port(net_id=vn1_fixture.vn_id)
        vm1_fixture.interface_attach(port_id=port_obj['id'])
        time.sleep(5)
        vm1_fixture.vm_obj.get()
        if vm1_fixture.vm_obj.status != 'ACTIVE':
            self.logger.error('VM %s is not ACTIVE(It is %s) during attach-detach' % (
                vn1_vm1_name, vm1_fixture.vm_obj.status))
            result = result and False
        if result and not vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip):
            self.logger.error('Ping to a attached port %s failed' %
                              (vm1_fixture.vm_ip))
            result = result and False

        return result
    # end test_ports_attach_detach
