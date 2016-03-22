#!/usr/bin/env python

import networkprobe

dave = networkprobe.probe()
dave.readConfig()
print dave.portList
print dave.hostList
print dave.graphiteList
