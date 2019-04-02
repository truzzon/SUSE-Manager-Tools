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

"""This program will sync the give channel"""

import argparse
from argparse import RawTextHelpFormatter
import xmlrpc.client
import time
import smtools

smt = smtools.SMTools()


def main():
    """Main Function"""
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-c", "--channel", help="name of the cloned parent channel to be updates")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.1, February 10, 2019')
    args = parser.parse_args()
    if not args.channel:
        smt.fatal_error("No parent channel to be cloned given. Aborting operation")
    else:
        channel = args.channel
    smt.suman_login()
    smt.log_info("Updating the following channel with latest patches and packages")
    smt.log_info("===============================================================")
    # noinspection PyUnboundLocalVariable
    smt.log_info(f"Updating: {channel}")
    try:
        clone_label = smt.client.channel.software.getDetails(smt.session, channel).get('clone_original')
    except xmlrpc.client.Fault:
        message = f'Unable to get channel information for {channel}. Does the channels exist or is it a cloned channel?'
        smt.fatal_error(message)
    smt.log_info('     Errata .....')
    try:
        # noinspection PyUnboundLocalVariable
        smt.client.channel.software.mergeErrata(smt.session, clone_label, channel)
    except xmlrpc.client.Fault:
        smt.fatal_error(f'Unable to get errata for channel {channel}')
    time.sleep(20)
    smt.log_info('     Packages .....')
    try:
        smt.client.channel.software.mergePackages(smt.session, clone_label, channel)
    except xmlrpc.client.Fault:
        smt.fatal_error(f'Unable to get packages for channel {channel}')
    smt.log_info("FINISHED")
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
