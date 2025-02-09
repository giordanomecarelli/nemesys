# tester.py
# -*- coding: utf8 -*-

# Copyright (c) 2010-2016 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
import socket
from datetime import datetime
from optparse import OptionParser

from common import iptools, utils
from common import nem_exceptions
from common import ntptime
from common import ping
from common.host import Host
from common.nem_exceptions import MeasurementException
from common.proof import Proof
from common.testerhttpdown import HttpTesterDown
from common.testerhttpup import HttpTesterUp

HTTP_BUFF = 8 * 1024
BW_3M = 3000000
BW_100M = 100000000
BW_500M = 500000000
logger = logging.getLogger(__name__)


class Tester(object):
    def __init__(self, dev, host, timeout=11):
        self._host = host
        self._timeout = timeout
        socket.setdefaulttimeout(self._timeout)
        self._testerhttpup = HttpTesterUp(dev)
        self._testerhttpdown = HttpTesterDown(dev)

    def testhttpdown(self, callback_update_speed=None, bw=BW_100M):
        url = "http://%s/file.rnd" % self._host.ip
        if bw >= BW_500M and utils.is_darwin():
            num_sessions = 1
            buffer_size = 2 * 8192
        else:
            num_sessions = 7
            buffer_size = 8192
        return self._testerhttpdown.test(url, callback_update_speed, num_sessions=num_sessions, buffer_size=buffer_size)

    def testhttpup(self, callback_update_speed=None, bw=BW_100M):
        url = "http://%s:8080/file.rnd" % self._host.ip
        buffer_size = 8192
        if bw < BW_3M:
            num_sessions = 1
            tcp_window_size = 22 * 1024
        elif bw == BW_3M:
            num_sessions = 1
            tcp_window_size = 65 * 1024
        elif bw <= BW_100M:
            num_sessions = 6
            tcp_window_size = 65 * 1024
        else:
            num_sessions = 1
            if utils.is_windows():
                tcp_window_size = 256 * 1024
            else:
                tcp_window_size = -1
                if utils.is_darwin():
                    buffer_size = 3 * 8129
        return self._testerhttpup.test(url, callback_update_speed, num_sessions=num_sessions,
                                       tcp_window_size=tcp_window_size, buffer_size=buffer_size)

    def testping(self, timeout=10):
        # si utilizza funzione ping.py
        start = datetime.fromtimestamp(ntptime.timestamp())
        try:
            rtt = ping.do_one(self._host.ip, timeout)
        except Exception as e:
            if "Timeout" in str(e):
                rtt = None
            else:
                raise MeasurementException("Impossibile effettuare il ping: %s" % e, nem_exceptions.PING_ERROR)

        if rtt is None:
            raise MeasurementException("Ping timeout", nem_exceptions.PING_TIMEOUT)

        return Proof(test_type='ping', start_time=start, duration=rtt * 1000, bytes_nem=0)


def main():
    import time
    # Aggancio opzioni da linea di comando

    parser = OptionParser(version="0.10.1.$Rev$",
                          description="A simple bandwidth tester able to perform HTTP upload/download and PING tests.")
    parser.add_option("-t", "--type", choices=('down', 'up', 'ping'),
                      dest="testtype", default="down", type="choice",
                      help="Choose the type of test to perform: down (default), up, ping")
    parser.add_option("-b", "--bandwidth", dest="bandwidth", default="100M", type="string",
                      help="The expected bandwith to measure, used in upload tests, e.g. 512k, 2M")
    parser.add_option("-n", "--num-tests", dest="num_tests", default="1", type="int",
                      help="Number of tests to perform")
    parser.add_option("-H", "--host", dest="host", default="193.104.137.133",
                      help="An ipaddress or FQDN of server host")

    (options, _) = parser.parse_args()
    try:
        dev = iptools.get_dev()
    except Exception:
        try:
            dev = iptools.get_dev(host=options.host, port=80)
        except Exception:
            print("Impossibile ottenere indirizzo e device, verificare la connessione all'host")
            import sys
            sys.exit(2)
    t = Tester(dev, Host(options.host), timeout=10)
    if options.bandwidth.endswith("M"):
        bw = int(options.bandwidth[:-1]) * 1000000
    elif options.bandwidth.endswith("k"):
        bw = int(options.bandwidth[:-1]) * 1000
    else:
        print("Please specify bandwith in the form of 2M or 512k")
        return

    print("===============================================")
    print(('Testing: %s' % options.host))
    for i in range(1, options.num_tests + 1):
        print("-----------------------------------------------")
        if i != 1:
            print("Sleeping....")
            print("-----------------------------------------------")
            time.sleep(10)
        print(('test %d %s' % (i, options.testtype)))
        if options.testtype == 'up':
            try:
                res = t.testhttpup(None, bw=bw)
                printout_http(res)
            except MeasurementException as e:
                print(("Error: [%d] %s" % (e.errorcode, str(e))))
        elif options.testtype == 'ping':
            try:
                res = t.testping()
                print(("Ping: %.2f milliseconds" % res.duration))
            except Exception as e:
                print(("Error: [%d] %s" % (e.errorcode, str(e))))
        else:
            try:
                res = t.testhttpdown(bw=bw)
                printout_http(res)
            except MeasurementException as e:
                print(("Error: %s" % str(e)))
    print("===============================================")


def printout_http(res):
    print(("Medium speed: %d kbps" % (int(res.bytes_tot * 8 / float(res.duration)))))
    print(("Spurious traffic: %.2f%%" % (res.spurious * 100.0)))


if __name__ == '__main__':
    from nemesys import log_conf

    log_conf.init_log()
    main()