#!/usr/bin/env python3
#
# (c) 2019 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2019-02-10
#
# Created by: SUSE Michael Brookhuis
#
# This script will clone channels from the give parent.
#
# Releasmt.session:
# 2017-01-23 M.Brookhuis - initial release.
# 2019-01-14 M.Brookhuis - Added yaml
#                        - Added logging
# 2019-02-10 M.Brookhuis - General update

"""This program will sync the give channel"""

import argparse
from argparse import RawTextHelpFormatter
import xmlrpc.client
import time
import datetime
import smtools

smt = smtools.SMTools()


def create_backup(par, dat):
    """Create backup from stage"""
    clo = "bu-" + dat + "-" + par
    clo_str = {'name': clo, 'label': clo, 'summary': clo}
    smt.log_info(f"Creating backup of current channel. Channel will be called with: {clo}")
    try:
        smt.client.channel.software.clone(smt.session, par, clo_str, False)
    except xmlrpc.client.Fault:
        smt.fatal_error('Unable to create backup. Please check logs')
    try:
        child_channels = smt.client.channel.software.listChildren(smt.session, par)
    except xmlrpc.client.Fault:
        smt.fatal_error(f'Unable to get list child channels for parent channel {par}.')
    for channels in child_channels:
        clo_str = {}
        new_clo = "bu-" + dat + "-" + channels.get('label')
        clo_str['name'] = clo_str['label'] = clo_str['summary'] = new_clo
        clo_str['parent_label'] = clo
        try:
            smt.client.channel.software.clone(smt.session, channels.get('label'), clo_str, False)
        except xmlrpc.client.Fault:
            smt.fatal_error(f'Unable to clone child channel {new_clo}. Please check logs')
    smt.log_info("Creating backup finished")


def clone_channel(channel):
    """Clone channel"""
    chan = channel.get('label')
    smt.log_info(f'Updating {chan}')
    try:
        clone_label = smt.client.channel.software.getDetails(smt.session, chan).get('clone_original')
    except xmlrpc.client.Fault:
        smt.minor_error(f'Unable to get parent data for channel {chan}. Has this channel been cloned. Skipping')
        return
    smt.log_info('     Errata .....')
    try:
        smt.client.channel.software.mergeErrata(smt.session, clone_label, chan)
    except xmlrpc.client.Fault:
        smt.minor_error(f'Unable to get errata for channel {chan}.')
    time.sleep(10)
    smt.log_info('     Packages .....')
    try:
        smt.client.channel.software.mergePackages(smt.session, clone_label, chan)
    except xmlrpc.client.Fault:
        smt.minor_error(f'Unable to get packages for channel {chan}.')


def main():
    """Main section"""
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-c", "--channel", help="name of the cloned parent channel to be updates")
    parser.add_argument("-b", "--backup", action="store_true", default=0, \
                        help="creates a backup of the stage first.")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.1, February 10, 2019')
    args = parser.parse_args()
    if not args.channel:
        smt.fatal_error("No parent channel to be cloned given. Aborting operation")
    else:
        parent = args.channel
    smt.suman_login()
    try:
        parent_details = smt.client.channel.software.getDetails(smt.session, parent)
    except xmlrpc.client.Fault:
        message = f'Unable to get details of parent channel {parent}.'
        message += ' Does the channel exist or is it a cloned channel?'
        smt.fatal_error(message)
    if parent_details.get('parent_channel_label'):
        smt.fatal_error(f"Given parent channel {parent}, is not a parent channel.")
    try:
        child_channels = smt.client.channel.software.listChildren(smt.session, parent)
    except xmlrpc.client.Fault:
        smt.fatal_error('Unable to get list child channels. Please check logs')
    smt.log_info("Updating the following channels with latest patches and packages")
    smt.log_info("================================================================")
    if args.backup:
        date = ("%s%02d%02d" % (datetime.datetime.now().year, datetime.datetime.now().month, \
                                datetime.datetime.now().day))
        buc = "bu-" + date + "-" + parent
        try:
            smt.client.channel.software.getDetails(smt.session, buc)
        except xmlrpc.client.Fault:
            create_backup(parent, date)
        else:
            smt.fatal_error(f'The backupchannel {buc} already exists. Aborting operation.')
    for channel in child_channels:
        if not "pool" in channel.get('label') or not "iso" in channel.get('label'):
            clone_channel(channel)
            time.sleep(20)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
