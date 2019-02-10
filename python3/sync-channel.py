#!/usr/bin/env python3
#
# (c) 2017 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support 
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2019-02-10
#
# Created by: SUSE Michael Brookhuis
#
# This script will clone the given channel.
#
# Releases:
# 2017-01-23 M.Brookhuis - initial release.
# 2019-01-14 M.Brookhuis - Added yaml
#                        - Added logging
# 2019-02-10 M.Brookhuis - General update

import os, sys, subprocess, xmlrpc.client, time, datetime, argparse, getpass, yaml, logging, smtools
from argparse import RawTextHelpFormatter

def main():
    # Check if parameters have been given
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-c", "--channel", help="name of the cloned parent channel to be updates")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.1, February 10, 2019')
    args = parser.parse_args()
    
    smtools.set_logging()
 
    if not args.channel:
       smtools.fatal_error("No parent channel to be cloned given. Aborting operation")
    else:
       channel = args.channel
   
    (client,session)=smtools.suman_login()

    smtools.log_info("Updating the following channel with latest patches and packages")
    smtools.log_info("===============================================================")
    smtools.log_info("Updating: %s" % channel) 
    try:
       clone_from_label = client.channel.software.getDetails(session,channel).get('clone_original')
    except xmlrpc.client.Fault as e:
       smtools.fatal.error('Unable to get channel information for %s. Does the channels exist or is it a cloned channel?' % channel)
    smtools.log_info('     Errata .....')
    try:
        erratas = client.channel.software.mergeErrata(session,clone_from_label,channel)
    except xmlrpc.client.Fault as e:
        smtools.fatal_error('Unable to get errata for channel %s' % channel)
    time.sleep(20)
    smtools.log_info('     Packages .....')
    try:
        packages = client.channel.software.mergePackages(session,clone_from_label,channel)
    except xmlrpc.client.Fault as e:
        smtools.fatal_error('Unable to get packages for channel %s' % channel)
    smtools.log_info("FINISHED")
    smtools.close_program()

if __name__ == "__main__":
    SystemExit(main())

