#
# grottconf  process command parameter and settings file
# Updated: 2022-08-26
# Version 2.7.6

import configparser
import sys
import argparse
import os
import json
import io
import ipaddress
from os import walk
from mqttdata import format_multi_line, str2bool


class Conf:

    def __init__(self, vrm):
        self.verrel = vrm

        # Set default variables
        self.verbose = False
        self.trace = False
        self.cfgfile = "mqttmitm.ini"
        self.gtime = "auto"  # time used =  auto: use record time or if not valid server time, alternative server: use always server time
        # enable / disable sending historical data from buffer
        self.sendbuf = True
        self.valueoffset = 6
        self.mode = "proxy"
        self.mqttport = 8883
        self.mqttip = "default"  # connect to server IP adress
        self.outfile = "sys.stdout"
        # set timezone (at this moment only used for influxdb)
        self.tmzone = "local"

        # Growatt server default
        self.alip = "k8s.aqualisa.like.st"
        self.alport = 8883

        # Set parm's
        # prio: 1.Command line parms, 2.env. variables, 3.config file 4.program default
        # process command settings that set processing values (verbose, trace, output, config, nomqtt)
        self.parserinit()

        # Process config file
        self.procconf()

        # Process environmental variable
        self.procenv()

        # Process environmental variable to override config and environmental settings
        self.parserset()

        # Prepare invert settings
        self.SN = "".join(['{:02x}'.format(ord(x)) for x in self.inverterid])
        self.offset = 6
        if self.compat:
            # set offset for older inverter types or after record change by Growatt
            self.offset = int(self.valueoffset)

    def parserinit(self):
        # Process commandline parameters init (read args, process c,v,o settings)
        parser = argparse.ArgumentParser(prog='grott')
        parser.add_argument('-v', '--verbose',
                            help="set verbose", action='store_true')
        parser.add_argument('--version', action='version', version=self.verrel)
        parser.add_argument(
            '-c', help="set config file if not specified config file is mqttmitm.ini", metavar="[config file]")
        parser.add_argument(
            '-o', help="set output file, if not specified output is stdout", metavar="[output file]")
        parser.add_argument(
            '-m', help="set mode (sniff or proxy), if not specified mode is sniff", metavar="[mode]")

        args, unknown = parser.parse_known_args()

        if (args.c != None):
            self.cfgfile = args.c
        if (args.o != None):
            sys.stdout = io.TextIOWrapper(
                open(args.o, 'wb', 0), write_through=True)
        self.verbose = args.verbose

    def parserset(self):
        # Correct Bool if changed to string during parsing process
        # if self.verbose == True or self.verbose == "True" : self.verbose = True
        # else : self.verbose = False
        self.verbose = str2bool(self.verbose)

    def procconf(self):
        print("\nGrott process configuration file")
        config = configparser.ConfigParser()
        config.read(self.cfgfile)
        if config.has_option("Generic", "ip"):
            self.grottip = config.get("Generic", "ip")
        if config.has_option("Generic", "port"):
            self.grottport = config.getint("Generic", "port")
        if config.has_option("Upstream", "ip"):
            self.alip = config.get("Upstream", "ip")
        if config.has_option("Upstream", "port"):
            self.alport = config.getint("Upstream", "port")
