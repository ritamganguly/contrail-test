import test
from connections import ContrailConnections
from common import isolated_creds
from vn_test import VNFixture
from vm_test import VMFixture
from netaddr import IPNetwork


class BaseNeutronTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseNeutronTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__,
                                                          cls.inputs, ini_file=cls.ini_file,
                                                          logger=cls.logger)
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.quantum_fixture = cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
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
        self.addCleanup(self.quantum_fixture.delete_router,obj['id'])
        return obj

    def delete_router(self, router_id=None):
        val = self.quantum_fixture.delete_router(router_id)

    def add_router_interface(self, router_id, subnet_id=None, port_id=None):
        result = self.quantum_fixture.add_router_interface(router_id, subnet_id)
        self.addCleanup(self.quantum_fixture.delete_router_interface,
                        router_id, subnet_id)
        return result

    def delete_router_interface(self, router_id, subnet_id):
        self.quantum_fixture.delete_router_interface(
                                            router_id, subnet_id)
        
    def add_vn_to_router(self, router_id, vn_fixture):
        self.add_router_interface(router_id, vn_fixture.vn_subnet_objs[0]['id'])
        
        
    def get_gateway(self, cidr):
        return str(IPNetwork(cidr)[0])
