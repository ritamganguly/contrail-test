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
from tcutils.util import get_an_ip

class TestSubnets(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestSubnets, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestSubnets, cls).tearDownClass()

    @preposttest_wrapper
    def test_subnet_host_routes(self):
        '''Validate host_routes parameter in subnet
        Create a VN with subnet having a host-route
        Create a VM using that subnet
        Check the route table in the VM
        
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[0], 1)
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
        assert dest_ip in route_output, 'Route pushed from DHCP is not '\
                         'present in Route table of the VM'
        self.logger.info('Route pushed from DHCP is present in route-table '
                        ' of the VM..OK')

        self.logger.info('Updating the subnet to remove the host routes')
        vn1_subnet_dict = {'host_routes' : []}
        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'], 
                                  vn1_subnet_dict)
        time.sleep(5)
        vm1_fixture.reboot()
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        route_output = output.values()[0]
        assert dest_ip not in route_output, 'Route pushed from DHCP is still '\
                         'present in Route table of the VM'
        self.logger.info('Route table in VM does not have the host routes..OK')
        assert vn1_gateway in route_output, 'Default Gateway is missing the \
                        route table of the VM'
    # end test_subnet_host_routes

    @preposttest_wrapper
    def test_dns_nameservers(self):
        '''Validate dns-nameservers parameter in subnet
        Create a VN with subnet having a dns-nameserver
        Create a VM using that subnet
        Check the resolv.conf in the VM
        
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_gateway = get_an_ip(vn1_subnets[1])
        dns1_ip = '8.8.8.8'
        dns2_ip = '4.4.4.4'
        vn1_subnets = [{'cidr': vn1_subnets[0],
                       'dns_nameservers': [dns1_ip, dns2_ip]
                       }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        route_output = output.values()[0]
        assert dns1_ip in route_output, 'DNS Server IP %s not seen in '\
                         'resolv.conf of the VM' % (dns1_ip)
        assert dns2_ip in route_output, 'DNS Server IP %s not seen in '\
                         'resolv.conf of the VM' % (dns2_ip)
        self.logger.info('DNS Server IPs are seen in resolv.conf of the VM')

        self.logger.info('Updating the subnet to remove the dns servers')
        vn1_subnet_dict = {'dns_nameservers' : []}
        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'], 
                                  vn1_subnet_dict)
        vm1_fixture.reboot()
        time.sleep(5)
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['cat /etc/resolv.conf'])
        dns_output = output.values()[0]
        assert dns1_ip not in dns_output, 'DNS Server IP %s still seen '\
                         ' in resolv.conf of the VM' % (dns1_ip)
        assert dns2_ip not in dns_output, 'DNS Server IP %s still seen '\
                         ' in resolv.conf of the VM' % (dns2_ip)
        assert vn1_gateway in dns_output, 'DNS Server IP %s not seen '\
                         ' in resolv.conf of the VM' % (vn1_gateway)
        self.logger.info('Route table in VM does not have the host routes..OK')
        assert vn1_gateway in route_output, 'Default Gateway is missing the \
                        route table of the VM'
    # end test_dns_nameservers

    @preposttest_wrapper
    def test_gateway(self):
        '''Validate that GW of first address of the subnet cidr is chosen by
        default. 
        Check that gw cannot be from within the allocation pool
        Check that custom addresses can be given
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr()
        vn1_gateway = get_an_ip(vn1_subnet_cidr, 1)
        vn1_subnets = [{'cidr': vn1_subnet_cidr,
                      'allocation_pools':[{'start': get_an_ip(vn1_subnet_cidr,3),
                                         'end':get_an_ip(vn1_subnet_cidr,10)}],
                       }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                    image_name='cirros-0.3.0-x86_64-uec')
        assert vm1_fixture.wait_till_vm_is_up()
        output = vm1_fixture.run_cmd_on_vm(['route -n'])
        route_output = output.values()[0]
        assert vn1_gateway in route_output, 'First address of CIDR %s : %s'\
                'is NOT set as gateway on the VM' % (vn1_subnet_cidr, vn1_gateway)
        self.logger.info('First address of CIDR %s : %s'\
                'is set as gateway on the VM' % (vn1_subnet_cidr, vn1_gateway))

        # Updating the gateway is not supported. Comment it for now
#        self.logger.info('Try updating gateway ip to be within the alloc pool')
#        vn1_subnet_dict = {'gateway_ip' : get_an_ip(vn1_subnet_cidr,5)}
#        self.assertRaises(CommonNetworkClientException,
#                                vn1_fixture.update_subnet,
#                                vn1_fixture.vn_subnet_objs[0]['id'], 
#                                vn1_subnet_dict)

        # Updating Gateway is not supported. for now, disable the below code
#        self.logger.info('Updating to valid GW IP and checking if VM gets it')
#        gw_plus1_ip = get_an_ip(vn1_subnet_cidr, 2)
#        vn1_subnet_dict = {'gateway_ip' : gw_plus1_ip}
#        vn1_fixture.update_subnet(vn1_fixture.vn_subnet_objs[0]['id'],
#                                  vn1_subnet_dict)
#        vm1_fixture.reboot()
#        time.sleep(5)
#        assert vm1_fixture.wait_till_vm_is_up()
#        output = vm1_fixture.run_cmd_on_vm(['route -n| grep ^0.0.0.0'])
#        route_output = output.values()[0]
#        assert gw_plus1_ip in route_output, 'VM has not got the modified GWIP'\
#                            ' %s' % (gw_plus1_ip)
#        self.logger.info('VM has got the modified GW IP %s' % (gw_plus1_ip))
    # end test_gateway

    @preposttest_wrapper
    def test_allocation_pools(self):
        '''Validate allocation pool config

        Create a VN with subnet having allocation pool
        Verify VMs are only created when alloc pool is available
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr('29')
        vn1_gateway = get_an_ip(vn1_subnet_cidr, 1)
        # Leave out the second IP...start from 3
        vn1_subnets = [{'cidr': vn1_subnet_cidr,
                       'allocation_pools': [
                            {'start': get_an_ip(vn1_subnet_cidr,3),
                             'end': get_an_ip(vn1_subnet_cidr,6)
                            }],
                       }]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name, 
                                    image_name='cirros-0.3.0-x86_64-uec')
        assert vm1_fixture.wait_till_vm_status('ACTIVE'), 'VM %s should '\
           'have been ACTIVE' % (vm1_fixture.vm_name)
        vm2_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm2_fixture.wait_till_vm_status('ACTIVE'), 'VM %s should '\
           'have been ACTIVE' % (vm2_fixture.vm_name)
        vm3_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm3_fixture.wait_till_vm_status('ACTIVE'), 'VM %s should '\
           'have been ACTIVE' % (vm3_fixture.vm_name)
        vm4_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm4_fixture.wait_till_vm_status('ACTIVE'), 'VM %s should '\
           'have been ACTIVE' % (vm4_fixture.vm_name)
        vm5_fixture = self.create_vm(vn1_fixture, get_random_name('vn1-vm1'),
                                     image_name='cirros-0.3.0-x86_64-uec')
        assert vm5_fixture.wait_till_vm_status('ERROR'), 'VM %s should '\
           'have failed since allocation pool is full' % (vm5_fixture.vm_name)
    # end test_allocation_pools
