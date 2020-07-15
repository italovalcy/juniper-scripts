#!/usr/bin/python2.7
#
# Requirements:
#   pip install junos-eznc jxmlease prettytable
#

from jnpr.junos import Device
from lxml import etree
import jxmlease
import sys, os
import getpass
from prettytable import PrettyTable

if len(sys.argv) > 1:
    host = sys.argv[1]
else:
    sys.stderr.write('USAGE: %s <ROUTER> [USER] [PWD]\n' % (sys.argv[0]))
    sys.exit()

if 'PYEZ_USER' in os.environ:
    user = os.environ['PYEZ_USER']
elif len(sys.argv) > 2:
    user = sys.argv[2]
else:
    sys.stderr.write("Username: ")
    user = raw_input()

if 'PYEZ_PWD' in os.environ:
    pwd = os.environ['PYEZ_PWD']
elif len(sys.argv) > 3:
    pwd = sys.argv[3]
else:
    pwd = getpass.getpass("Password: ")

dev = Device(host=host, user=user, password=pwd, normalize=True)

dev.open()

#rpc = dev.rpc.get_bgp_summary_information()
rpc = dev.rpc.get_bgp_neighbor_information()
rpc_xml = etree.tostring(rpc, pretty_print=True, encoding='unicode')
dev.close()

#print(rpc_xml)

xmlparser = jxmlease.Parser()
result = jxmlease.parse(rpc_xml)

#print(result)

t = PrettyTable(['Peer-IP-Addr', 'Local-IP-Addr', 'AS-Number', 'State', 'RTI', 'Advertised', 'Received', 'Accepted'])
for neighbor in result['bgp-information']['bgp-peer']:
    bgp_rib = neighbor.get('bgp-rib', None)
    (advertised,received,accepted) = (0,0,0)
    if isinstance(bgp_rib, list):
        bgp_rib = bgp_rib[0]
    if isinstance(bgp_rib, dict):
        advertised = str(bgp_rib['advertised-prefix-count'])
        received = str(bgp_rib['received-prefix-count'])
        accepted = str(bgp_rib['accepted-prefix-count'])
    peer_addr = str(neighbor['peer-address']).split('+')[0]
    local_addr = str(neighbor['local-address']).split('+')[0]
    t.add_row([peer_addr, local_addr, str(neighbor['peer-as']),  \
                    str(neighbor['peer-state']), str(neighbor['peer-cfg-rti']), \
                    advertised, received, accepted])

print(t)
