import time
import test
from connections import ContrailConnections
from common import isolated_creds
from vn_test import VNFixture
from vm_test import VMFixture
from project_test import ProjectFixture
from tcutils.util import get_random_name
from fabric.context_managers import settings
from fabric.api import run
from fabric.operations import get, put
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
import ConfigParser

contrail_api_conf = '/etc/contrail/contrail-api.conf'


class BaseNeutronTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseNeutronTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(
            cls.__name__,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.admin_inputs = cls.isolated_creds.get_admin_inputs()
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.quantum_fixture = cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(BaseNeutronTest, cls).tearDownClass()
    # end tearDownClass

    def create_vn(self, vn_name, vn_subnets):
        return self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections,
                      inputs=self.inputs,
                      vn_name=vn_name,
                      subnets=vn_subnets))

    def create_vm(self, vn_fixture, vm_name, node_name=None,
                  flavor='contrail_flavor_small',
                  image_name='ubuntu-traffic',
                  port_ids=[]):
        return self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture.obj,
                vm_name=vm_name,
                image_name=image_name,
                flavor=flavor,
                node_name=node_name,
                port_ids=port_ids))

    def create_router(self, router_name, tenant_id=None):
        obj = self.quantum_fixture.create_router(router_name, tenant_id)
        if obj:
            self.addCleanup(self.quantum_fixture.delete_router, obj['id'])
        return obj

    def delete_router(self, router_id=None):
        val = self.quantum_fixture.delete_router(router_id)

    def create_port(self, net_id, subnet_id=None, ip_address=None,
                    mac_address=None, no_security_group=False,
                    security_groups=[], extra_dhcp_opts=None):
        port_rsp = self.quantum_fixture.create_port(
            net_id,
            subnet_id,
            ip_address,
            mac_address,
            no_security_group,
            security_groups,
            extra_dhcp_opts)
        self.addCleanup(self.delete_port, port_rsp['id'], quiet=True)
        return port_rsp

    def delete_port(self, port_id, quiet=False):
        self._remove_from_cleanup(self.quantum_fixture.delete_port, (port_id))
        if quiet and not self.quantum_fixture.get_port(port_id):
            return
        self.quantum_fixture.delete_port(port_id)

    def update_port(self, port_id, port_dict):
        if not self.quantum_fixture.get_port(port_id):
            self.logger.error('Port with port_id %s not found'%port_id)
            return
        else:
            port_rsp= self.quantum_fixture.update_port(port_id, port_dict)
        return port_rsp


    def add_router_interface(self, router_id, subnet_id=None, port_id=None):
        if subnet_id:
            result = self.quantum_fixture.add_router_interface(
                router_id, subnet_id)
        elif port_id:
            result = self.quantum_fixture.add_router_interface(router_id,
                                                               port_id=port_id)

        self.addCleanup(self.delete_router_interface,
                        router_id, subnet_id, port_id)
        return result

    def delete_router_interface(self, router_id, subnet_id=None, port_id=None):
        self._remove_from_cleanup(self.delete_router_interface,
                                  (router_id, subnet_id, port_id))
        self.quantum_fixture.delete_router_interface(
            router_id, subnet_id, port_id)

    def add_vn_to_router(self, router_id, vn_fixture):
        self.add_router_interface(
            router_id,
            vn_fixture.vn_subnet_objs[0]['id'])

    def delete_vn_from_router(self, router_id, vn_fixture):
        self.delete_router_interface(
            router_id,
            vn_fixture.vn_subnet_objs[0]['id'])

    def create_security_group(self, name, quantum_handle=None):
        q_h = None
        if quantum_handle:
            q_h = quantum_handle
        else:
            q_h = self.quantum_fixture
        obj = q_h.create_security_group(name)
        if obj:
            self.addCleanup(self.delete_security_group, obj['id'])
        return obj
    # end create_security_group

    def delete_security_group(self, sg_id, quantum_handle=None):
        q_h = None
        if quantum_handle:
            q_h = quantum_handle
        else:
            q_h = self.quantum_fixture
        q_h.delete_security_group(sg_id)

    def update_default_quota_list(
            self,
            subnet=-1,
            virtual_network=-1,
            floating_ip=-1,
            logical_router=-1,
            security_group_rule=-1,
            virtual_machine_interface=-1,
            security_group=-1):
        contrail_api_file_list = []

        # Copy the contrail-api.conf to /tmp/ and restore it later

        for cfgm_ip in self.inputs.cfgm_ips:
            api_file_name = get_random_name('contrail-api')
            contrail_api_file_list.append(api_file_name)
            issue_cmd = "cp " + contrail_api_conf + " /tmp/" + \
                api_file_name
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        self.addCleanup(
            self.restore_default_quota_list,
            contrail_api_file_list)

        # Fetch the contrail-api.conf from all config nodes to active cfgm's
        # /tmp/

        api_file_list = []
        api_file_list.append(contrail_api_conf)
        for cfgm_ip in self.inputs.cfgm_ips[1:]:
            with settings(
                    host_string='%s@%s' % (
                        self.inputs.host_data[cfgm_ip]['username'], cfgm_ip)):
                api_conf_file = get_random_name('contrail-api-remote')
                api_file_list.append('/tmp/' + api_conf_file)
                get(contrail_api_conf, '/tmp/' + api_conf_file)

        # Edit the contrail-api.conf files adding quota sections

        for api_conf in api_file_list:
            api_conf_h = open(api_conf, 'a')
            config = ConfigParser.ConfigParser()
            config.add_section('QUOTA')
            config.set('QUOTA', 'subnet', subnet)
            config.set('QUOTA', 'virtual-network', virtual_network)
            config.set('QUOTA', 'floating-ip', floating_ip)
            config.set('QUOTA', 'logical-router', logical_router)
            config.set('QUOTA', 'security-group', security_group)
            config.set('QUOTA', 'security-group_rule', security_group_rule)
            config.set(
                'QUOTA',
                'virtual-machine-interface',
                virtual_machine_interface)
            config.write(api_conf_h)
            api_conf_h.close()

        # Put back updated contrail-api.conf file to respective cfgm's remove
        # temp files

        count = 1
        for cfgm_ip in self.inputs.cfgm_ips[1:]:
            with settings(
                    host_string='%s@%s' % (
                        self.inputs.host_data[cfgm_ip]['username'], cfgm_ip)):
                put(api_file_list[count], contrail_api_conf)
                issue_cmd = "rm -rf " + api_file_list[count]
                output = self.inputs.run_cmd_on_server(
                    cfgm_ip,
                    issue_cmd,
                    self.inputs.host_data[cfgm_ip]['username'],
                    self.inputs.host_data[cfgm_ip]['password'])
                count = count + 1

        # Restart contrail-api service on all cfgm nodes

        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip])

        time.sleep(30)

    # end update_default_quota_list

    def restore_default_quota_list(self, file_list=[]):
        # Restore default contrail-api.conf on respective cfgm nodes remove
        # temp files

        file_itr = iter(file_list)
        for cfgm_ip in self.inputs.cfgm_ips:
            api_conf_backup = next(file_itr)
            issue_cmd = "cp /tmp/" + api_conf_backup + \
                " " + contrail_api_conf + "; rm -rf /tmp/" + api_conf_backup
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip])

        time.sleep(30)

    # end restore_default_quota_list

    def create_external_network(self, connections, inputs):
        ext_vn_name = get_random_name('ext_vn')
        ext_subnets = [self.inputs.fip_pool]
        mx_rt = self.inputs.mx_rt
        ext_vn_fixture = self.useFixture(
                VNFixture(
                    project_name=inputs.project_name,
                    connections=connections,
                    vn_name=ext_vn_name,
                    inputs=inputs,
                    subnets=ext_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt,
                    router_external=True))
        assert ext_vn_fixture.verify_on_setup()
        return ext_vn_fixture

    # end create_external_network

    def allow_default_sg_to_allow_all_on_project(self, project_name):

        project_fixture = self.useFixture(
                ProjectFixture(
                    vnc_lib_h=self.vnc_lib,
                    project_name=self.inputs.project_name,
                    connections=self.connections))
        self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                project_name)
        project_fixture.set_sec_group_for_allow_all(
                project_name, 'default')

    # end allow_default_sg_to_allow_all_on_project

    def verify_snat(self, vm_fixture):
        result= True
        self.logger.info("Ping to 8.8.8.8 from vm %s" % (vm_fixture.vm_name))
        if not vm_fixture.ping_with_certainty('8.8.8.8'):
           self.logger.error("Ping to 8.8.8.8 from vm %s Failed" % (vm_fixture.vm_name))
           result = result and False
        self.logger.info('Testing FTP...Intsalling VIM In the VM via FTP')
        run_cmd = "wget ftp://ftp.vim.org/pub/vim/unix/vim-7.3.tar.bz2"
        vm_fixture.run_cmd_on_vm(cmds=[run_cmd])
        output = vm_fixture.return_output_values_list[0]
        if 'saved' not in output:
              self.logger.error("FTP failed from VM %s" %
                                  (vm_fixture.vm_name))
              result = result and False
        else:
              self.logger.info("FTP successful from VM %s via FIP" %
                                 (vm_fixture.vm_name))
        return result
    # end verify_snat

    def config_aap(self, port1, port2, ip):
        self.logger.info('Configuring AAP on ports %s and %s'%(port1['id'], port2['id']))
        port1_dict = {'allowed_address_pairs': [{"ip_address": ip+'/32', "mac_address": port1['mac_address']}]}
        port1_rsp= self.update_port(port1['id'], port1_dict)
        port2_dict = {'allowed_address_pairs': [{"ip_address": ip+'/32', "mac_address": port2['mac_address']}]}
        port2_rsp= self.update_port(port2['id'], port2_dict)
        return True
    #end config_aap

    def config_vrrp(self, vm1, vm2, ip):
        self.logger.info('Configuring VRRP on %s and %s'%(vm1.vm_name, vm2.vm_name))
        vrrp_mas_cmd = 'nohup vrrpd -n -D -i eth0 -v 1 -a none -p 20 %s'%ip
        vrrp_bck_cmd = 'nohup vrrpd -n -D -i eth0 -v 1 -a none -p 10 %s'%ip
        vm1.run_cmd_on_vm(cmds=[vrrp_mas_cmd], as_sudo=True)
        vm2.run_cmd_on_vm(cmds=[vrrp_bck_cmd], as_sudo=True)
        return True
    #end config_vrrp
    
    def vrrp_mas_chk(self, vm, vn, ip):
        vrrp_mas_chk_cmd= 'ip -4 addr ls'
        self.logger.info('Will verify who the VRRP master is and the corresponding route entries in the Agent')
        vm.run_cmd_on_vm(cmds=[vrrp_mas_chk_cmd], as_sudo=True)
        output = vm.return_output_cmd_dict[vrrp_mas_chk_cmd]
        if ip in output:
            self.logger.info('%s is selected as the VRRP Master'%vm.vm_name)
            result= True
        assert result, 'VRRP Master not selected'
        inspect_h = self.agent_inspect[vm.vm_node_ip]
        (domain, project, vnw) = vn.vn_fq_name.split(':')
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vnw)
        agent_vrf_obj = vm.get_matching_vrf(agent_vrf_objs['vrf_list'], vn.vrf_name)
        vn1_vrf_id = agent_vrf_obj['ucindex']
        paths = inspect_h.get_vna_active_route(vrf_id=vn1_vrf_id, ip=ip, prefix='32')['path_list']
        for path in paths:
            if path['peer'] == 'LocalVmPort' and path['path_preference_data']['wait_for_traffic'] == 'false':
                result= True
                break
            else:
                result= False
        assert result, 'The Agent entries to the vIP do not correspond to the VRRP master'
        return True
    #end vrrp_mas_chk
    
    def verify_vrrp_action(self, src_vm, dst_vm, ip):
        self.logger.info('Will ping %s from %s and check if %s responds'%(ip, src_vm.vm_name, dst_vm.vm_name))
        compute_ip = dst_vm.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password'] 
        session = ssh(compute_ip, compute_user, compute_password)
        vm_tapintf = dst_vm.tap_intf[dst_vm.vn_fq_name]['name']
        cmd = 'tcpdump -nni %s -c 10 > /tmp/%s_out.log' % (vm_tapintf,vm_tapintf)
        execute_cmd(session, cmd, self.logger) 
        assert src_vm.ping_with_certainty(ip), 'Ping to vIP failure'
        output_cmd = 'cat /tmp/%s_out.log' % vm_tapintf  
        output, err = execute_cmd_out(session, output_cmd, self.logger) 
        assert ip in output, 'ICMP Requests not seen on the VRRP Master'
        return True
    #end verify_vrrp_sction
    
    def _remove_from_cleanup(self, func_call, args):
        for cleanup in self._cleanups:
            if func_call in cleanup and args == cleanup[1]:
                self._cleanups.remove(cleanup)

    def create_lb_pool(self, name, lb_method, protocol, subnet_id):
        lb_pool_resp = None
        lb_pool_resp = self.quantum_fixture.create_lb_pool(
                            name, lb_method, protocol, subnet_id)
        if lb_pool_resp :
            self.addCleanup(self.quantum_fixture.delete_lb_pool, 
                            lb_pool_resp['id'])
        return lb_pool_resp
    # end create_lb_pool

    def create_lb_member(self, ip_address, protocol_port, pool_id):
        lb_member_resp = None
        lb_member_resp = self.quantum_fixture.create_lb_member(
                            ip_address, protocol_port, pool_id)
        if lb_member_resp :
            self.addCleanup(self.quantum_fixture.delete_lb_member,
                            lb_member_resp['id'])
        return lb_member_resp
    # end create_lb_member

    def create_health_monitor(self, delay, max_retries, probe_type, timeout):
        hm_resp = None
        hm_resp = self.quantum_fixture.create_health_monitor(
                    delay, max_retries, probe_type, timeout) 
        if hm_resp :
            self.addCleanup(self.quantum_fixture.delete_health_monitor,
                            hm_resp['id'])
        return hm_resp 
    # end create_health_monitor

    def create_vip(self, name, protocol, protocol_port, subnet_id, pool_id):
        vip_resp = None
        vip_resp = self.quantum_fixture.create_vip(
                    name, protocol, protocol_port, subnet_id, pool_id)
        if vip_resp :
            self.addCleanup(self.quantum_fixture.delete_vip,
                            vip_resp['id'])
        return vip_resp
    # end create_vip

    def associate_health_monitor(self, pool_id, hm_id):
        hm_resp = self.quantum_fixture.associate_health_monitor(
                    pool_id, hm_id)
        if hm_resp:
            self.addCleanup(self.quantum_fixture.disassociate_health_monitor(
                pool_id, hm_id)) 
    # end associate_health_monitor