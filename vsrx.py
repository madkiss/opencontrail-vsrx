
import sys
import time
import paramiko
from opencontrail_config.config_obj import *
from ncclient import manager as netconf
from ncclient.xml_ import *

class Vsrx():
    def __init__(self, name, username, password, config_client):
        self.name = name
        self.instance_name = '%s_1' %(name)
        self.username = username
        self.password = password
        self.config_client = config_client
        self.mgmt_addr = None
        self.nc_client = None

    def nc_session_open(self):
        if not self.mgmt_addr:
            self.mgmt_addr_get()
        self.nc_client = netconf.connect(host = self.mgmt_addr, port = 830,
                username = self.username, password = self.password,
                hostkey_verify = False, device_params={'name':'junos'})

    def nc_session_close(self):
        self.nc_client.close_session()
        self.nc_client = None

    def config_get(self, filter):
        self.nc_session_open()
        result = self.nc_client.get_config('running', filter = filter)
        self.nc_session_close()
        return result

    def config_set(self, list):
        self.nc_session_open()
        self.nc_client.load_configuration(action = 'set', config = list)
        self.nc_client.commit()
        time.sleep(8)
        self.nc_session_close()

    def check(self):
        si = ConfigServiceInstance(self.config_client)
        for item in si.obj_list():
            if (item['fq_name'][2] == self.name):
                return True

    def launch(self, template, net_list):
        print 'Launch service instance.'
        si = ConfigServiceInstance(self.config_client)
        si.add(name = self.name, template = template, network_list = net_list)

        print 'Waiting for service instance to be active...'
        timeout = 12
        while timeout:
            time.sleep(3)
            vm = self.config_client.nova.servers.find(
                    name = self.instance_name)
            if vm.status != 'BUILD':
                print 'Service instance %s is %s' %(vm.name, vm.status)
                break
            timeout -= 1
        self.mgmt_addr = vm.addresses['management'][0]['addr']

        print 'Post-launch configuration.'
        vm_if = ConfigVmInterface(self.config_client)
        vm_if.delete(name = 'management', sg = 'default', vm_id = vm.id)
        vm_if.delete(name = 'public', sg = 'default', vm_id = vm.id)
        vm_if.delete(name = 'access', sg = 'default', vm_id = vm.id)

    def delete(self):
        si = ConfigServiceInstance(self.config_client)
        si.delete(name = self.name)
        count = 0
        while (count < 30):
            print 'Waiting for service instance to be deleted...%d' %(count)
            try:
                vm = self.config_client.nova.servers.find(
                        name = self.instance_name)
                count += 1
                time.sleep(2)
                continue
            except:
                print 'Service instance is deleted.'
                break

    def netconf_enable(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        count = 0
        while True:
            print 'Waiting for service booting up...%d' %(count)
            try:
                ssh.connect(self.mgmt_addr, username = self.username,
                        password = self.password, timeout = 5)
                break
            except:
                count += 1

        print 'Enable NETCONF...'
        cmd = 'cli -c "configure;' \
              'set system services netconf ssh;' \
              'set security zones security-zone trust interfaces ' \
                  'ge-0/0/0.0 host-inbound-traffic system-services all;' \
              'commit"'
        ssh.exec_command(cmd)
        time.sleep(8)
        ssh.close()

    def gateway_get(self, net_name):
        vn = self.config_client.vnc.virtual_network_read(
                fq_name = ['default-domain', 'admin', net_name])
        ipam = vn.get_network_ipam_refs()[0]
        subnet = ipam['attr'].get_ipam_subnets()[0]
        return subnet.get_default_gateway()

    def mgmt_addr_get(self):
        vm = self.config_client.nova.servers.find(name = self.instance_name)
        self.mgmt_addr = vm.addresses['management'][0]['addr']
        return self.mgmt_addr

