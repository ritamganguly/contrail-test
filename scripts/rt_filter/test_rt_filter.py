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
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.wait_till_vm_is_up()
        
        route_target= vn1_fixture.rt_names[0]
        ip= vm1_fixture.vm_ip + '/32'
        active_ctrl_node= self.get_active_control_node(vm1_fixture)
        self.verify_rt_entry(active_ctrl_node, route_target, ip)
        
        return True
    #end test_vn_rt_entry
        
    def verify_rt_entry(self, control_node, route_target, ip):
        
        rt_group_entry= self.cn_inspect[control_node].get_cn_rtarget_group(route_target)
        rt_table_entry= self.cn_inspect[control_node].get_cn_rtarget_table()
        result= False
        sub_result= False
        for rt_entry in rt_table_entry:
            if route_target in rt_entry['prefix']:
                result= True
                self.logger.info('RT %s seen in the bgp.rtarget.0 table of the control nodes'%route_target)
                break
        assert result,'RT %s not seen in the bgp.rtarget.0 table of the control nodes'%route_target
        if rt_group_entry is None:
            result= False
            assert result, 'No entry for RT %s seen in the control nodes'%route_target
        else:
            result= True
            self.logger.info('RT %s seen in the control nodes'%route_target)
            for y in rt_group_entry['dep_route']:
                if ip in y:
                    sub_result= True
                    self.logger.info('IP %s is seen in the dep_routes'%ip)
                    break
        assert sub_result, 'IP %s is not seen in the dep_routes'%ip
        return True
    #end verify_rt_entry

    def get_active_control_node(self, vm):
        active_controller = None
        inspect_h1 = self.agent_inspect[vm.vm_node_ip]
        agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
                new_controller = self.inputs.host_data[active_controller]['host_ip']
                self.logger.info('Active control node is %s' % new_controller)
        return new_controller

    #end get_active_control_node
