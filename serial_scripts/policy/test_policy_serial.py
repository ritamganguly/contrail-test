from vn_test import VNFixture
from policy_test import PolicyFixture
from vm_test import VMFixture
from base import BaseSerialPolicyTest
from tcutils.wrappers import preposttest_wrapper
from sdn_topo_setup import sdnTopoSetupFixture
from system_verification import assertEqual
import system_verification 
from traffic_tests import trafficTestFixture
import time
import sdn_policy_traffic_test_topo


class TestSerialPolicy(BaseSerialPolicyTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestSerialPolicy, cls).setUpClass()

    @preposttest_wrapper
    def test_controlnode_switchover_policy_between_vns_traffic(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass
        with control-node switchover without any traffic drops
        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            self.logger.info(
                "Skiping Test. At least 2 control node required to run the test")
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        msg = []
        vn1_name = 'vn40'
        vn1_subnets = ['40.1.1.0/24']
        vn2_name = 'vn41'
        vn2_subnets = ['41.1.1.0/24']
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        policy3_name = 'policy3'
        policy4_name = 'policy4'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules,
                inputs=self.inputs,
                connections=self.connections))
        policy3_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy3_name,
                rules_list=rules1,
                inputs=self.inputs,
                connections=self.connections))
        policy4_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy4_name,
                rules_list=rev_rules1,
                inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets,
                policy_objs=[
                    policy1_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets,
                policy_objs=[
                    policy2_fixture.policy_obj]))
        assert vn2_fixture.verify_on_setup()
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic'))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vn1_vm2_name,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=True)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy1_name])
        assertEqual(result, True, msg)

        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        dpi = 9100
        proto = 'udp'
        expectedResult = {}
        for proto in traffic_proto_l:
            expectedResult[proto] = True if rules[0][
                'simple_action'] == 'pass' else False
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=vm1_fixture,
                rx_vm_fixture=vm2_fixture,
                stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, vm1_fixture.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
            assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = ["Traffic disruption is seen: details: "] + \
                traffic_stats['msg']
        assertEqual(traffic_stats['status'],
                    expectedResult[proto], err_msg)
        self.logger.info("-" * 80)

        # Figuring the active control node
        active_controller = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, active_controller))

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %
                         (active_controller))
        self.inputs.stop_service('contrail-control', [active_controller])
        self.addCleanup(self.inputs.start_service,
                        'contrail-control', [active_controller])
        time.sleep(5)

        # Check the control node shifted to other control node
        new_active_controller = None
        new_active_controller_state = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller = entry['controller_ip']
                new_active_controller_state = entry['state']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, new_active_controller))
        if new_active_controller == active_controller:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (active_controller, new_active_controller))
            result = False

        if new_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            status = True if stopStatus[proto] == [] else False
            if status != expectedResult[proto]:
                msg.append(stopStatus[proto])
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)
        assertEqual(result, True, msg)

        # bind the new policy to VN1
        self.logger.info("Bind the new policy to VN's..")
        policy_fq_name1 = [policy3_fixture.policy_fq_name]
        policy_fq_name2 = [policy4_fixture.policy_fq_name]
        vn1_fixture.bind_policies(policy_fq_name1, vn1_fixture.vn_id)
        time.sleep(5)
        # bind the new policy to VN2
        vn2_fixture.bind_policies(policy_fq_name2, vn2_fixture.vn_id)
        time.sleep(5)

        # policy deny applied traffic should fail
        self.logger.info(
            'Checking the ping between the VM with new policy(deny)')
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy3_name])
        assertEqual(result, True, msg)

        self.logger.info("Verify ping to vm %s" % (vn1_vm1_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm1_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy4_name])
        assertEqual(result, True, msg)

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (active_controller))
        self.inputs.start_service('contrail-control', [active_controller])

        time.sleep(10)
        # Check the BGP peering status from the currently active control node
        cn_bgp_entry = self.cn_inspect[
            new_active_controller].get_cn_bgp_neigh_entry()
        time.sleep(5)
        for entry in cn_bgp_entry:
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))

        # Stop on current Active node to simulate fallback
        self.logger.info("Will fallback to original primary control-node..")
        self.logger.info('Stoping the Control service in  %s' %
                         (new_active_controller))
        self.inputs.stop_service('contrail-control', [new_active_controller])
        self.addCleanup(self.inputs.start_service,
                        'contrail-control', [new_active_controller])
        time.sleep(5)

        # Check the control node shifted back to previous cont
        orig_active_controller = None
        orig_active_controller_state = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                orig_active_controller = entry['controller_ip']
                orig_active_controller_state = entry['state']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, orig_active_controller))
        if orig_active_controller == new_active_controller:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (self.new_active_controller, orig_active_controller))
            result = False

        if orig_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Check the ping
        self.logger.info(
            'Checking the ping between the VM again with new policy deny..')
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy3_name])
        assertEqual(result, True, msg)

        self.logger.info("Verify ping to vm %s" % (vn1_vm1_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=False)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm1_name, ret)
        self.logger.info(result_msg)
        if not ret:
            result = False
            msg.extend([result_msg, policy4_name])
        assertEqual(result, True, msg)

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (new_active_controller))
        self.inputs.start_service('contrail-control', [new_active_controller])
        if not result:
            self.logger.error('Switchover of control node failed')
            assert result
        return True
    # end test_controlnode_switchover_policy_between_vns_traffic

    @preposttest_wrapper
    def test_policy_single_vn_with_multi_proto_traffic(self):
        """ Call policy_test_with_multi_proto_traffic with single VN scenario.
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_1vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_with_multi_proto_traffic(topo)

    @preposttest_wrapper
    def test_policy_multi_vn_with_multi_proto_traffic(self):
        """ Call policy_test_with_multi_proto_traffic with multi VN scenario.
        """
        topology_class_name = sdn_policy_traffic_test_topo.sdn_2vn_2vm_config
        self.logger.info(
            "Scenario for the test used is: %s" %
            (topology_class_name))
        # set project name
        try:
            # provided by wrapper module if run in parallel test env
            topo = topology_class_name(
                project=self.project.project_name,
                username=self.project.username,
                password=self.project.password)
        except NameError:
            topo = topology_class_name()
        return self.policy_test_with_multi_proto_traffic(topo)

    def policy_test_with_multi_proto_traffic(self, topo):
        """ Pick 2 VM's for testing, have rules affecting icmp & udp protocols..
        Generate traffic streams matching policy rules - udp & icmp for now..
        assert if traffic failure is seen as no disruptive trigger is applied here..
        """
        result = True
        msg = []
        #
        # Test setup: Configure policy, VN, & VM
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup()
        #out= setup_obj.topo_setup(vm_verify='yes', skip_cleanup='yes')
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            topo, config_topo = out['data']
        # Setup/Verify Traffic ---
        # 1. Define Traffic Params
        test_vm1 = topo.vmc_list[0]  # 'vmc0'
        test_vm2 = topo.vmc_list[1]  # 'vmc1'
        test_vm1_fixture = config_topo['vm'][test_vm1]
        test_vm2_fixture = config_topo['vm'][test_vm2]
        test_vn = topo.vn_of_vm[test_vm1]  # 'vnet0'
        test_vn1 = topo.vn_of_vm[test_vm2]
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp', 'udp', 'tcp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 1
        total_streams['tcp'] = 1
        dpi = 9100
        # 2. set expectation to verify..
        matching_rule_action = {}
        # Assumption made here: one policy assigned to test_vn
        policy = topo.vn_policy[test_vn][0]
        policy_info = "policy in effect is : " + str(topo.rules[policy])
        num_rules = len(topo.rules[policy])
        for i in range(num_rules):
            proto = topo.rules[policy][i]['protocol']
            matching_rule_action[proto] = topo.rules[
                policy][i]['simple_action']
        if num_rules == 0:
            for proto in traffic_proto_l:
                matching_rule_action[proto] = 'deny'
        self.logger.info("matching_rule_action: %s" % matching_rule_action)
        # 3. Start Traffic
        expectedResult = {}
        start_time = self.analytics_obj.getstarttime(
            self.inputs.compute_ips[0])
        for proto in traffic_proto_l:
            expectedResult[proto] = True if matching_rule_action[
                proto] == 'pass' else False
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                trafficTestFixture(self.connections))
            # def startTraffic (self, name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=test_vm1_fixture, rx_vm_fixture=test_vm2_fixture, stream_proto=proto)
            msg1 = "Status of start traffic : %s, %s, %s" % (
                proto, test_vm1_fixture.vm_ip, startStatus[proto]['status'])
            if startStatus[proto]['status'] == False:
                self.logger.error(msg1)
                msg.extend(
                    [msg1, 'More info on failure: ', startStatus[proto]['msg']])
            else:
                self.logger.info(msg1)
            self.assertEqual(startStatus[proto]['status'], True, msg)
        self.logger.info("-" * 80)
        # 4. Poll live traffic
        # poll traffic and get status - traffic_stats['msg'],
        # traffic_stats['status']
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = [policy_info] + traffic_stats['msg']
            self.logger.info(" --> , flow proto: %s, expected: %s, got: %s" %
                             (proto, expectedResult[proto], traffic_stats['status']))
            self.assertEqual(traffic_stats['status'],
                             expectedResult[proto], err_msg)
        self.logger.info("-" * 80)
        # 4.a Opserver verification
        self.logger.info("Verfiy Policy info in Opserver")
        self.logger.info("-" * 80)
        exp_flow_count = total_streams['icmp'] + \
            total_streams['tcp'] + total_streams['udp']
        self.logger.info("-" * 80)

        src_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + test_vn
        dst_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + test_vn1
        query = {}
        query['udp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =17) AND (sourceip=' + \
            test_vm1_fixture.vm_ip + \
            ') AND (destip=' + test_vm2_fixture.vm_ip + ')'
        query['tcp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =6) AND (sourceip=' + \
            test_vm1_fixture.vm_ip + \
            ') AND (destip=' + test_vm2_fixture.vm_ip + ')'
        query['icmp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =1) AND (sourceip=' + \
            test_vm1_fixture.vm_ip + \
            ') AND (destip=' + test_vm2_fixture.vm_ip + ')'
        flow_record_data = {}
        flow_series_data = {}
        expected_flow_count = {}
        for proto in traffic_proto_l:
            flow_record_data[proto] = self.ops_inspect.post_query('FlowRecordTable', start_time=start_time, end_time='now', select_fields=[
                                                                  'sourcevn', 'sourceip', 'destvn', 'destip', 'setup_time', 'teardown_time', 'agg-packets', 'agg-bytes', 'protocol'], where_clause=query[proto])
            flow_series_data[proto] = self.ops_inspect.post_query('FlowSeriesTable', start_time=start_time, end_time='now', select_fields=[
                                                                  'sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
            msg1 = proto + \
                " Flow count info is not matching with opserver flow series record"
            # initialize expected_flow_count to num streams generated for the
            # proto
            expected_flow_count[proto] = total_streams[proto]
            self.logger.info(flow_series_data[proto])
            self.assertEqual(
                flow_series_data[proto][0]['flow_count'], expected_flow_count[proto], msg1)
        # 5. Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        traffic_stats = {}
        for proto in traffic_proto_l:
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            status = True if stopStatus[proto] == [] else False
            if status != expectedResult[proto]:
                msg.append(stopStatus[proto])
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
            # Get the traffic Stats for each protocol sent
            traffic_stats[proto] = traffic_obj[proto].returnStats()
            time.sleep(5)
            # Get the Opserver Flow series data
            flow_series_data[proto] = self.ops_inspect.post_query('FlowSeriesTable', start_time=start_time, end_time='now', select_fields=[
                                                                  'sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
        self.assertEqual(result, True, msg)
        # 6. Match traffic stats against Analytics flow series data
        self.logger.info("-" * 80)
        self.logger.info(
            "***Match traffic stats against Analytics flow series data***")
        self.logger.info("-" * 80)
        msg = {}
        for proto in traffic_proto_l:
            self.logger.info(
                " verify %s traffic status against Analytics flow series data" % (proto))
            msg[proto] = proto + \
                " Traffic Stats is not matching with opServer flow series data"
            self.logger.info(
                "***Actual Traffic sent by agent %s \n\n stats shown by Analytics flow series%s" %
                (traffic_stats[proto], flow_series_data[proto]))
            self.assertGreaterEqual(flow_series_data[proto][0]['sum(packets)'], traffic_stats[
                                    proto]['total_pkt_sent'], msg[proto])

        # 6.a Let flows age out and verify analytics still shows the data
        self.logger.info("-" * 80)
        self.logger.info(
            "***Let flows age out and verify analytics still shows the data in the history***")
        self.logger.info("-" * 80)
        time.sleep(180)
        for proto in traffic_proto_l:
            self.logger.info(
                " verify %s traffic status against Analytics flow series data after flow age out" % (proto))
            flow_series_data[proto] = self.ops_inspect.post_query('FlowSeriesTable', start_time='now', end_time='now', select_fields=[
                                                                  'sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
            msg = proto + \
                " Flow count info is not matching with opserver flow series record after flow age out in kernel"
            # live flows shoud be '0' since all flows are age out in kernel
            # self.assertEqual(flow_series_data[proto][0]['flow_count'],0,msg)
            self.assertEqual(len(flow_series_data[proto]), 0, msg)
            flow_series_data[proto] = self.ops_inspect.post_query('FlowSeriesTable', start_time=start_time, end_time='now', select_fields=[
                                                                  'sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
            msg = proto + \
                " Traffic Stats is not matching with opServer flow series data after flow age out in kernel"
            # Historical data should be present in the Analytics, even if flows
            # age out in kernel
            self.assertGreaterEqual(
                flow_series_data[proto][0]['sum(packets)'], traffic_stats[proto]['total_pkt_sent'], msg)
        return result
    # end test_policy_with_multi_proto_traffic
# end of class TestSerialPolicy
