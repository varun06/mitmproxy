
# Copyright (C) 2010  Aldo Cortesi
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import Queue, threading

#begin nocover

class Msg:
    def __init__(self):
        self.q = Queue.Queue()
        self.acked = False

    def ack(self, data=None):
        self.acked = True
        self.q.put(data or self)

    def send(self, masterq):
        self.acked = False
        masterq.put(self)
        return self.q.get()


class Slave(threading.Thread):
    def __init__(self, masterq, server):
        self.masterq, self.server = masterq, server
        self.server.set_mqueue(masterq)
        threading.Thread.__init__(self)

    def run(self):
        self.server.serve_forever()


class Master:
    def __init__(self, server):
        self.server = server
        self._shutdown = False
        self.masterq = None

    def tick(self, q):
        try:
            # Small timeout to prevent pegging the CPU
            msg = q.get(timeout=0.01)
            self.handle(msg)
        except Queue.Empty:
            pass

    def run(self):
        q = Queue.Queue()
        self.masterq = q
        slave = Slave(q, self.server)
        slave.start()
        while not self._shutdown:
            self.tick(q)
        self.shutdown()

    def handle(self, msg):
        c = "handle_" + msg.__class__.__name__.lower()
        m = getattr(self, c, None)
        if m:
            m(msg)
        else:
            msg.ack()

    def shutdown(self):
        if not self._shutdown:
            self._shutdown = True
            self.server.shutdown()


class DumpMaster(Master):
    """
        A simple master that just dumps to screen.
    """
    def __init__(self, server, verbosity):
        self.verbosity = verbosity
        Master.__init__(self, server)

    def run(self):
        try:
            return Master.run(self)
        except KeyboardInterrupt:
            self.shutdown()

    def handle_response(self, msg):
        if 0 < self.verbosity < 3:
            print >> sys.stderr, ">>",
            print >> sys.stderr, msg.request.short()
        if self.verbosity == 1:
            print >> sys.stderr, "<<",
            print >> sys.stderr, msg.short()
        elif self.verbosity == 2:
            print >> sys.stderr, "<<"
            for i in msg.assemble().splitlines():
                print >> sys.stderr, "\t", i
            print >> sys.stderr, "<<"
        elif self.verbosity == 3:
            print >> sys.stderr, ">>"
            for i in msg.request.assemble().splitlines():
                print >> sys.stderr, "\t", i
            print >> sys.stderr, ">>"
            print >> sys.stderr, "<<"
            for i in msg.assemble().splitlines():
                print >> sys.stderr, "\t", i
            print >> sys.stderr, "<<"
        msg.ack()