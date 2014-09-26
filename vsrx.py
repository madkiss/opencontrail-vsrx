
import sys
import time
import paramiko
from opencontrail_config.config_obj import *
from ncclient import manager as netconf
from ncclient.xml_ import *

class Vsrx():
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.mgmt_addr = None
        self.nc_client = None

    def nc_session_open(self):
        self.nc_client = netconf.connect(host = self.mgmt_addr, port = 830,
                username = self.username, password = self.password,
                hostkey_verify = False, device_params={'name':'junos'})

    def nc_session_close(self):
        self.nc_client.close_session()
        self.nc_client = None

    def config_get(self, filter):
        if not self.nc_client:
            return
        result = self.nc_client.get_config('running', filter = filter)
        return result

    def config_set(self, list):
        if not self.nc_client:
            return
        self.nc_client.load_configuration(action = 'set', config = list)
        self.nc_client.commit()
        time.sleep(5)

    def launch(self, name, template, api_client, net_list):
        print 'Launch service instance.'
        si = ConfigServiceInstance(api_client)
        si.add(name = name, template = template, network_list = net_list)

        print 'Waiting for service instance to be active...'
        timeout = 12
        while timeout:
            time.sleep(3)
            vm = api_client.nova.servers.find(name = '%s_1' %(name))
            if vm.status != 'BUILD':
                print 'Service instance %s is %s' %(vm.name, vm.status)
                break
            timeout -= 1
        self.mgmt_addr = vm.addresses['management'][0]['addr']

        #print 'Post-launch configuration.'
        #vm_if = ConfigVmInterface(api_client)
        #vm_if.delete(name = 'management', sg = 'default', vm_id = vm.id)
        #vm_if.delete(name = 'public', sg = 'default', vm_id = vm.id)
        #vm_if.delete(name = 'access', sg = 'default', vm_id = vm.id)

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

