#!/usr/bin/env python3
#
# system_rereg.py
#
# (c) 2018 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting
#
# Version: 2019-04-29
#
# Created by: SUSE Michael Brookhuis
#
# This script will re-register a system against a proxy.
#
# Releases:
# 2019-12-11 M.Brookhuis - Initial release
#
#

"""
This script re-register a system against a proxy
"""

import argparse
from argparse import RawTextHelpFormatter
import xmlrpc.client
import os
import datetime
import smtools

__smt = None


def perform_rereg(server, proxy):
    """
    Apply configuration
    """
    smt.set_hostname(server)
    sid = smt.get_server_id_nofatal()
    print(server)
    try:
        entitlement = smt.client.system.getDetails(smt.session, sid)
    except xmlrpc.client.Fault:
        smt.log_error('Unable to retrieve entitlement data')
        return
    try:
        rereg_key = smt.client.system.obtainReactivationKey(smt.session, sid)
    except xmlrpc.client.Fault:
        smt.log_error("Unable to generate reactivation key for {}.".format(server))
        return
    if entitlement.get('base_entitlement') == "salt_entitled":
        script = "#!/bin/bash \n" \
                 "echo \"master: {}\" > /etc/salt/minion.d/susemanager.conf \n" \
                 "echo \"grains:\" >> /etc/salt/minion.d/susemanager.conf \n" \
                 "echo \"   susemanager:\" >> /etc/salt/minion.d/susemanager.conf \n" \
                 "echo \"      management_key: \"{}\" \">> /etc/salt/minion.d/susemanager.conf \n" \
                 "sleep 10 \n " \
                 "systemctl restart salt-minion \n" \
                 "sleep 15 \n " \
                 "echo \"master: {}\" > /etc/salt/minion.d/susemanager.conf \n" \
                 "echo \"grains:\" >> /etc/salt/minion.d/susemanager.conf \n" \
                 "echo \"   susemanager:\" >> /etc/salt/minion.d/susemanager.conf \n".format(proxy, rereg_key, proxy)
    else:
        script = "#!/bin/bash\nrhnreg_ks --activationkey={} --serverUrl=https://{}/XMLRPC --force\n".format(rereg_key, proxy)
    try:
        smt.client.system.scheduleScriptRun(smt.session, sid, 'root', 'root', 6000, script, datetime.datetime.now())
    except xmlrpc.client.Fault as e:
        smt.log_error("unable to schedule a script run for server. Error: {}".format(e))


def rereg_server(args):
    """
    start update process
    """
    if args.server and args.file:
        smt.fatal_error("please select only 1 option and not both --server and --file")
    if args.server:
        perform_rereg(args.server, args.proxy)
    if args.file:
        if os.path.exists(args.file):
            try:
                sf = open(args.file, "r")
            except:
                smt.fatal_error("Given file {} doesn't exists. aborting".format(args.file))
            for line in sf:
                perform_rereg(line.rstrip(), args.proxy)
        else:
            smt.fatal_error("Given file {} doesn't exists. aborting".format(args.file))


def main():
    """
    Main function
    """
    global smt
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
        Usage:
        system_update.py 
            '''))
    parser.add_argument('-s', '--server', help='name of the server to be re-registered.')
    parser.add_argument('-p', '--proxy',
                        help='name of the proxy server the system should be registered against. Required')
    parser.add_argument('-f', '--file',
                        help='file with list of servers to be re-registered. There should be 1 server per line')
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1, December 11, 2019')
    args = parser.parse_args()
    smt = smtools.SMTools("system_update")
    if not args.proxy:
        smt.log_error("The option --proxy is mandatory. Exiting script")
        smt.exit_program(1)
    else:
        smt.log_info("Start")
        smt.suman_login()
        smt.set_hostname(args.proxy)
        dummy = smt.get_server_id()
    # login to suse manager
    rereg_server(args)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
