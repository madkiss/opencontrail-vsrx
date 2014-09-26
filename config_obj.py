
import os
import sys
import time
import uuid
from vnc_api import vnc_api
try:
    import novaclient.v1_1.client
    config_nova = True
except:
    config_nova = False


class ConfigVirtualDns():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.virtual_DNSs_list()['virtual-DNSs']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == name):
                return self.vnc.virtual_DNS_read(id = item['uuid'])

    def obj_show(self, obj):
        print 'Virtual DNS'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)
        dns = obj.get_virtual_DNS_data()
        print 'Domain name: %s' %(dns.domain_name)
        print 'Record order: %s' %(dns.record_order)
        print 'Default TTL: %s seconds' %(dns.default_ttl_seconds)
        print 'Next DNS: %s' %(dns.next_virtual_DNS)

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                print '    %s' %(item['fq_name'][1])

    def add(self, name, domain_name, record_order, next_dns):
        data = vnc_api.VirtualDnsType(domain_name = domain_name,
                dynamic_records_from_client = True,
                record_order = record_order,
                default_ttl_seconds = 86400,
                next_virtual_DNS = 'default-domain:' + next_dns)
        obj = vnc_api.VirtualDns(name = name, virtual_DNS_data = data)
        try:
            self.vnc.virtual_DNS_create(obj)
        except Exception as e:
            print 'ERROR: %s' %(str(e))

    def delete(self, name):
        try:
            self.vnc.virtual_DNS_delete(
                    fq_name = ['default-domain', name])
        except Exception as e:
            print 'ERROR: %s' %(str(e))


class ConfigIpam():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.network_ipams_list()['network-ipams']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.network_ipam_read(id = item['uuid'])

    def dns_show(self, mgmt):
        print '    DNS Type: %s' %(mgmt.ipam_dns_method)
        if (mgmt.ipam_dns_method == 'virtual-dns-server'):
            print '        Virtual DNS Server: %s' %(
                    mgmt.get_ipam_dns_server().virtual_dns_server_name)
        elif (mgmt.ipam_dns_method == 'tenant-dns-server'):
            list = mgmt.get_ipam_dns_server().get_tenant_dns_server_address().get_ip_address()
            print '        Tenant DNS Server:'
            for item in list:
                print '            %s' %(item)

    def dhcp_show(self, mgmt):
        dhcp_opt = {'4':'NTP Server', '15':'Domain Name'}
        print '    DHCP Options:'
        dhcp = mgmt.get_dhcp_option_list()
        if not dhcp:
            return
        for item in dhcp.get_dhcp_option():
            print '        %s: %s' %(dhcp_opt[item.dhcp_option_name],
                    item.dhcp_option_value)

    def obj_show(self, obj):
        print 'IPAM'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)
        print 'Management:'
        mgmt = obj.get_network_ipam_mgmt()
        if not mgmt:
            return
        self.dns_show(mgmt)
        self.dhcp_show(mgmt)

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def dns_add(self, mgmt, dns_type, virtual_dns = None, tenant_dns = None):
        type = {'none':'none',
                'default':'default-dns-server',
                'virtual':'virtual-dns-server',
                'tenant':'tenant-dns-server'}
        if not dns_type:
            return
        mgmt.set_ipam_dns_method(type[dns_type])
        if virtual_dns:
            mgmt.set_ipam_dns_server(vnc_api.IpamDnsAddressType(
                    virtual_dns_server_name = virtual_dns))
        if tenant_dns:
            mgmt.set_ipam_dns_server(vnc_api.IpamDnsAddressType(
                    tenant_dns_server_address = vnc_api.IpAddressesType(
                    ip_address = tenant_dns)))

    def dhcp_add(self, mgmt, domain_name = None, ntp_server = None):
        if domain_name:
            list = mgmt.get_dhcp_option_list()
            if not list:
                list = vnc_api.DhcpOptionsListType()
                mgmt.set_dhcp_option_list(list)
            list.add_dhcp_option(vnc_api.DhcpOptionType(
                    dhcp_option_name = '15',
                    dhcp_option_value = domain_name))
        if ntp_server:
            list = mgmt.get_dhcp_option_list()
            if not list:
                list = vnc_api.DhcpOptionsListType()
                mgmt.set_dhcp_option_list()
            list.add_dhcp_option(vnc_api.DhcpOptionType(
                    dhcp_option_name = '4',
                    dhcp_option_value = ntp_server))

    def add(self, name, dns_type, virtual_dns = None, tenant_dns = None,
            domain_name = None, ntp_server = None):
        create = False
        obj = self.obj_get(name)
        if not obj:
            obj = vnc_api.NetworkIpam(name = name,
                    parent_obj = self.tenant)
            create = True
        mgmt = obj.get_network_ipam_mgmt()
        if not mgmt:
            mgmt = vnc_api.IpamType()
            obj.set_network_ipam_mgmt(mgmt)
        self.dns_add(mgmt, dns_type, virtual_dns, tenant_dns)
        self.dhcp_add(mgmt, domain_name, ntp_server)
        if create:
            try:
                self.vnc.network_ipam_create(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))
        else:
            self.vnc.network_ipam_update(obj)

    def delete(self, name, domain_name = None):
        update = False
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
            return
        if domain_name:
            mgmt = obj.get_network_ipam_mgmt()
            list = mgmt.get_dhcp_option_list()
            for item in list.get_dhcp_option():
                if (item.dhcp_option_name == '15') and \
                    (item.dhcp_option_value == domain_name):
                    list.delete_dhcp_option(item)
                    break
            update = True
        if update:
            self.vnc.network_ipam_update(obj)
        else:
            try:
                self.vnc.network_ipam_delete(
                        fq_name = ['default-domain', self.tenant.name,
                        name])
            except Exception as e:
                print 'ERROR: %s' %(str(e))


class ConfigPolicy():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.network_policys_list()['network-policys']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.network_policy_read(id = item['uuid'])

    def addr_show(self, addr_list):
        for item in addr_list:
            print '        Virtual Network: %s' %(item.get_virtual_network())

    def port_show(self, port_list):
        for item in port_list:
            print '        %d:%d' %(item.get_start_port(), item.get_end_port())

    def action_show(self, rule):
        list = rule.get_action_list()
        if not list:
            return
        action = list.get_simple_action()
        if action:
            print '        %s' %(action)
        else:
            for item in rule.get_action_list().get_apply_service():
                print '        %s' %(item)

    def rule_show(self, obj):
        rules_obj = obj.get_network_policy_entries()
        if (rules_obj == None):
            return
        list = rules_obj.get_policy_rule()
        count = 1
        for rule in list:
            print 'Rule #%d' %(count)
            print '    Direction: %s' %(rule.get_direction())
            print '    Protocol: %s' %(rule.get_protocol())
            print '    Source Addresses:'
            self.addr_show(rule.get_src_addresses())
            print '    Source Ports:'
            self.port_show(rule.get_src_ports())
            print '    Destination Addresses:'
            self.addr_show(rule.get_dst_addresses())
            print '    Destination Ports:'
            self.port_show(rule.get_dst_ports())
            print '    Action:'
            self.action_show(rule)
            count += 1

    def obj_show(self, obj):
        print 'Policy'
        print 'Name: %s' %(obj.get_fq_name())
        print 'UUID: %s' %(obj.uuid)
        self.rule_show(obj)
        list = obj.get_virtual_network_back_refs()
        if (list != None):
            print '[BR] network:'
            for item in list:
                print '    %s' %(item['to'][2])

    def show(self, name):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def rule_add(self, arg_list):
        direction = None
        protocol = None
        src_net_list = []
        dst_net_list = []
        src_port_list = []
        dst_port_list = []
        action = None
        service_list = []
        for arg in arg_list:
            arg_name = arg.split('=')[0]
            arg_val = arg.split('=')[1]
            if (arg_name == 'direction'):
                direction = arg_val
            elif (arg_name == 'protocol'):
                protocol = arg_val
            elif (arg_name == 'src-net'):
                net = 'default-domain:%s:%s' %(self.tenant.name, arg_val)
                src_net_list.append(vnc_api.AddressType(virtual_network = net))
            elif (arg_name == 'dst-net'):
                net = 'default-domain:%s:%s' %(self.tenant.name, arg_val)
                dst_net_list.append(vnc_api.AddressType(virtual_network = net))
            elif (arg_name == 'src-port'):
                if (arg_val == 'any'):
                    src_port_list.append(vnc_api.PortType(
                            start_port = -1, end_port = -1))
                else:
                    s_e = arg_val.split(':')
                    src_port_list.append(vnc_api.PortType(
                            start_port = int(s_e[0]), end_port = int(s_e[1])))
            elif (arg_name == 'dst-port'):
                if (arg_val == 'any'):
                    src_port_list.append(vnc_api.PortType(
                            start_port = -1, end_port = -1))
                else:
                    s_e = arg_val.split(':')
                    src_port_list.append(vnc_api.PortType(
                            start_port = int(s_e[0]), end_port = int(s_e[1])))
            elif (arg_name == 'action'):
                action = arg_val
            elif (arg_name == 'service'):
                service_list.append('default-domain:%s:%s' \
                        %(self.tenant.name, arg_val))
 
        rule = vnc_api.PolicyRuleType()
        if not direction:
            direction = '<>'
        rule.set_direction(direction)
        if not protocol:
            protocol = 'any'
        rule.set_protocol(protocol)
        if not src_net_list:
            src_net_list.append(vnc_api.AddressType(virtual_network = 'any'))
        rule.set_src_addresses(src_net_list)
        if not dst_net_list:
            dst_net_list.append(vnc_api.AddressType(virtual_network = 'any'))
        rule.set_dst_addresses(dst_net_list)
        if not src_port_list:
            src_port_list.append(vnc_api.PortType(
                    start_port = -1, end_port = -1))
        rule.set_src_ports(src_port_list)
        if not dst_port_list:
            dst_port_list.append(vnc_api.PortType(
                    start_port = -1, end_port = -1))
        rule.set_dst_ports(dst_port_list)
        if not action:
            action_list = vnc_api.ActionListType(simple_action = 'pass')
        elif (action == 'service'):
            action_list = vnc_api.ActionListType(apply_service = service_list)
        else:
            action_list = vnc_api.ActionListType(simple_action = action)
        rule.set_action_list(action_list)
        return rule

    def add(self, name, rule_arg_list):
        rule_list = []
        if not rule_arg_list:
            rule = self.rule_add([])
            rule_list.append(rule)
        else:
            for rule_arg in rule_arg_list:
                rule = self.rule_add(rule_arg.split(','))
                rule_list.append(rule)

        obj = self.obj_get(name = name)
        if obj:
            rules = obj.get_network_policy_entries()
            if not rules:
                rules = vnc_api.PolicyEntriesType(policy_rule = rule_list)
            else:
                for item in rule_list:
                    rules.add_policy_rule(item)
            obj.set_network_policy_entries(rules)
            try:
                self.vnc.network_policy_update(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))
        else:
            rules = vnc_api.PolicyEntriesType(policy_rule = rule_list)
            obj = vnc_api.NetworkPolicy(name = name,
                    parent_obj = self.tenant,
                    network_policy_entries = rules)
            try:
                self.vnc.network_policy_create(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))

    def delete(self, name, rule_arg_list):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
            return
        if rule_arg_list:
            rules = obj.get_network_policy_entries()
            if not rules:
                return
            for rule_arg in rule_arg_list:
                for arg in rule_arg.split(','):
                    arg_name = arg.split('=')[0]
                    arg_val = arg.split('=')[1]
                    if (arg_name == 'index'):
                        rule = rules.get_policy_rule()[int(arg_val) - 1]
                        rules.delete_policy_rule(rule)
            obj.set_network_policy_entries(rules)
            self.vnc.network_policy_update(obj)
        else:
            try:
                self.vnc.network_policy_delete(fq_name = ['default-domain',
                        self.tenant.name, name])
            except Exception as e:
                print 'ERROR: %s' %(str(e))


class ConfigSecurityGroup():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.security_groups_list()['security-groups']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.security_group_read(id = item['uuid'])

    def addr_show(self, addr_list):
        for item in addr_list:
            print '        Security Group: %s' %(item.get_security_group())
            subnet = item.get_subnet()
            if subnet:
                print '        Subnet: %s/%d' %(subnet.get_ip_prefix(), \
                        subnet.get_ip_prefix_len())
            else:
                print '        Subnet: None'

    def port_show(self, port_list):
        for item in port_list:
            print '        %d:%d' %(item.get_start_port(), item.get_end_port())

    def rule_show(self, obj):
        rules_obj = obj.get_security_group_entries()
        if (rules_obj == None):
            return
        list = rules_obj.get_policy_rule()
        count = 1
        for rule in list:
            print 'Rule #%d' %(count)
            print '    Direction: %s' %(rule.get_direction())
            print '    Protocol: %s' %(rule.get_protocol())
            print '    Source Addresses:'
            self.addr_show(rule.get_src_addresses())
            print '    Source Ports:'
            self.port_show(rule.get_src_ports())
            print '    Destination Addresses:'
            self.addr_show(rule.get_dst_addresses())
            print '    Destination Ports:'
            self.port_show(rule.get_dst_ports())
            count += 1

    def obj_show(self, obj):
        print 'Security Group'
        print 'Name: %s' %(obj.get_fq_name())
        print 'UUID: %s' %(obj.uuid)
        self.rule_show(obj)

    def show(self, name):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def add(self, name, protocol = None, address = None, port = None,
            direction = None):
        rule = vnc_api.PolicyRuleType()
        rule.set_direction('>')
        if protocol:
            rule.set_protocol(protocol)
        else:
            rule.set_protocol('any')

        addr_list = []
        if address:
            for item in address:
                prefix = item.split('/')[0]
                len = item.split('/')[1]
                addr_list.append(vnc_api.AddressType(
                        subnet = vnc_api.SubnetType(
                        ip_prefix = prefix, ip_prefix_len = int(len))))
        else:
            addr_list.append(vnc_api.AddressType(
                    subnet = vnc_api.SubnetType(
                    ip_prefix = '0.0.0.0', ip_prefix_len = 0)))

        local_addr_list = [vnc_api.AddressType(security_group = 'local')]

        port_list = []
        if port:
            for item in port:
                if (item == 'any'):
                    port_list.append(vnc_api.PortType(
                            start_port = -1, end_port = -1))
                else:
                    s_e = item.split(':')
                    port_list.append(vnc_api.PortType(
                            start_port = int(s_e[0]), end_port = int(s_e[1])))
        else:
            port_list.append(vnc_api.PortType(start_port = -1, end_port = -1))

        local_port_list = [vnc_api.PortType(start_port = -1, end_port = -1)]

        if (direction == 'ingress'):
            rule.set_src_addresses(addr_list)
            rule.set_src_ports(port_list)
            rule.set_dst_addresses(local_addr_list)
            rule.set_dst_ports(local_port_list)
        else:
            rule.set_src_addresses(local_addr_list)
            rule.set_src_ports(local_port_list)
            rule.set_dst_addresses(addr_list)
            rule.set_dst_ports(port_list)

        obj = self.obj_get(name = name)
        if obj:
            rules = obj.get_security_group_entries()
            if not rules:
                rules = vnc_api.PolicyEntriesType(policy_rule = [rule])
            else:
                rules.add_policy_rule(rule)
            try:
                self.vnc.security_group_update(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))
        else:
            rules = vnc_api.PolicyEntriesType(policy_rule = [rule])
            obj = vnc_api.SecurityGroup(name = name,
                    parent_obj = self.tenant,
                    security_group_entries = rules)
            try:
                self.vnc.security_group_create(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))

    def rule_del(self, obj, index):
        rules = obj.get_security_group_entries()
        if not rules:
            return
        rule = rules.get_policy_rule()[index - 1]
        rules.delete_policy_rule(rule)
        self.vnc.security_group_update(obj)

    def delete(self, name, rule = None):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
            return
        if rule:
            self.rule_del(obj, int(rule))
        else:
            try:
                self.vnc.security_group_delete(fq_name = ['default-domain',
                        self.tenant.name, name])
            except Exception as e:
                print 'ERROR: %s' %(str(e))


class ConfigNetwork():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.virtual_networks_list()['virtual-networks']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.virtual_network_read(id = item['uuid'])

    def prop_route_target_show(self, obj):
        print '[P] Route targets:'
        rt_list = obj.get_route_target_list()
        if not rt_list:
            return
        for rt in rt_list.get_route_target():
            print '    %s' %(rt)

    def child_floating_ip_pool_show(self, obj):
        print '[C] Floating IP pools:'
        pool_list = obj.get_floating_ip_pools()
        if not pool_list:
            return
        for pool in pool_list:
            print '    %s' %(pool['to'][3])
            pool_obj = self.vnc.floating_ip_pool_read(id = pool['uuid'])
            ip_list = pool_obj.get_floating_ips()
            if (ip_list != None):
                for ip in ip_list:
                    ip_obj = self.vnc.floating_ip_read(id = ip['uuid'])
                    print '        %s' %(ip_obj.get_floating_ip_address())

    def ref_ipam_show(self, obj):
        print '[R] IPAMs:'
        ipam_list = obj.get_network_ipam_refs()
        if not ipam_list:
            return
        for item in ipam_list:
            print '    %s' %(item['to'][2])
            subnet_list = item['attr'].get_ipam_subnets()
            for subnet in subnet_list:
                print '        subnet: %s/%d, gateway: %s' %(
                        subnet.get_subnet().get_ip_prefix(),
                        subnet.get_subnet().get_ip_prefix_len(),
                        subnet.get_default_gateway())

    def ref_policy_show(self, obj):
        print '[R] Policies:'
        policy_list = obj.get_network_policy_refs()
        if not policy_list:
            return
        for item in policy_list:
            print '    %s (%d.%d)' %(item['to'][2],
                    item['attr'].get_sequence().get_major(),
                    item['attr'].get_sequence().get_minor())

    def ref_route_table_show(self, obj):
        print '[R] Route Tables:'
        rt_list = obj.get_route_table_refs()
        if not rt_list:
            return
        for item in rt_list:
            print '    %s' %(item['to'][2])

    def obj_show(self, obj):
        print 'Virtual Network'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)
        self.prop_route_target_show(obj)
        self.child_floating_ip_pool_show(obj)
        self.ref_ipam_show(obj)
        self.ref_policy_show(obj)
        self.ref_route_table_show(obj)

    def show(self, name):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def ipam_add(self, obj, name, subnet, gateway = None):
        try:
            ipam_obj = self.vnc.network_ipam_read(fq_name = ['default-domain',
                    self.tenant.name, name])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        cidr = subnet.split('/')
        subnet = vnc_api.SubnetType(ip_prefix = cidr[0],
                ip_prefix_len = int(cidr[1]))
        ipam_subnet = vnc_api.IpamSubnetType(subnet = subnet,
                default_gateway = gateway)
        obj.add_network_ipam(ref_obj = ipam_obj,    
                ref_data = vnc_api.VnSubnetsType([ipam_subnet]))

    def ipam_del(self, obj, name):
        try:
            ipam_obj = self.vnc.network_ipam_read(fq_name = ['default-domain',
                    self.tenant.name, name])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.del_network_ipam(ref_obj = ipam_obj)

    def policy_add(self, obj, name):
        try:
            policy_obj = self.vnc.network_policy_read(
                    fq_name = ['default-domain', self.tenant.name, name])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        seq = vnc_api.SequenceType(major = 0, minor = 0)
        obj.add_network_policy(ref_obj = policy_obj,
                ref_data = vnc_api.VirtualNetworkPolicyType(sequence = seq))

    def policy_del(self, obj, name):
        try:
            policy_obj = self.vnc.network_policy_read(
                    fq_name = ['default-domain', self.tenant.name, name])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.del_network_policy(ref_obj = policy_obj)

    def route_target_add(self, obj, rt):
        rt_list = obj.get_route_target_list()
        if not rt_list:
            rt_list = vnc_api.RouteTargetList()
            obj.set_route_target_list(rt_list)
        rt_list.add_route_target('target:%s' %(rt))

    def route_target_del(self, obj, rt):
        rt_list = obj.get_route_target_list()
        if not rt_list:
            return
        rt_list.delete_route_target('target:%s' %(rt))

    def route_table_add(self, obj, rt):
        try:
            rt_obj = self.vnc.route_table_read(fq_name = ['default-domain',
                    self.tenant.name, rt])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.add_route_table(ref_obj = rt_obj)

    def route_table_del(self, obj, rt):
        try:
            rt_obj = self.vnc.route_table_read(fq_name = ['default-domain',
                    self.tenant.name, rt])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.del_route_table(ref_obj = rt_obj)

    def add(self, name, ipam = None, subnet = None, policy = None,
            route_target = None, route_table = None, shared = None,
            external = None, l2 = None):
        create = False
        obj = self.obj_get(name)
        if not obj:
            obj = vnc_api.VirtualNetwork(name = name,
                    parent_obj = self.tenant)
            if l2:
                prop = vnc_api.VirtualNetworkType(forwarding_mode = 'l2')
                obj.set_virtual_network_properties(prop)
            if shared:
                obj.set_is_shared(shared)
            if external:
                obj.set_router_external(external)
            create = True
        if ipam and subnet:
            self.ipam_add(obj, ipam, subnet)
        if policy:
            self.policy_add(obj, policy)
        if route_target:
            self.route_target_add(obj, route_target)
        if route_table:
            self.route_table_add(obj, route_table)
        if create:
            try:
                self.vnc.virtual_network_create(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))
        else:
            self.vnc.virtual_network_update(obj)

    def delete(self, name, ipam = None, policy = None, route_target = None,
            route_table = None):
        update = False
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
        if ipam:
            self.ipam_del(obj, ipam)
            update = True
        if policy:
            self.policy_del(obj, policy)
            update = True
        if route_target:
            self.route_target_del(obj, route_target)
            update = True
        if route_table:
            self.route_table_del(obj, route_table)
            update = True
        if update:
            self.vnc.virtual_network_update(obj)
        else:
            try:
                self.vnc.virtual_network_delete(id = obj.uuid)
            except Exception as e:
                print 'ERROR: %s' %(str(e))


class ConfigFloatingIpPool():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.floating_ip_pools_list()['floating-ip-pools']
        return list

    def obj_get(self, name, network = None):
        for item in self.obj_list():
            if network:
                if (item['fq_name'][1] == self.tenant.name) and \
                        (item['fq_name'][2] == network) and \
                        (item['fq_name'][3] == name):
                    return self.vnc.floating_ip_pool_read(id = item['uuid'])
            else:
                if (item['fq_name'][1] == self.tenant.name) and \
                        (item['fq_name'][3] == name):
                    return self.vnc.floating_ip_pool_read(id = item['uuid'])

    def prop_subnet_show(self, obj):
        print '[P] Subnet:'
        prefixes = obj.get_floating_ip_pool_prefixes()
        if not prefixes:
            return
        for item in prefixes.get_subnet():
            print '    %s/%s' %(item.get_ip_prefix(), item.get_ip_prefix_len())

    def child_ip_show(self, obj):
        print '[C] Floating IPs:'
        list = obj.get_floating_ips()
        if not list:
            return
        for ip in list:
            ip_obj = self.vnc.floating_ip_read(id = ip['uuid'])
            print '    %s' %(ip_obj.get_floating_ip_address())

    def back_ref_tenant_show(self, obj):
        print '[BR] Tenants:'
        list = obj.get_project_back_refs()
        if not list:
            return
        for item in list:
            print '    %s' %(item['to'][1])

    def obj_show(self, obj):
        print 'Floating IP Pool'
        print 'Name: %s' %(obj.get_fq_name())
        print 'UUID: %s' %(obj.uuid)
        self.prop_subnet_show(obj)
        self.child_ip_show(obj)
        self.back_ref_tenant_show(obj)

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s in network %s' \
                            %(item['fq_name'][2], item['fq_name'][3])

    def add(self, name, network):
        if not name:
            print 'ERROR: The name of floating IP pool is not specified!'
            return
        if not network:
            print 'ERROR: Network is not specified!'
            return
        try:
            net_obj = self.vnc.virtual_network_read(
                    fq_name = ['default-domain', self.tenant.name, network])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj = vnc_api.FloatingIpPool(name = name, parent_obj = net_obj)
        try:
            self.vnc.floating_ip_pool_create(obj)
            self.tenant.add_floating_ip_pool(obj)
            self.vnc.project_update(self.tenant)
        except Exception as e:
            print 'ERROR: %s' %(str(e))

    def fip_delete(self, pool_obj):
        pass

    def delete(self, name, network):
        if not name:
            print 'ERROR: The name of floating IP pool is not specified!'
            return
        obj = self.obj_get(name, network)
        if not obj:
            print 'ERROR: Floating IP pool %s in network %s is not found!' \
                    %(name, network)
            return
        if obj.get_floating_ips():
            print 'ERROR: There are allocated floating IPs!'
            return
        for tenant_ref in obj.get_project_back_refs():
            tenant = self.vnc.project_read(fq_name = tenant_ref['to'])
            tenant.del_floating_ip_pool(obj)
            self.vnc.project_update(tenant)
        try:
            self.vnc.floating_ip_pool_delete(id = obj.uuid)
        except Exception as e:
            print 'ERROR: %s' %(str(e))


class ConfigServiceTemplate():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.service_templates_list()['service-templates']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == name):
                return self.vnc.service_template_read(id = item['uuid'])

    def obj_show(self, obj):
        print 'Service Template'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)
        properties = obj.get_service_template_properties()
        print 'Service Mode: %s' %(properties.get_service_mode())
        print 'Service Type: %s' %(properties.get_service_type())
        print 'Service Image: %s' %(properties.get_image_name())
        print 'Service Flavor: %s' %(properties.get_flavor())
        print 'Service Interfaces:'
        for item in properties.get_interface_type():
            print '    %s' %(item.get_service_interface_type())

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                print '    %s' %(item['fq_name'][1])

    def add(self, name, mode, type, image, flavor, interface_type,
            scale = None):
        obj = vnc_api.ServiceTemplate(name = name)
        properties = vnc_api.ServiceTemplateType(service_mode = mode,
                service_type = type, image_name = image, flavor = flavor,
                ordered_interfaces = True, availability_zone_enable = True)
        if scale:
            properties.set_service_scaling(scale)
            for item in interface_type:
                if (mode == 'transparent') and \
                       ((item == 'left') or (item == 'right')):
                    shared_ip = True
                elif (mode == 'in-network') and (item == 'left'):
                    shared_ip = True
                else:
                    shared_ip = False
                type = vnc_api.ServiceTemplateInterfaceType(
                        service_interface_type = item,
                        shared_ip = shared_ip,
                        static_route_enable = True)
                properties.add_interface_type(type)
        else:
            for item in interface_type:
                type = vnc_api.ServiceTemplateInterfaceType(
                        service_interface_type = item,
                        static_route_enable = True)
                properties.add_interface_type(type)
        obj.set_service_template_properties(properties)
        try:
            self.vnc.service_template_create(obj)
        except Exception as e:
            print 'ERROR: %s' %(str(e))

    def delete(self, name):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
        try:
            self.vnc.service_template_delete(id = obj.uuid)
        except Exception as e:
            print 'ERROR: %s' %(str(e))


class ConfigServiceInstance():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.service_instances_list()['service-instances']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.service_instance_read(id = item['uuid'])

    def obj_show(self, obj):
        print 'Service Instance'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)

    def show(self, name):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def add(self, name, template, network_list,
            auto_policy = None, scale_max = None):
        obj = vnc_api.ServiceInstance(name = name, parent_obj = self.tenant)
        properties = vnc_api.ServiceInstanceType(auto_policy = auto_policy)
        for net in network_list:
            net_name = None
            net_route = None
            net_auto = False
            tenant_name = self.tenant.name
            for arg in net.split(','):
                arg_name = arg.split('=')[0]
                arg_val = arg.split('=')[1]
                if (arg_name == 'tenant'):
                    tenant_name = arg_val
                elif (arg_name == 'network'):
                    if (arg_val == 'auto'):
                        net_auto = True
                    else:
                        net_name = arg_val
                elif (arg_name == 'route'):
                    net_route = arg_val
            if net_auto:
                net_fq_name = None
            else:
                net_fq_name = 'default-domain:%s:%s' %(tenant_name, net_name)
            interface = vnc_api.ServiceInstanceInterfaceType(
                    virtual_network = net_fq_name)
            if net_route:
                route = vnc_api.RouteType(prefix = net_route)
                route_table = vnc_api.RouteTableType()
                route_table.add_route(route)
                interface.set_static_routes(route_table)
            properties.add_interface_list(interface)

        if scale_max:
            scale = vnc_api.ServiceScaleOutType(
                    max_instances = int(scale_max),
                    auto_scale = True)
        else:
            scale = vnc_api.ServiceScaleOutType()
        properties.set_scale_out(scale)

        obj.set_service_instance_properties(properties)
        try:
            template = self.vnc.service_template_read(
                    fq_name = ['default-domain', template])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
        obj.set_service_template(template)
        try:
            self.vnc.service_instance_create(obj)
        except Exception as e:
            print 'ERROR: %s' %(str(e))

    def delete(self, name):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
        try:
            self.vnc.service_instance_delete(id = obj.uuid)
        except Exception as e:
            print 'ERROR: %s' %(str(e))


class ConfigImage():
    def __init__(self, client):
        self.nova = client.nova

    def obj_list(self):
        list = self.nova.images.list()
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item.name == name):
                return item

    def obj_show(self, obj):
        print 'Image'
        print 'Name: %s' %(obj.name)      
        print 'UUID: %s' %(obj.id)

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                print '    %s' %(item.name)

    def add(self, name):
        pass
    def delete(self, name):
        pass


class ConfigFlavor():
    def __init__(self, client):
        self.nova = client.nova

    def obj_list(self):
        list = self.nova.flavors.list()
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item.name == name):
                return item

    def obj_show(self, obj):
        print 'Flavor'
        print 'Name: %s' %(obj.name)      
        print 'UUID: %s' %(obj.id)

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                print '    %s' %(item.name)

    def add(self, name):
        pass
    def delete(self, name):
        pass


class ConfigVirtualMachine():
    def __init__(self, client):
        self.vnc = client.vnc
        self.nova = client.nova
        self.tenant = client.tenant

    def obj_list(self):
        list = self.nova.servers.list()
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item.name == name):
                return item

    def obj_show(self, obj):
        print 'Virtual Machine'
        print 'Name: %s' %(obj.name)      
        print 'UUID: %s' %(obj.id)
        print 'Status: %s' %(obj.status)
        print 'Addresses:'
        for item in obj.addresses.keys():
            print '    %s  %s' %(obj.addresses[item][0]['addr'], item)

    def show(self, name):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                print '    %s' %(item.name)

    def add(self, name, image, flavor, network, node = None, user_data = None,
            wait = None):
        try:
            image_obj = self.nova.images.find(name = image)
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        try:
            flavor_obj = self.nova.flavors.find(name = flavor)
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return

        networks = []
        net_list = self.vnc.virtual_networks_list()['virtual-networks']
        for item in network:
            for vn in net_list:
                if (vn['fq_name'][1] == self.tenant.name) and \
                        (vn['fq_name'][2] == item):
                    networks.append({'net-id': vn['uuid']})
                    break
            else:
                print 'ERROR: Network %s is not found!' %(item)
                return

        #if node:
        #    zone = self.nova.availability_zones.list()[1]
        #    for item in zone.hosts.keys():
        #        if (item == node):
        #            break
        #    else:
        #        print 'ERROR: Node %s is not found!' %(name)
        #        return

        try:
            vm = self.nova.servers.create(name = name, image = image_obj,
                    flavor = flavor_obj, availability_zone = node,
                    nics = networks, userdata = user_data)
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return

        if wait:
            timeout = 12
            while timeout:
                time.sleep(3)
                vm = self.nova.servers.get(vm.id)
                if vm.status != 'BUILD':
                    print 'VM %s is %s' %(vm.name, vm.status)
                    break
                timeout -= 1

    def delete(self, name):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
        self.nova.servers.delete(obj.id)


class ConfigRouteTable():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.route_tables_list()['route-tables']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.route_table_read(id = item['uuid'])

    def obj_show(self, obj):
        print 'Route Table'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)
        routes = obj.get_routes()
        if not routes:
            return
        for item in routes.get_route():
            print '  %s next-hop %s' %(item.get_prefix(), item.get_next_hop())

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def route_add(self, obj, route):
        routes = obj.get_routes()
        if not routes:
            routes = vnc_api.RouteTableType()
            obj.set_routes(routes)
        prefix = route.split(':')[0]
        nh = 'default-domain:%s:%s' %(self.tenant.name, route.split(':')[1])
        routes.add_route(vnc_api.RouteType(prefix = prefix, next_hop = nh))

    def route_del(self, obj, prefix):
        routes = obj.get_routes()
        if not routes:
            return
        for item in routes.get_route():
            if (item.get_prefix() == prefix):
                routes.delete_route(item)

    def add(self, name, route = None):
        create = False
        obj = self.obj_get(name)
        if not obj:
            obj = vnc_api.RouteTable(name = name, parent_obj = self.tenant)
            create = True
        if route:
            for item in route:
                self.route_add(obj, item)
        if create:
            try:
                self.vnc.route_table_create(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))
        else:
            self.vnc.route_table_update(obj)

    def delete(self, name, route = None):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
        if route:
            for item in route:
                self.route_del(obj, item)
            self.vnc.route_table_update(obj)
        else:
            try:
                self.vnc.route_table_delete(id = obj.uuid)
            except Exception as e:
                print 'ERROR: %s' %(str(e))


class ConfigInterfaceRouteTable():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.interface_route_tables_list()['interface-route-tables']
        return list

    def obj_get(self, name):
        for item in self.obj_list():
            if (item['fq_name'][1] == self.tenant.name) and \
                    (item['fq_name'][2] == name):
                return self.vnc.interface_route_table_read(id = item['uuid'])

    def obj_show(self, obj):
        print 'Interface Route Table'
        print 'Name: %s' %(obj.get_fq_name())      
        print 'UUID: %s' %(obj.uuid)
        routes = obj.get_interface_route_table_routes()
        if not routes:
            return
        for item in routes.get_route():
            print '  %s' %(item.get_prefix())

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj)
        else:
            for item in self.obj_list():
                if (item['fq_name'][1] == self.tenant.name):
                    print '    %s' %(item['fq_name'][2])

    def route_add(self, obj, prefix):
        routes = obj.get_interface_route_table_routes()
        if not routes:
            routes = vnc_api.RouteTableType()
        routes.add_route(vnc_api.RouteType(prefix = prefix))
        obj.set_interface_route_table_routes(routes)

    def route_del(self, obj, prefix):
        routes = obj.get_interface_route_table_routes()
        if not routes:
            return
        for item in routes.get_route():
            if (item.get_prefix() == prefix):
                routes.delete_route(item)
        obj.set_interface_route_table_routes(routes)

    def add(self, name, route = None):
        create = False
        obj = self.obj_get(name)
        if not obj:
            obj = vnc_api.InterfaceRouteTable(name = name,
                    parent_obj = self.tenant)
            create = True
        if route:
            for item in route:
                self.route_add(obj, item)
        if create:
            try:
                self.vnc.interface_route_table_create(obj)
            except Exception as e:
                print 'ERROR: %s' %(str(e))
        else:
            self.vnc.interface_route_table_update(obj)

    def delete(self, name, route = None):
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
        if route:
            for item in route:
                self.route_del(obj, item)
            self.vnc.interface_route_table_update(obj)
        else:
            try:
                self.vnc.interface_route_table_delete(id = obj.uuid)
            except Exception as e:
                print 'ERROR: %s' %(str(e))


class ConfigVmInterface():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant
        self.nova = client.nova

    def obj_list(self, vm_id = None):
        list = []
        if vm_id:
            vm = self.vnc.virtual_machine_read(id = vm_id)
            if_ref_list = vm.get_virtual_machine_interface_back_refs()
            for if_ref in if_ref_list:
                if_obj = self.vnc.virtual_machine_interface_read(
                        id = if_ref['uuid'])
                vn_name = if_obj.get_virtual_network_refs()[0]['to'][2]
                list.append({'name':vn_name, 'uuid':if_ref['uuid'],
                        'obj':if_obj})
        else:
            for vm_nova in self.nova.servers.list():
                vm = self.vnc.virtual_machine_read(id = vm_nova.id)
                if_ref_list = vm.get_virtual_machine_interface_back_refs()
                for if_ref in if_ref_list:
                    if_obj = self.vnc.virtual_machine_interface_read(
                            id = if_ref['uuid'])
                    vn_name = if_obj.get_virtual_network_refs()[0]['to'][2]
                    list.append({'name':'%s:%s' %(vm_nova.name, vn_name),
                            'uuid':if_ref['uuid'], 'obj':if_obj})
        return list

    def obj_get(self, name, vm_id = None):
        list = self.obj_list(vm_id)
        for item in list:
            if (item['name'] == name):
                return item['obj']

    def prop_mac_show(self, obj):
        print '[P] MAC addresses:'
        mac = obj.get_virtual_machine_interface_mac_addresses()
        if not mac:
            return
        for item in mac.get_mac_address():
            print '    %s' %(item)

    def prop_prop_show(self, obj):
        prop = obj.get_virtual_machine_interface_properties()
        if not prop:
            return
        print '[P] Service interface type: %s' \
                %(prop.get_service_interface_type())
        print '[P] Interface mirror: %s' %(prop.get_interface_mirror())

    def ref_sg_show(self, obj):
        print '[R] Security groups:'
        refs = obj.get_security_group_refs()
        if refs:
            for item in obj.get_security_group_refs():
                print '    %s' %(item['to'][2])

    def ref_net_show(self, obj):
        print '[R] Virtual networks:'
        for item in obj.get_virtual_network_refs():
            print '    %s' %(item['to'][2])

    def ref_irt_show(self, obj):
        print '[R] Interface route tables:'
        list = obj.get_interface_route_table_refs()
        if list:
            for item in list:
                print '    %s' %(item['to'][2])

    def back_ref_ip_show(self, obj):
        print '[BR] Instance IPs:'
        list = obj.get_instance_ip_back_refs()
        if not list:
            return
        for item in list:
            ip = self.vnc.instance_ip_read(id = item['uuid'])
            print '    %s' %(ip.get_instance_ip_address())

    def back_ref_fip_show(self, obj):
        print '[BR] Floating IPs:'
        list = obj.get_floating_ip_back_refs()
        if not list:
            return
        for item in list:
            ip = self.vnc.floating_ip_read(id = item['uuid'])
            print '    %s' %(ip.get_floating_ip_address())

    def obj_show(self, obj, name):
        print 'Virtual Machine Interface'
        print 'Name: %s' %(name)      
        print 'UUID: %s' %(obj.uuid)
        self.prop_mac_show(obj)
        self.prop_prop_show(obj)
        self.ref_sg_show(obj)
        self.ref_net_show(obj)
        self.ref_irt_show(obj)
        self.back_ref_ip_show(obj)
        self.back_ref_fip_show(obj)

    def show(self, name = None):
        if name:
            obj = self.obj_get(name)
            if not obj:
                print 'ERROR: Object %s is not found!' %(name)
                return
            self.obj_show(obj, name)
        else:
            for item in self.obj_list():
                    print '    %s' %(item['name'])

    def sg_add(self, obj, sg):
        try:
            sg_obj = self.vnc.security_group_read(
                    fq_name = ['default-domain', self.tenant.name, sg])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.add_security_group(sg_obj)

    def addr_add(self, obj, addr):
        id = str(uuid.uuid4())
        ip_obj = vnc_api.InstanceIp(name = id, instance_ip_address = addr)
        ip_obj.uuid = id
        ip_obj.add_virtual_machine_interface(obj)
        vn_id = obj.get_virtual_network_refs()[0]['uuid']
        vn_obj = self.vnc.virtual_network_read(id = vn_id)
        ip_obj.add_virtual_network(vn_obj)
        self.vnc.instance_ip_create(ip_obj)

    def irt_add(self, obj, irt):
        try:
            table_obj = self.vnc.interface_route_table_read(
                    fq_name = ['default-domain', self.tenant.name, irt])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.add_interface_route_table(table_obj)

    def fip_add(self, obj, fip_pool, fip):
        pool_name = fip_pool.split(':')
        pool_name.insert(0, 'default-domain')
        try:
            pool_obj = self.vnc.floating_ip_pool_read(fq_name = pool_name)
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        id = str(uuid.uuid4())
        fip_obj = vnc_api.FloatingIp(name = id, parent_obj = pool_obj)
        fip_obj.uuid = id
        if (fip != 'any'):
            fip_obj.set_floating_ip_address(fip)
        fip_obj.add_project(self.tenant)
        fip_obj.add_virtual_machine_interface(obj)
        self.vnc.floating_ip_create(fip_obj)
        self.tenant.add_floating_ip_pool(pool_obj)
        self.vnc.project_update(self.tenant)

    def add(self, name, sg = None, irt = None, addr = None,
            fip_pool = None, fip = None):
        update = False
        obj = self.obj_get(name)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
            return
        if sg:
            self.sg_add(obj, sg)
            update = True
        if irt:
            self.irt_add(obj, irt)
            update = True
        if addr:
            self.addr_add(obj, addr)
            update = True
        if fip and fip_pool:
            self.fip_add(obj, fip_pool, fip)
            update = True
        if update:
            self.vnc.virtual_machine_interface_update(obj)

    def sg_del(self, obj, sg):
        try:
            sg_obj = self.vnc.security_group_read(
                    fq_name = ['default-domain', self.tenant.name, sg])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.del_security_group(sg_obj)

    def irt_del(self, obj, irt):
        try:
            table_obj = self.vnc.interface_route_table_read(
                    fq_name = ['default-domain', self.tenant.name, irt])
        except Exception as e:
            print 'ERROR: %s' %(str(e))
            return
        obj.del_interface_route_table(table_obj)

    def addr_del(self, obj, addr):
        ip_list = obj.get_instance_ip_back_refs()
        for ip in ip_list:
            ip_obj = self.vnc.instance_ip_read(id = ip['uuid'])
            if (ip_obj.get_instance_ip_address() == addr):
                self.vnc.instance_ip_delete(id = ip_obj.uuid)
                break
        else:
            print 'ERROR: IP address %s is not found!' %(addr)

    def fip_del(self, obj):
        list = obj.get_floating_ip_back_refs()
        if not list:
            return
        for item in list:
            ip = self.vnc.floating_ip_delete(id = item['uuid'])

    def delete(self, name, sg = None, irt = None, addr = None,
            fip = None, vm_id = None):
        update = False
        obj = self.obj_get(name, vm_id)
        if not obj:
            print 'ERROR: Object %s is not found!' %(name)
            return
        if sg:
            self.sg_del(obj, sg)
            update = True
        if irt:
            self.irt_del(obj, irt)
            update = True
        if addr:
            self.addr_del(obj, addr)
            update = True
        if fip:
            self.fip_del(obj)
            update = True
        if update:
            self.vnc.virtual_machine_interface_update(obj)


class ConfigGlobalVrouter():
    def __init__(self, client):
        self.vnc = client.vnc
        self.tenant = client.tenant

    def obj_list(self):
        list = self.vnc.interface_route_tables_list()['interface-route-tables']
        return list

    def obj_get(self, name):
        obj = self.vnc.global_vrouter_config_read(
                fq_name = ['default-global-system-config',
                'default-global-vrouter-config'])
        return obj

    def obj_show(self, obj):
        pass

    def show(self, name = None):
        obj = self.obj_get('dummy')
        print 'Link Local Service'
        for item in obj.get_linklocal_services().get_linklocal_service_entry():
            print '  %s  %s:%s  %s:%s' %(item.get_linklocal_service_name(),
                    item.get_linklocal_service_ip(),
                    item.get_linklocal_service_port(),
                    item.get_ip_fabric_service_ip()[0],
                    item.get_ip_fabric_service_port())

    def add(self, name, link_local_addr, fabric_addr):
        obj = self.obj_get('dummy')
        list = obj.get_linklocal_services().get_linklocal_service_entry()
        list.append(vnc_api.LinklocalServiceEntryType(
                linklocal_service_name = name,
                linklocal_service_ip = link_local_addr.split(':')[0],
                linklocal_service_port = int(link_local_addr.split(':')[1]),
                ip_fabric_service_ip = [fabric_addr.split(':')[0]],
                ip_fabric_service_port = int(fabric_addr.split(':')[1])))
        self.vnc.global_vrouter_config_update(obj)

    def delete(self, name):
        obj = self.obj_get('dummy')
        list = obj.get_linklocal_services().get_linklocal_service_entry()
        for item in list:
            if (item.get_linklocal_service_name() == name):
                list.remove(item)
                break
        self.vnc.global_vrouter_config_update(obj)

class ConfigClient():
    def __init__(self, username, password, tenant, region, api_server):
        self.vnc = vnc_api.VncApi(username = username, password = password,
                tenant_name = tenant, api_server_host = api_server)
        if config_nova:
            self.nova = novaclient.v1_1.client.Client(username = username,
                    api_key = password, project_id = tenant,
                    region_name = region,
                    auth_url = 'http://%s:35357/v2.0' %(api_server))
        else:
            self.nova = None
        self.tenant = self.vnc.project_read(
                fq_name = ['default-domain', tenant])

