import networkprobe
dave = networkprobe.probe()
dave.portList = [2000, 3000]
while True:
    dave.connectHost('localhost')
