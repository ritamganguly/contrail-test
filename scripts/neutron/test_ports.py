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
from netaddr import IPNetwork, IPAddress


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


    @preposttest_wrapper
    def test_ports_specific_subnet(self):
        '''Create ports from specific subnets

        Create a port in a VN with 2 subnets. 
        Validate that port can be created in any of the subnets
        Ping between them should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vn1_subnet1_id = vn1_fixture.vn_subnet_objs[0]['id']
        vn1_subnet2_id = vn1_fixture.vn_subnet_objs[1]['id']
        port1_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    subnet_id=vn1_subnet1_id)
        port2_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    subnet_id=vn1_subnet2_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                        image_name='cirros-0.3.0-x86_64-uec',
                                        port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                    image_name='cirros-0.3.0-x86_64-uec',
                                    port_ids=[port2_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.assertEqual(vm1_fixture.vm_ip,
          port1_obj['fixed_ips'][0]['ip_address'],'VM IP and Port IP Mismatch')
        self.assertEqual(vm2_fixture.vm_ip,
          port2_obj['fixed_ips'][0]['ip_address'],'VM IP and Port IP Mismatch')
        assert IPAddress(vm1_fixture.vm_ip) in IPNetwork(vn1_subnet_1),\
            'Port IP %s not from subnet %s' % (vm1_fixture.vm_ip, vn1_subnet_1)
        assert IPAddress(vm2_fixture.vm_ip) in IPNetwork(vn1_subnet_2),\
            'Port IP %s not from subnet %s' % (vm2_fixture.vm_ip, vn1_subnet_2)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' %( vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_subnet

    @preposttest_wrapper
    def test_ports_specific_subnet_ip(self):
        '''Create ports with specific Subnet and IP

        Create two ports in a VN with 2 subnets and specific IPs
        Attach to two VMs
        Ping between them should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vn1_subnet1_id = vn1_fixture.vn_subnet_objs[0]['id']
        vn1_subnet2_id = vn1_fixture.vn_subnet_objs[1]['id']
        vn1_subnet1_ip = get_an_ip(vn1_fixture.vn_subnet_objs[0]['cidr'], 5)
        vn1_subnet2_ip = get_an_ip(vn1_fixture.vn_subnet_objs[1]['cidr'], 5)
        port1_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    subnet_id=vn1_subnet1_id,
                    ip_address=vn1_subnet1_ip)
        port2_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    subnet_id=vn1_subnet2_id,
                    ip_address=vn1_subnet2_ip)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                        image_name='cirros-0.3.0-x86_64-uec',
                                        port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                    image_name='cirros-0.3.0-x86_64-uec',
                                    port_ids=[port2_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.assertEqual(vm1_fixture.vm_ip,
          vn1_subnet1_ip, 'VM IP and Port IP Mismatch')
        self.assertEqual(vm2_fixture.vm_ip,
          vn1_subnet2_ip, 'VM IP and Port IP Mismatch')
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' %( vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_subnet_ip

    @preposttest_wrapper
    def test_ports_specific_mac(self):
        '''Create ports with specific MAC

        Create two ports in a VN with 2 specific MACs
        Attach to two VMs
        Ping between them should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_subnet_2 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1, vn1_subnet_2])
        vm1_mac = '00:00:00:00:00:01'
        vm2_mac = '00:00:00:00:00:02'

        port1_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    mac_address=vm1_mac)
        port2_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    mac_address=vm2_mac)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                        image_name='cirros-0.3.0-x86_64-uec',
                                        port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                    image_name='cirros-0.3.0-x86_64-uec',
                                    port_ids=[port2_obj['id']])
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm1_tap_intf = vm1_fixture.tap_intf[vm1_fixture.vn_fq_names[0]]
        vm2_tap_intf = vm2_fixture.tap_intf[vm2_fixture.vn_fq_names[0]]
        assert vm1_tap_intf['mac_addr'] == vm1_mac, ''\
          'VM MAC %s is not the same as configured %s' % (
                    vm1_tap_intf['mac_addr'],vm1_mac)
        assert vm2_tap_intf['mac_addr'] == vm2_mac, ''\
          'VM MAC %s is not the same as configured %s' % (
                    vm2_tap_intf['mac_addr'],vm2_mac)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping between VMs %s, %s failed' %( vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
    # end test_ports_specific_mac

    @preposttest_wrapper
    def test_ports_no_sg(self):
        '''Create port with no SG

        Attach it to a VM
        Validate that another VM in the same VN is not able to reach this VM
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        port1_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    no_security_group=True)
        port2_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                        image_name='cirros-0.3.0-x86_64-uec',
                                        port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                    image_name='cirros-0.3.0-x86_64-uec',
                                    port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' %( vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), ''\
            'Ping from VM %s to %s, should have passed' %( vm2_fixture.vm_ip,
                                                vm1_fixture.vm_ip)
    # end test_ports_no_sg


    @preposttest_wrapper
    def test_ports_custom_sg(self):
        '''Create port with custom SG

        Attach it to a VM
        Validate with another VM that the SG applied is working
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_1 = get_random_cidr()
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, [vn1_subnet_1])

        sg1 = self.create_security_group(get_random_name('sg1'))

        port1_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id,
                    security_groups=[sg1['id']])
        port2_obj = self.quantum_fixture.create_port(
                    net_id=vn1_fixture.vn_id)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                        image_name='cirros-0.3.0-x86_64-uec',
                                        port_ids=[port1_obj['id']])
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                    image_name='cirros-0.3.0-x86_64-uec',
                                    port_ids=[port2_obj['id']])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM does not seem to be up'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' %( vm1_fixture.vm_ip,
                                                vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip,
                                               expectation=False), ''\
            'Ping from VM %s to %s, should have failed' %( vm2_fixture.vm_ip,
                                                vm1_fixture.vm_ip)
    # end test_ports_custom_sg
