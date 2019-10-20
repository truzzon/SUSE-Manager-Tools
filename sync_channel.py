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

__smt = None


def main():
    """
    Main Function
    """
    global smt
    smt = smtools.SMTools("sync_channel")
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
    smt.log_info("Updating: %s" % channel)
    try:
        clone_label = smt.client.channel.software.getDetails(smt.session, channel).get('clone_original')
    except xmlrpc.client.Fault:
        message = ('Unable to get channel information for {}.'.format(channel))
        message += ' Does the channels exist or is it a cloned channel?'
        smt.fatal_error(message)
    smt.log_info('     Errata .....')
    total = None
    try:
        # noinspection PyUnboundLocalVariable
        total = smt.client.channel.software.mergeErrata(smt.session, clone_label, channel)
    except xmlrpc.client.Fault:
        smt.fatal_error('Unable to get errata for channel {}'.format(channel))
    smt.log_info('     Merging {} patches'.format(len(total)))
    time.sleep(120)
    smt.log_info('     Packages .....')
    try:
        total = smt.client.channel.software.mergePackages(smt.session, clone_label, channel)
    except xmlrpc.client.Fault:
        smt.minor_error('Unable to get packages for channel {}.'.format(channel))
    smt.log_info('     Merging {} packages'.format(len(total)))
    smt.log_info("FINISHED")
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
