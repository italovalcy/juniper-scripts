import re, sys
import argparse

parser = argparse.ArgumentParser(description='Juniper show-route parser')
parser.add_argument('--prefix', default='', help='Insert a text on the prefix')
parser.add_argument('--suffix', default='', help='Insert a text on the suffix')
parser.add_argument('--output_format', default='csv',
                    choices=['gobgp', 'exabgp', 'csv'],
                    help='Output format (default: csv)')
parser.add_argument('--file', help='File with the show-route dump', 
                    required=True)
args = parser.parse_args()
param = vars(args)

# BGP ORIGIN Types (RFC4271)
ORIGIN_T = {
    'I':'IGP',
    'E':'EGP',
    '?':'INCOMPLETE',
}

JNPR_IGNORE_EXT_COMM = ['rt-import', 'src-as', 'rte-type','domain-id', 'iana', 
    'route-type-vendor', 'router-id-vendor', 'unknown', '30c', '603', '43',
]

#param = {
# 'prefix' : '',
# 'prefix' : 'global rib add -a ipv4 ',
# 'prefix' : 'neighbor 1.2.3.4 announce route ',
# 'suffix' : '',
# 'output_format': 'gobgp',
# 'output_format': 'exabgp',
# 'output_format': 'csv',
#}

def fmt_next_hop(value):
    if param['output_format'] == 'exabgp':
        return ' next-hop %s' % (value)
    elif param['output_format'] == 'gobgp':
        return ' nexthop %s' % (value)
    else:
        return ',next-hop=%s' % (value)

def fmt_med(value):
    if param['output_format'] == 'exabgp':
        return ' med %s' % (value)
    elif param['output_format'] == 'gobgp':
        return ' med %s' % (value)
    else:
        return ',med=%s' % (value)

def fmt_as_path(as_path, origin):
    as_path = as_path.rstrip()
    if param['output_format'] == 'exabgp':
        origin = ORIGIN_T[origin]
        as_path = as_path.replace('{', '(').replace('}', ')')
        return ' as-path [%s] origin %s' % (as_path, origin)
    elif param['output_format'] == 'gobgp':
        origin = ORIGIN_T[origin].lower()
        return ' aspath "%s" origin %s' % (as_path, origin)
    else:
        as_path = as_path.replace(' ', ';')
        return ',as-path=%s,origin=%s' % (as_path,origin)

def fmt_community(value, name='community'):
    if not value:
        return ''
    if param['output_format'] == 'exabgp':
        return ' %s [%s]' % (name, ' '.join(value))
    elif param['output_format'] == 'gobgp':
        return ' %s "%s"' % (name, ','.join(value))
    else:
        return ',%s=%s' % (name, ';'.join(value))

def fmt_aggregator(value):
    if param['output_format'] == 'exabgp':
        value = value.replace(' ',':')
        return ' aggregator (%s)' % (value)
    elif param['output_format'] == 'gobgp':
        value = value.replace(' ',':')
        return ' aggregator "%s"' % (value)
    else:
        value = value.replace(' ',':')
        return ',aggregator=%s' % (value)

def fmt_local_pref(value):
    if param['output_format'] == 'exabgp':
        return ' local-preference %s' % (value)
    elif param['output_format'] == 'gobgp':
        return ' local-pref %s' % (value)
    else:
        return ',local-pref=%s' % (value)

def get_bgp_attr(key, value):
    if key == 'Connector ID' or (key == 'AS path' and not value) or \
            key.startswith('AS2 PA') or key.startswith('AS4 PA'):
        return ''
    elif key == 'Nexthop' and value:
        return fmt_next_hop(value)
    elif key == 'MED' and value:
        return fmt_med(value)
    elif (key == 'AS path' or key.startswith("Merged")) and value:
        m = re.search('([0-9{}]+ )*([IE?])', value)
        if m is None:
            sys.stderr.write("==>>> Invalid AS-PATH %s\n" % (value))
            return ''
        return fmt_as_path(m.group(1) or '', m.group(2))
    elif key == 'Communities' and value:
        community = []
        extended = []
        large = []
        # Following juniper documentation to split the communities into
        # normal, large (RFC 8092) and extended (RFC 4360) communities
        # https://www.juniper.net/documentation/en_US/junos/topics/concept/policy-bgp-communities-extended-communities-match-conditions-overview.html
        for c in value.split(' '):
            groups = c.split(':')
            if len(groups) == 2 or c in ['no-export']:
                community.append(c)
            elif groups[0] in ['target', 'origin','bandwidth']:
                extended.append(c)
            elif groups[0] == 'large':
                large.append(':'.join(groups[1:]))
            elif groups[0] in JNPR_IGNORE_EXT_COMM:
                continue
            else:
                sys.stderr.write("==>>> Invalid Community %s\n" % (c))
        return fmt_community(community) \
                + fmt_community(extended, 'extended-community') \
                + fmt_community(large, 'large-community')
    elif key == 'Aggregator' and value:
        return fmt_aggregator(value)
    elif key == 'Localpref' and value:
        return fmt_local_pref(value)
    else:
        sys.stderr.write("==>>> Invalid attribute=%s value=%s\n" % (key,value))
    return ''

f = open(param['file'], "r")
data = f.read()
for r in re.split('\r?\n\r?\n', data):
    nlri = ''
    attrs = ''
    for l in re.split('\r?\n', r):
        if not l.strip():
            continue
        elif re.search('[^:]+: \d+ destinations, \d+ routes \(\d+ active, \d+ holddown, \d+ hidden\)', l):
            continue
        elif re.search('^\s+(Unrecognized Attributes|Attr flags \w+ code \w+|Hidden reason|BGP group .* type .*|Accepted)', l):
            continue
        m = re.search('[* ] ([\w.:/]+) \(\d+ entr[iy]e?s?, \d+ announced\)', l)
        if m is not None:
            nlri = m.group(1)
            continue
        m = re.search('^\s+(Nexthop|MED|AS path|Communities|Aggregator|Connector ID|AS2 PA\[\d+\]|AS4 PA\[\d+\]|Merged\[\d+\]|Localpref):?(.*)', l)
        if m is not None:
            attrs += get_bgp_attr(m.group(1), m.group(2).strip())
            continue
        sys.stderr.write("==>>> unknown format %s\n" % (l))
    print '%s%s%s%s' % \
        (param['prefix'], nlri, attrs, param['suffix'])
