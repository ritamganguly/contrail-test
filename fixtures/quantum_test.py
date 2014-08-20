import os
import fixtures
from contrail_fixtures import contrail_fix_ext
from tcutils.util import get_plain_uuid, get_dashed_uuid

try:
    from quantumclient.quantum import client
    from quantumclient.client import HTTPClient
    from quantumclient.common.exceptions import QuantumClientException as CommonNetworkClientException
except ImportError:
    from neutronclient.neutron import client
    from neutronclient.client import HTTPClient
    from neutronclient.common.exceptions import NeutronClientException as CommonNetworkClientException


class NetworkClientException(CommonNetworkClientException):

    def __init__(self, **kwargs):
        message = kwargs.get('message')
        self.status_code = kwargs.get('status_code', 0)
        if message:
            self.message = message
        super(NetworkClientException, self).__init__(**kwargs)

    def __str__(self):
        return repr(self.message)


class QuantumFixture(fixtures.Fixture):

    def __init__(
            self,
            username,
            password,
            project_id,
            inputs,
            cfgm_ip,
            openstack_ip):
        httpclient = None
        self.quantum_port = '9696'
        self.username = username
        self.password = password
        self.project_id = None
        self.project_id = project_id
        self.cfgm_ip = cfgm_ip
        self.openstack_ip = openstack_ip
        self.inputs = inputs
        self.obj = None
        self.auth_url = os.getenv('OS_AUTH_URL') or \
                                    'http://' + openstack_ip + ':5000/v2.0'
        self.logger = self.inputs.logger
    # end __init__

    def setUp(self):
        super(QuantumFixture, self).setUp()
        project_id = get_plain_uuid(self.project_id)
        try:
            httpclient = HTTPClient(username=self.username,
                                    tenant_id=project_id,
                                    password=self.password,
                                    auth_url=self.auth_url)
            httpclient.authenticate()
        except CommonNetworkClientException as e:
            self.logger.exception('Exception while connection to Quantum')
            raise e
        OS_URL = httpclient.endpoint_url
        OS_TOKEN = httpclient.auth_token
        self.obj = client.Client('2.0', endpoint_url=OS_URL, token=OS_TOKEN)
        self.project_id = httpclient.auth_tenant_id
    # end setUp

    def cleanUp(self):
        super(QuantumFixture, self).cleanUp()

    def get_handle(self):
        return self.obj
    # end get_handle

    def create_network(self, vn_name, vn_subnets, ipam_fq_name):
        """Create network given a name and a list of subnets.
        """
        try:
            net_req = {'name': vn_name}
            net_rsp = self.obj.create_network({'network': net_req})
            self.logger.debug('Response for create_network : ' + repr(net_rsp))

            vn_id = net_rsp['network']['id']
            net_id = net_rsp['network']['id']
            for subnet in vn_subnets:
                net_rsp = self.create_subnet(
                    subnet, net_id, ipam_fq_name)
            # end for
            return self.obj.show_network(network=net_id)
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Quantum Exception while creating network %s' % (vn_name))
            return None

    def create_subnet(self, subnet, net_id, ipam_fq_name=None):
        subnet_req = subnet
        subnet_req['network_id'] = net_id
        subnet_req['ip_version'] = 4
        subnet_req['cidr'] = unicode(subnet_req['cidr'])

        subnet_rsp = self.obj.create_subnet({'subnet': subnet_req})
        self.logger.debug('Response for create_subnet : ' + repr(subnet_rsp))
        return subnet_rsp
    # end create_subnet

    def create_port(self, net_id, subnet_id=None, ip_address=None,
                    mac_address=None, no_security_group=False,
                    security_groups=[], extra_dhcp_opts=None):
        port_req_dict = {
            'network_id': net_id,
        }
        fixed_ip_req = {}
        if subnet_id:
            fixed_ip_req['subnet_id'] = subnet_id
        if ip_address:
            fixed_ip_req['ip_address'] = ip_address
        if mac_address:
            port_req_dict['mac_address'] = mac_address
        if no_security_group:
            port_req_dict['security_groups'] = None
        if security_groups:
            port_req_dict['security_groups'] = security_groups
        if extra_dhcp_opts:
            port_req_dict['extra_dhcp_opts'] = extra_dhcp_opts

        port_req_dict['fixed_ips'] = [fixed_ip_req]
        port_rsp = self.obj.create_port({'port': port_req_dict})
        self.logger.debug('Response for create_port : ' + repr(port_rsp))
        return port_rsp['port']
    # end create_port

    def create_security_group(self, name):
        sg_dict = {'name': name, 'description': 'SG-' + name}
        sg_resp = self.obj.create_security_group({'security_group': sg_dict})
        return sg_resp['security_group']
    # end create_security_group

    def delete_security_group(self, sg_id):
        self.obj.delete_security_group(sg_id)
    # end delete_security_group

    def create_security_group_rule(self, sg_id, direction='ingress',
                                   port_range_min=None, port_range_max=None,
                                   protocol=None, remote_group_id=None,
                                   remote_ip_prefix=None):
        sg_rule = None
        sg_rule_dict = {'security_group_id': sg_id}
        if direction:
            sg_rule_dict['direction'] = direction
        if port_range_min:
            sg_rule_dict['port_range_min'] = port_range_min
        if port_range_max:
            sg_rule_dict['port_range_max'] = port_range_max
        if protocol:
            sg_rule_dict['protocol'] = protocol
        if remote_group_id:
            sg_rule_dict['remote_group_id'] = remote_group_id
        if remote_ip_prefix:
            sg_rule_dict['remote_ip_prefix'] = remote_ip_prefix
        try:
            self.obj.create_security_group_rule(
                {'security_group_rule': sg_rule_dict})
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Quantum Exception while creating SG Rule %s' % (sg_rule_dict))
        return sg_rule
    # end create_security_group_rule

    def delete_port(self, port_id,):
        port_rsp = self.obj.delete_port(port_id)
        self.logger.debug('Response for delete_port : ' + repr(port_rsp))
        return port_rsp
    # end delete_port

    def get_vn_obj_if_present(self, vn_name, project_id=None):
        if not project_id:
            project_id = get_dashed_uuid(self.project_id)
        try:
            net_rsp = self.obj.list_networks()
            for (x, y, z) in [(network['name'], network['id'], network['tenant_id']) for network in net_rsp['networks']]:
                dashed_tenant_id = get_dashed_uuid(z)
                if vn_name == x and project_id in dashed_tenant_id:
                    net_id = y
                    return self.obj.show_network(network=net_id)
        except CommonNetworkClientException as e:
            self.logger.exception(
                "Some exception while doing Quantum net-list")
            raise NetworkClientException(message=str(e))
        return None
    # end get_vn_obj_if_present

    def get_vn_obj_from_id(self, id):
        try:
            return self.obj.show_network(network=id)
        except CommonNetworkClientException as e:
            self.logger.exception(
                "Some exception while doing Quantum net-list")
            return None
        return None

    def delete_vn(self, vn_id):
        result = True
        try:
            net_rsp = self.obj.delete_network(vn_id)
            self.logger.debug('Response for deleting network %s' %
                              (str(net_rsp)))
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Quantum exception while deleting a VN %s' % (vn_id))
            result = False

        return result
    # end _delete_vn

    def list_networks(self, args):
        try:
            net_rsp = self.obj.list_networks(args)
            return net_rsp
        except CommonNetworkClientException as e:
            self.logger.debug("Exception while viewing Network list")
            return []
    # end list_networks

    def create_floatingip(self, fip_pool_vn_id, project_id):
        fip_req = {'floatingip': {'floating_network_id': fip_pool_vn_id,
                                  'tenant_id': project_id}}
        fip_resp = self.obj.create_floatingip(fip_req)
        return fip_resp
    # end create_floatingip

    def delete_floatingip(self, fip_id):
        fip_resp = self.obj.delete_floatingip(fip_id)
        return fip_resp
    # end delete_floatingip

    def list_floatingips(self, tenant_id):
        self.obj.list_floatingips(tenant_id=tenant_id)
    # end

    def get_floatingip(self, fip_id):
        return self.obj.show_floatingip(fip_id)
    # end get_floatingip

    def get_port_id(self, vm_id):
        ''' Returns the Quantum port-id of a VM.

        '''
        try:
            port_rsp = self.obj.list_ports(device_id=[vm_id])
            port_id = port_rsp['ports'][0]['id']
            return port_id
        except Exception as e:
            self.logger.error('Error occured while getting port-id of a VM ')
            return None
    # end

    def update_floatingip(self, fip_id, update_dict):
        return self.obj.update_floatingip(fip_id, update_dict)
    # end update_floatingip

    def get_vn_id(self, vn_name):
        net_id = None
        net_rsp = self.obj.list_networks()
        for (x, y, z) in [(network['name'], network['id'], network['tenant_id']) for network in net_rsp['networks']]:
            if vn_name == x and self.project_id in z:
                net_id = y
                break
        return net_id
    # end get_vn_id

    def create_policy(self, policy_dict):
        policy_rsp = None
        try:
            policy_rsp = self.obj.create_policy(policy_dict)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while creating policy" + str(e))
        return policy_rsp
    # end create_policy

    def update_policy(self, policy_id, policy_entries):
        '''policy_data format {'policy': {'entries': new_policy_entries}}'''
        policy_rsp = None
        try:
            policy_rsp = self.obj.update_policy(policy_id, policy_entries)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while creating policy" + str(e))
        self.logger.info("policy_rsp for policy_id %s after update is %s" %
                         (policy_id, policy_rsp))
        return policy_rsp
    # end update_policy

    def get_policy_if_present(self, project_name=None, policy_name=None):
        policy_rsp = None
        try:
            policy_rsp = self.list_policys()
            for (x, y, z) in [(policy['name'], policy['id'], policy['fq_name']) for policy in policy_rsp['policys']]:
                if policy_name == x:
                    if project_name:
                        if project_name in z:
                            policy_id = y
                            return self.obj.show_policy(policy=policy_id)
                    else:
                        policy_id = y
                        return self.obj.show_policy(policy=policy_id)
        except CommonNetworkClientException as e:
            self.logger.exception(
                "Some exception while doing Quantum policy-listing")
        return None

    # end get_policy_if_present

    def list_policys(self):
        policy_list = None
        try:
            policy_list = self.obj.list_policys(tenant_id=self.project_id)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while listing policies" + str(e))
        return policy_list
    # end list_policys

    def delete_policy(self, policy_id):
        result = True
        try:
            self.obj.delete_policy(policy_id)
        except CommonNetworkClientException as e:
            result = False
            self.logger.error(
                "Quantum Exception while deleting policy" + str(e))
        return result
    # end delete_policy

    def get_policy_fq_name(self, policy_obj):
        return policy_obj['policy']['fq_name']
    # end get_policy_fq_name

    def update_network(self, vn_id, network_dict):
        net_rsp = None
        try:
            net_rsp = self.obj.update_network(vn_id, network_dict)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while updating network" + str(e))
        return net_rsp
    # end update_network

    def list_security_groups(self, *args, **kwargs):
        return self.obj.list_security_groups(*args, **kwargs)
    # end

    def create_router(self, router_name, tenant_id=None):
        router_body = {}
        router_body['router'] = {}
        router_body['router']['name'] = router_name
        if tenant_id:
            router_body['router']['tenant_id'] = tenant_id
        return self.obj.create_router(router_body)['router']

    def delete_router(self, router_id=None):
        return self.obj.delete_router(router_id)

    def get_subnets_of_vn(self, vn_id):
        subnets = []
        try:
            vn_obj = self.obj.show_network(vn_id)
            for subnet_id in vn_obj['network']['subnets']:
                subnets.append(self.obj.show_subnet(subnet_id)['subnet'])
        except CommonNetworkClientException as e:
            self.logger.exception(
                'Exception while reading network details%s' % (vn_id))
            return None
        return subnets
    # end get_subnets_of_vn

    def add_router_interface(self, router_id, subnet_id=None, port_id=None):
        ''' Add an interface to router.
            Result will be of form
            {u'subnet_id': u'd5ae735b-4df2-473f-9d6c-ca9ddb263fdc', u'tenant_id': u'509a5c7a23474f15a456905adcd9fc8d', u'port_id': u'f2d4cb13-2401-4830-b8cc-c23d544bb1d6', u'id': u'da7e4878-04fa-4d1a-8def-4b11c2eaf569'}
        '''
        body = {}
        if subnet_id:
            body['subnet_id'] = subnet_id
        if port_id:
            body['port_id'] = port_id
        self.logger.info('Adding interface with subnet_id %s, port_id %s'
                         ' to router %s' % (subnet_id, port_id, router_id))
        result = self.obj.add_interface_router(router_id, body)
        return result
    # end add_router_interface

    def delete_router_interface(self, router_id, subnet_id=None, port_id=None):
        ''' Remove an interface from router
        '''
        body = {}
        if subnet_id:
            body['subnet_id'] = subnet_id
        if port_id:
            body['port_id'] = port_id
        self.logger.info('Deleting interface with subnet_id %s, port_id %s'
                         ' from router %s' % (subnet_id, port_id, router_id))
        result = self.obj.remove_interface_router(router_id, body)
        return result
    # end delete_router_interface

    def update_router(self, router_id, router_dict):
        router_rsp = None
        body = {}
        body['router'] = router_dict
        try:
            router_rsp = self.obj.update_router(router_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while updating router " + str(e))
            raise e
        return router_rsp
    # end update_router

    def update_security_group(self, sg_id, sg_dict):
        sg_rsp = None
        body = {}
        body['security_group'] = sg_dict
        try:
            sg_rsp = self.obj.update_security_group(sg_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while updating security group " + str(e))
            raise e
        return sg_rsp
    # end update_security_group

    def get_router_interfaces(self, router_id):
        ports_obj = self.obj.list_ports(device_id=router_id)['ports']
        return ports_obj

    def update_subnet(self, subnet_id, subnet_dict):
        subnet_rsp = None
        body = {}
        body['subnet'] = subnet_dict
        try:
            subnet_rsp = self.obj.update_subnet(subnet_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while updating subnet" + str(e))
            raise e
        return subnet_rsp
    # end update_subnet

    def update_port(self, port_id, port_dict):
        port_rsp = None
        body = {}
        body['port'] = port_dict
        self.logger.debug('Updating port %s with body : %s' % (
            port_id, body))
        try:
            port_rsp = self.obj.update_port(port_id, body)
        except CommonNetworkClientException as e:
            self.logger.error(
                "Quantum Exception while updating port" + str(e))
            raise e
        return port_rsp
    # end update_port

# end QuantumFixture
