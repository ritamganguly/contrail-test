import os
import sys
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('scripts/tcutils/pkgs/Traffic'))
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from base import BaseRtFilterTest
from common import isolated_creds
import inspect

import test

class TestBasicRTFilter(BaseRtFilterTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicRTFilter, cls).setUpClass()

    #@preposttest_wrapper
    def test_vn_rt_entry(self):
        ''' Validate the entry of the VN's Route Target in the rt_group and  bgp.rtarget.0 table on the control nodes

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        route_target= vn1_fixture.rt_names[0]
        for bgp_ip in self.inputs.bgp_ips:
            self.verify_rt_group_entry(bgp_ip, route_target) 
        self.logger.info('Will create a VM and check that the dep_route is created in the rt_group table')
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        ip= vm1_fixture.vm_ip + '/32'
        active_ctrl_node= self.get_active_control_node(vm1_fixture) 
        self.verify_rt_group_entry(active_ctrl_node, route_target)
        self.verify_dep_rt_entry(active_ctrl_node, route_target, ip)
        self.verify_rtarget_table_entry(active_ctrl_node, route_target)
        return True
    #end test_vn_rt_entry
 
    #@preposttest_wrapper
    def test_user_def_rt_entry(self):
        ''' Validate the entry and deletion of the VN's user-added Route Target in the rt_group and  bgp.rtarget.0 table on the control nodes

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        user_def_rt_num = '11111'
        user_def_rt= "target:%s:%s" % (self.inputs.router_asn, user_def_rt_num)
        system_rt= vn1_fixture.rt_names[0]
        routing_instance = vn1_fixture.ri_name
        self.logger.info('Will add a user-defined RT to the VN')
        vn1_fixture.add_route_target(routing_instance, self.inputs.router_asn, user_def_rt_num)  
        sleep(5)
        rt_list= [user_def_rt, system_rt]
        for bgp_ip in self.inputs.bgp_ips:
            for rt in rt_list:
                self.verify_rt_group_entry(bgp_ip, rt)
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        ip= vm1_fixture.vm_ip + '/32'
        active_ctrl_node= self.get_active_control_node(vm1_fixture)
        for rt in rt_list:
            self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            self.verify_rtarget_table_entry(active_ctrl_node, rt)
        self.logger.info('Will remove the user-defined RT to the VN and verify that the entry is removed from the tables')
        vn1_fixture.del_route_target(routing_instance, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        self.verify_rt_entry_removal(active_ctrl_node, user_def_rt)
        self.logger.info('Will verify that the system generated RT is still seen in the control-nodes')
        self.verify_rt_group_entry(active_ctrl_node, system_rt)
        self.verify_dep_rt_entry(active_ctrl_node, system_rt, ip)
        self.verify_rtarget_table_entry(active_ctrl_node, system_rt)   
        return True
    #end test_user_def_rt_entry
 
    #@preposttest_wrapper
    def test_rt_entry_persistence_across_restarts(self):
        ''' Validate the persistence of Route Target entry in the rt_group and bgp.rtarget.0 table on the control nodes
            across control-node/agent service restarts

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        
        user_def_rt_num = '11111'
        user_def_rt= "target:%s:%s" % (self.inputs.router_asn, user_def_rt_num)
        system_rt= vn1_fixture.rt_names[0]
        routing_instance = vn1_fixture.ri_name
        self.logger.info('Will add a user-defined RT to the VN')
        vn1_fixture.add_route_target(routing_instance, self.inputs.router_asn, user_def_rt_num)  
        sleep(10)
        ip= vm1_fixture.vm_ip + '/32'
        active_ctrl_node= self.get_active_control_node(vm1_fixture)
        
        rt_list= [user_def_rt, system_rt]
        self.logger.info('Verifying both the user-defined RT and the system-generated RT')
        for rt in rt_list:
            self.verify_rt_group_entry(active_ctrl_node, rt)
            self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            self.verify_rtarget_table_entry(active_ctrl_node, rt) 
        
        self.logger.info('Will restart contrail-vrouter service and check if the RT entries persist')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)                                                                                                                                                                                                                                                             
        self.logger.info('Verifying both the user-defined RT and the system-generated RT')
        for rt in rt_list:
            self.verify_rt_group_entry(active_ctrl_node, rt)
            self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            self.verify_rtarget_table_entry(active_ctrl_node, rt)
        
        self.logger.info('Will restart contrail-control service and check if the RT entries persist')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        self.logger.info('Sleeping for 30 seconds')
        sleep(30)                                                                                                                                                                                                                                                             
        self.logger.info('Verifying both the user-defined RT and the system-generated RT')
        for rt in rt_list:
            self.verify_rt_group_entry(active_ctrl_node, rt)
            self.verify_dep_rt_entry(active_ctrl_node, rt, ip)
            self.verify_rtarget_table_entry(active_ctrl_node, rt)
        return True
    #end test_rt_entry_persistence_across_restarts

    #@preposttest_wrapper
    def test_vpnv4_route_entry_only_on_RT_interest_receipt(self):
        ''' Validate the presence of route in the bgp.l3vpn.0 table only when a RT interest is generated
        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        result= True
        self.logger.info('*With RT-Filtering enabled, we should not see route 0/0 from Mx in the bgp.l3vpn.0 table*')
        active_ctrl_node= self.get_active_control_node(vm1_fixture)
        def_rt= self.cn_inspect[active_ctrl_node].get_cn_vpnv4_table('0.0.0.0/0')
        if def_rt:
            result= False
        else:
            self.logger.info('0/0 not seen in the bgp.l3vpn.0 table')
        assert result, '0/0 seen in the bgp.l3vpn.0 table'

        self.remove_rt_filter_family()
        self.logger.info('*Will disable RT_filter Address family between control-nodes and MX*')
        sleep(10)
        self.logger.info('*Now we should be able to see all routes from Mx in the bgp.l3vpn.0 table, including 0/0*')
        def_rt= self.cn_inspect[active_ctrl_node].get_cn_vpnv4_table('0.0.0.0/0')
        if def_rt:
            self.logger.info('0/0 seen in the bgp.l3vpn.0 table')
        else:
            result= False
        assert result, '0/0 not seen in the bgp.l3vpn.0 table even after removing RT_filter Family'

        self.add_rt_filter_family()
        self.logger.info('*Will re-enable RT_filter Address family between control-nodes and MX*')
        sleep(10)
        self.logger.info('*Now the 0/0 route should be withdrawn from the bgp.l3vpn.0 table*')
        def_rt= self.cn_inspect[active_ctrl_node].get_cn_vpnv4_table('0.0.0.0/0')
        if def_rt:
            result= False
        else:
            self.logger.info('0/0 not seen in the bgp.l3vpn.0 table')
        assert result, '0/0 seen in the bgp.l3vpn.0 table after adding RT_filter Family'
        
        return True
    #end test_vpnv4_route_entry_only_on_RT_interest_receipt
 
    #@preposttest_wrapper
    def test_dep_routes_two_vns_with_same_rt(self):
        ''' Validate that dep_routes are seen in the RTGroup Table under the route-target which is common to two different networks

        '''
        vn1_name = get_random_name('vn30')
        vn2_name = get_random_name('vn40')
        vn1_subnets = [get_random_cidr()]
        vn2_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vm1')
        vn2_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        assert vn2_fixture.verify_on_setup()
        user_def_rt_num = '11111'
        user_def_rt= "target:%s:%s" % (self.inputs.router_asn, user_def_rt_num)
        system_rt1= vn1_fixture.rt_names[0]
        system_rt2= vn2_fixture.rt_names[0] 
        routing_instance1 = vn1_fixture.ri_name
        routing_instance2 = vn2_fixture.ri_name
        self.logger.info('Will add a user-defined RT to the two VNs')
        vn1_fixture.add_route_target(routing_instance1, self.inputs.router_asn, user_def_rt_num)
        vn2_fixture.add_route_target(routing_instance2, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        vm2_fixture = self.create_vm(vn2_fixture,vm_name=vn2_vm2_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm2_fixture.wait_till_vm_is_up()                               
        ip1= vm1_fixture.vm_ip + '/32'
        ip2= vm2_fixture.vm_ip + '/32'
        active_ctrl_node= self.get_active_control_node(vm1_fixture)
        self.verify_dep_rt_entry(active_ctrl_node, user_def_rt, ip1)
        self.verify_dep_rt_entry(active_ctrl_node, user_def_rt, ip2)
        self.logger.info('Will remove the user-defined RT on VN2 and verify that the entry is removed from the tables')
        self.logger.info('The entry for VM1 should still persist')
        vn2_fixture.del_route_target(routing_instance2, self.inputs.router_asn, user_def_rt_num)
        sleep(5)
        self.verify_dep_rt_entry_removal(active_ctrl_node, user_def_rt, ip2)
        self.verify_dep_rt_entry(active_ctrl_node, user_def_rt, ip1)
        return True
    #end test_dep_routes_two_vns_with_same_rt
