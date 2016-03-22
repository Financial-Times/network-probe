import networkprobe
dave = networkprobe.probe()
dave.portList = [100,2000, 3000]
dave.connectHost('localhost')
