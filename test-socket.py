import networkprobe
dave = networkprobe.probe()
dave.portList = [2000, 3000]
dave.listen()

