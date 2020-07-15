Juniper routing dump parser
---------------------------

The goal of this script is to parser the Juniper 'show routes' dump to the format of ExaBGP and GoBGP.

If you can use MRT dumps (https://bgp.guru/2019/01/30/mrt-dumps-with-gobgp/), it is much more recommended. If you cannot, this script may be helpful.

The first step is to generate the dump from the Juniper router::

    show route receive-protocol bgp <NEIGHBOR> | save /var/tmp/sh-route-dump-XYZ.cfg

After that, you can use the script to generate the dump in GoBGP, ExaBGP or CSV format::

    python jnpr-routes-parser.py --file show-route-192.168.1.1-inet-rcv.txt --prefix 'global rib add -a ipv4 ' --output_format gobgp > gobgp-input.txt
