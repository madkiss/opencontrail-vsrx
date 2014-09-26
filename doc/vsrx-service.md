#Goal
To build an integrated solution for end user.
* Create a service with vSRX in the service chain.
* Base on the official release of vSRX, no manual configuration is required.
* One single step for end user to create and provisioning the service.

#1 vSRX and OpenStack
vSRX (Firefly Perimeter) is the virtualization of SRX service gateway provided by Juniper. This is the product page.
http://www.juniper.net/us/en/products-services/security/firefly-perimeter/#overview

The KVM-based vSRX is packed in JVA container. It's available on this link to download.
http://www.juniper.net/support/downloads/?p=firefly#sw

##1.1 Add vSRX image
* Download vSRX JVA container and unpack it.
```
# chmod 755 junos-vsrx-12.1X46-D20.5-domestic.jva
# ./junos-vsrx-12.1X46-D20.5-domestic.jva -x
```
* Add vSRX image into OpenStack.
```
# cd junos-vsrx-12.1X46-D20.5-domestic-1400526077
# glance --os-username <admin username> --os-password <admin password> --os-tenant-name admin --os-auth-url http://127.0.0.1:5000/v2.0/ image-create --name "vSRX 12.1X46-D20.5" --disk-format qcow2 --container-format bare --is-public True --file junos-vsrx-12.1X46-D20.5-domestic.img 
```

##1.2 Launch vSRX instance
The minimum resource required by vSRX is 2 vCPUs and 1GB memory. Assume a network is already configured in tennant demo.
```
# nova --os-username <admin username> --os-password <admin password> --os-tenant-name demo --os-auth-url http://127.0.0.1:5000/v2.0/ boot vsrx --flavor m1.medium --image "vSRX 12.1X46-D20.5" --nic net-id=<network UUID>
```
Now, vSRX instance can be accessed by console from OpenStack Web UI.

##1.3 Provisioning vSRX
At the first time when vSRX is launched, there is no configuration applied. Normally, user needs to login vSRX from console to do the initial configuration, like root user authentication and networking interface. After that, any further configuration can be done by mulitple options, like management Web on vSRX, SSH, NETCONF, etc.

###1.3.1 Metadata
This is the standard option for OpenStack to pass data into VM after launching it. VM needs to read from http://169.254.169.254 to get metadata. This is not supported by vSRX yet.

###1.3.2 File injection
This is another option for OpenStack to transfer data into VM. Potentially, a configuration file can be injected into vSRX and get applied. This is not supported by vSRX yet.

###1.3.3 Sysinfo
This is the only option supported by vSRX to get data for initial configuration. But it's not supported by OpenStack. To make this work with OpenStack, one additionaly line needs to be added into function `get_guest_config_sysinfo()` in `class LibvirtDriver()` in nova/virt/libvirt/driver.py. And service openstack-nova-compute needs to be restarted to apply the update.
```
         sysinfo.system_serial = self.get_host_uuid()
         sysinfo.system_uuid = instance['uuid']
+        sysinfo.bios_version = ';dhcp=yes;rootpw=$1$TCXFwR9d$enGW30hmBFmGNrxIFYPB30;'

         return sysinfo
```
The root password `rootpw` is the hashed string of 'passWD'.
```
# service openstack-nova-compute restart
```

This update will add new entry into /var/lib/nova/instances/<uuid>/libvirt.xml for libvirt to create the VM. There is a script in vSRX to read this sysinfo and apply it to configuration. This is the automatic initial provistioning without manual configuration.

With this initial configuration, network, SSH and web based management are enabled. To provisition vSRX by NETCONF, two more configurations are required, [ system services netconf ssh ] and [ security zones security-zone trust interfaces ge-0/0/0.0 host-inbound-traffic system-services all ]. They can be configured by SSH.

#2 vSRX and Contrail
vSRX can be launched by Contrail service monitor as a service in service chain.

#3 Example of NAT

##3.1 Overview
![Demo topo](vsrx-nat-figure-1.png)
* A tenant space is allocated in the cloud for each customer.
* An access virtual network is created in each tenant and extened for customer access by gateway.
* A public virtual network is created in admin tenant to provide public access for all customers. It's extended to public by gateway.
* A  management virtual network is created in admin tenant for managing all service instances. It's also extended to physical network by gateway, because the orchestration program runs on physical network.

## 3.2 Preparations
Given a fresh installation, some configurations need to be done to prepare the demo. Some utilities are required from this repository.
https://github.com/tonyliu0592/orch
* As described in 1.3.3, nova needs to be updated on all compute nodes.
* Get code from GitHub.
```
# git clone https://github.com/tonyliu0592/orch.git
# cd orch
# git clone https://github.com/leopoul/ncclient.git
# mv ncclinet ncclient.git
# mv ncclient.git/ncclient ./
# rm -fr ncclient.git
```
Check script `config` to confirm default settings.
* VN "management" and "public" with public address in administration tenant
```
# config --tenant admin add ipam ipam-default
# config --tenant admin add network management --ipam ipam-default --subnet 10.84.53.128/28 --route-target 64512:10284
# config --tenant admin add network public --ipam ipam-default --subnet 10.84.53.48/28 --route-target 64512:10184
```
* Service template
```
# config --tenant admin add service-template vsrx-nat --mode in-network-nat --type firewall --image "vSRX 12.1X46-D20.5" --flavor m1.medium --interface-type management --interface-type left --interface-type right
```
* User tenant "acme"
```
# keystone --os-username admin --os-password <admin password> --os-tenant-name admin --os-auth-url http://127.0.0.1:5000/v2.0/ tenant-create --name acme --enabled true
# keystone --os-username admin --os-password <admin password> --os-tenant-name admin --os-auth-url http://127.0.0.1:5000/v2.0/ user-role-add --user admin --role admin --tenant acme
```
* VN "access"
```
# config --tenant acme add ipam ipam-default
# config --tenant acme add network access --ipam ipam-default --subnet 192.168.1.0/24  --route-target 64512:11000
```
* Configure on the gateway
```
chassis {
    fpc 0 {
        pic 0 {
            tunnel-services;
        }
    }
}
interfaces {
    lt-0/0/0 {
        unit 104 {
            encapsulation frame-relay;
            dlci 184;
            peer-unit 184;
            family inet;
        }
        unit 184 {
            encapsulation frame-relay;
            dlci 184;
            peer-unit 104;
            family inet;
        }
        unit 204 {
            encapsulation frame-relay;
            dlci 100;
            peer-unit 284;
            family inet;
        }
        unit 284 {
            encapsulation frame-relay;
            dlci 100;
            peer-unit 204;
            family inet;
        }
    }
    ge-1/1/0 {
        unit 0 {
            family inet {
                address 10.84.18.253/24;
            }
        }
    }
    lo0 {
        unit 100 {
            family inet {
                address 10.1.1.1/32;
            }
        }
        unit 184 {
            family inet {
                address 1.1.18.4/32;
            }
        }
    }
}
routing-options {
    static {
        route 0.0.0.0/0 next-hop 10.84.18.254;
        route 10.84.53.48/28 next-hop lt-0/0/0.104;
        route 10.84.53.128/28 next-hop lt-0/0/0.204;
    }
    route-distinguisher-id 10.84.18.253;
    autonomous-system 64512;
    dynamic-tunnels {
        dynamic_overlay_tunnels {
            source-address 10.84.18.253;
            gre;
            destination-networks {
                10.84.18.0/24;
            }
        }
    }
}
protocols {
    mpls {
        interface all;
    }
    bgp {
        group contrail {
            type internal;
            local-address 10.84.18.253;
            keep all;
            family inet-vpn {
                unicast;
            }
            neighbor 10.84.18.4;
        }
    }
}
routing-instances {
    access-acme {
        instance-type vrf;
        interface lo0.100;
        vrf-target target:64512:11000;
    }
    management {
        instance-type vrf;
        interface lt-0/0/0.284;
        vrf-target target:64512:10284;
        routing-options {
            static {
                route 0.0.0.0/0 next-hop lt-0/0/0.284;
            }
        }
    }
    public {
        instance-type vrf;
        interface lt-0/0/0.184;
        interface lo0.184;
        vrf-target target:64512:10184;
        routing-options {
            static {
                route 0.0.0.0/0 next-hop lt-0/0/0.184;
            }
        }
    }
}
```
## 3.3 Launch and provisioning service
Once the cloud is prepared, running utility `vsrx` will do the followings.
* Launch vSRX service instance based on pre-defined service template.
* Attach the management, left and right interfaces of vSRX service instance on management, access and public virtual networks respectively.
* Since the service instance is across tenants, service policy doesn't work here. Static interface route needs to be added in access virtual network to steer traffic to vSRX.
* Enable NETCONF service on vSRX.
* Provisioning vSRX for NAT service.
```
vsrx --tenant acme
```
At the end, customer will have NAT service in the cloud and be able to access internet.

In this demo, lo0.100 in VRF access-acme is as the user host, lo0.184 in VRF public is as the internet server. ICMP traffic from user host to internet server shows this demo works as expected.
```
gateway> ping routing-instance access-acme 1.1.18.4    
PING 1.1.18.4 (1.1.18.4): 56 data bytes
64 bytes from 1.1.18.4: icmp_seq=3 ttl=63 time=7.870 ms
64 bytes from 1.1.18.4: icmp_seq=4 ttl=63 time=14.991 ms
```


