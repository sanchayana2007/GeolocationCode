from twisted.internet import protocol, defer

class CompServer(protocol.ServerFactory):
  def __init__(self, app):
    self.components = {}
    self.app = app

