#!/usr/bin/env python
#
# Copyright (c) 2015 University of Cambridge
# Copyright (c) 2015 Modified by Neelakandan Manihatty Bojan, Georgina Kalogeridou, Noa Zilberman
# All rights reserved.
#
# This software was developed by the University of Cambridge Computer Laboratory 
# under EPSRC INTERNET Project EP/H040536/1, National Science Foundation under Grant No. CNS-0855268,
# and Defense Advanced Research Projects Agency (DARPA) and Air Force Research Laboratory (AFRL), 
# under contract FA8750-11-C-0249.
#
# @NETFPGA_LICENSE_HEADER_START@
#
# Licensed to NetFPGA Open Systems C.I.C. (NetFPGA) under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  NetFPGA licenses this
# file to you under the NetFPGA Hardware-Software License, Version 1.0 (the
# "License"); you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at:
#
#   http://www.netfpga-cic.org
#
# Unless required by applicable law or agreed to in writing, Work distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations under the License.
#
# @NETFPGA_LICENSE_HEADER_END@
#


import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from NFTest import *
import sys
import os
from scapy.layers.all import Ether, ARP, Raw
from reg_defines_arp_crypto import *
#from crypto_lib import *
from struct import pack, unpack

#conn = ('../connections/crossover', [])
#nftest_init(sim_loop = ['nf0', 'nf1', 'nf2', 'nf3'], hw_config = [conn])
phy2loop0 = ('../connections/conn', [])
nftest_init(sim_loop = [], hw_config = [phy2loop0])

nftest_start()

nftest_regwrite(SUME_OUTPUT_PORT_LOOKUP_0_RESET(), 0x111)
nftest_barrier()
nftest_regwrite(SUME_OUTPUT_PORT_LOOKUP_0_RESET(), 0x000)
nftest_barrier()

#nftest_barrier()


# set parameters
SA = "aa:bb:cc:dd:ee:ff"
DA = "00:ca:fe:00:00:02"
TTL = 64
DIP = "192.168.1.1"
SIP = "192.168.0.1"
nextHopMAC = "dd:55:dd:66:dd:77"
HWDST = "00:00:00:00:00:00"
    
# define the data we want to use 
size = (1500 - 64) * 1 + 150
data_size = pack("<L", size)
data = ''.join(['a' for i in xrange(size)])
magic = pack('<L', 0xa5a5a5a5)

mres = []

nftest_regwrite(SUME_ARP_CRYPTO_0_DATA0(), size)
if isHW():
    mres.append(nftest_regread_expect(SUME_ARP_CRYPTO_0_DATA0(), size))
else:
    nftest_regread_expect(SUME_ARP_CRYPTO_0_DATA0(), size) 

#nftest_barrier()

num_broadcast = 0x14

## send data over dma
pkts = []
tmp_size = size
for i in xrange(size / (1500 - 64) + 1):
    DA = "00:ca:fe:00:00:00"
    data_sent = min(1500 - 64, tmp_size)
    pkt = make_IP_pkt(src_MAC="aa:bb:cc:dd:ee:ff", dst_MAC="00:ca:fe:00:00:01",
                      src_IP="192.168.0.1", dst_IP="192.168.1.1", pkt_len=data_sent)
    pkt.payload.payload.load = '\x00' * (64 - 34) + data[ (1500 - 64) * i : (1500 - 64) * i + data_sent]
    pkt.tuser_sport = 0xff # TODO: fix it
    tmp_size -= data_sent
    pkt.time = (i*(1e-8))
    if isHW():
        nftest_send_dma('nf' + '1', pkt)
        nftest_expect_dma('nf' + '1', pkt)
    else:
        nftest_send_phy('nf0', pkt) 
        nftest_expect_dma('nf1', pkt)

pkts = []
expected_pkts = []
for i in range(size / (1500 - 64) + 1):
    DA = "ff:ff:ff:ff:ff:ff"
    pkt = Ether(src = SA, dst = DA) / ARP(op = 'who-has', psrc = SIP, pdst = DIP, hwsrc = SA, hwdst = HWDST)

    pkt.tuser_sport = 1
    pkts.append(pkt)
    offset = pack(">L", (1500 - 64) * i)
    
    expected_pkts.append(pkt / Raw(load = magic + offset + data_size + '\x00' * 20 + data[(1500 - 64) * i : (1500 - 64) * (i + 1)]))

    for i in range(size / (1500 - 64) + 1):
        for pkt in pkts:
            pkt.time = i*(1e-8) + (1e-6)

    if isHW():
        nftest_expect_phy('nf1', pkt / Raw(load = magic + offset + data_size + '\x00' * 20 + data[(1500 - 64) * i : (1500 - 64) * (i + 1)]))
        nftest_send_phy('nf0', pkt)
    
if not isHW():
    nftest_send_phy('nf0', pkts)
    nftest_expect_phy('nf1', expected_pkts)
    nftest_expect_phy('nf2', expected_pkts)
    nftest_expect_phy('nf3', expected_pkts)

#nftest_barrier()

if isHW():
    # Now we expect to see the lut_hit and lut_miss registers incremented and we
    # verify this by doing a  reg
    #rres3= nftest_regread_expect(SUME_OUTPUT_PORT_LOOKUP_0_LUTMISS(), num_broadcast)
    #rres4= nftest_regread_expect(SUME_OUTPUT_PORT_LOOKUP_0_LUTHIT(), num_normal)
    # List containing the return values of the reg_reads
    #mres.extend([rres3, rres4])
    pass
else:
 #   nftest_regread_expect(SUME_CRYPTO_KEY_0(), key1) #encryption key
    #nftest_regread_expect(SUME_OUTPUT_PORT_LOOKUP_0_LUTMISS(), num_broadcast) # lut_miss
    #nftest_regread_expect(SUME_OUTPUT_PORT_LOOKUP_0_LUTHIT(), num_normal) # lut_hit
    mres=[]

nftest_finish(mres)