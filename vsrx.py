
import sys
import time
import paramiko
from config_obj import *
from ncclient import manager as netconf
from ncclient.xml_ import *

class Vsrx():
    def __init__(self, username, password, addr = None):
        self.username = username
        self.password = password
        self.mgmt_addr = addr
        self.nc_client = None

    def mgmt_addr_set(self, addr):
        self.mgmt_addr = addr

    def nc_session_open(self):
        self.nc_client = netconf.connect(host = self.mgmt_addr, port = 830,
                username = self.username, password = self.password,
                hostkey_verify = False, device_params={'name':'junos'})

    def nc_session_close(self):
        self.client.close_session()
        self.client = None

    def config_get(self, filter):
        if not self.client:
            return
        result = self.client.get_config('running', filter = filter)
        return result

    def config_set(self, list):
        if not self.client:
            return
        self.client.load_configuration(action = 'set', config = list)
        self.client.commit()
        time.sleep(5)

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

