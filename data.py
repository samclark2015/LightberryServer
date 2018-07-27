class Store:
    def __init__(self):
        self.Users = {}
        self.Devices = []
        self.Links = []

    def addDevice(self, device):
        self.Devices.append(device)

    def addUser(self, token, user):
        self.Users[token] = user

    def deleteUser(self, token):
        self.Users.pop(token, None)

    def addLink(self, link):
        self.Links.append(link)

    def deleteLink(self, deviceId):
        self.Links = [s for s in self.Links if s[1] != deviceId]

    def getDevice(self, deviceId):
        l = [s for s in self.Devices if s.deviceId == deviceId]
        if len(l) < 1:
            return None
        else:
            return l[0]
