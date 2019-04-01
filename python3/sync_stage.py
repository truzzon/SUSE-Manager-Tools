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
import datetime
import smtools

def create_backup(clt, ses, par, dat):
    """Create backup from stage"""
    clo = "bu-"+dat+"-"+par
    clo_str = {}
    clo_str['name'] = clo
    clo_str['label'] = clo
    clo_str['summary'] = clo
    smtools.log_info("Creating backup of current channel. Channel will be called with: %s" % clo)
    try:
        dummy = clt.channel.software.clone(ses, par, clo_str, False)
    except xmlrpc.client.Fault:
        smtools.fatal_error('Unable to create backup. Please check logs')
    try:
        child_channels = clt.channel.software.listChildren(ses, par)
    except xmlrpc.client.Fault:
        smtools.fatal_error('Unable to get list child channels for parent channel %s. \
                            Please check logs' % par)
    for channels in child_channels:
        clo_str = {}
        clo_str['name'] = "bu-"+dat+"-"+channels.get('label')
        clo_str['label'] = "bu-"+dat+"-"+channels.get('label')
        clo_str['summary'] = "bu-"+dat+"-"+channels.get('label')
        clo_str['parent_label'] = clo
        try:
            dummy = clt.channel.software.clone(ses, channels.get('label'), clo_str, False)
        except xmlrpc.client.Fault:
            smtools.fatal_error('Unable to clone child channel %s. Please check logs' \
                % clo+"-"+channels.get('label'))
    smtools.log_info("Creating backup finished")

def clone_channel(client, session, channel):
    """Clone channel"""
    smtools.log_info('Updating %s' % channel.get('label'))
    try:
        clone_label = client.channel.software.getDetails(session, \
                       channel.get('label')).get('clone_original')
    except xmlrpc.client.Fault:
        smtools.minor_error('Unable to get parent data for channel %s. \
                             Has this channel been cloned. Skipping' % channel.get('label'))
        return
    smtools.log_info('     Errata .....')
    try:
        client.channel.software.mergeErrata(session, clone_label, channel.get('label'))
    except xmlrpc.client.Fault:
        smtools.minor_error('Unable to get errata for channel %s. Continue with \
                            next channel' % channel.get('label'))
        return
    time.sleep(10)
    smtools.log_info('     Packages .....')
    try:
        client.channel.software.mergePackages(session, clone_label, channel.get('label'))
    except xmlrpc.client.Fault:
        smtools.minor_error('Unable to get packages for channel %s. Continue with \
                             next channel' % channel.get('label'))

def main():
    """Main section"""
    smtools.set_logging()
    # Check if parameters have been given
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
        smtools.fatal_error("No parent channel to be cloned given. Aborting operation")
    else:
        parent = args.channel
    (client, session) = smtools.suman_login()

    try:
        parent_details = client.channel.software.getDetails(session, parent)
    except xmlrpc.client.Fault:
        smtools.fatal_error('Unable to get details of parent channel %s. \
                            Does the channel exist or is it a cloned channel?' % parent)
    if parent_details.get('parent_channel_label'):
        smtools.fatal_error("Given parent channel %s, is not a parent channel. \
                           Aborting operation" % parent)
    try:
        child_channels = client.channel.software.listChildren(session, parent)
    except xmlrpc.client.Fault:
        smtools.fatal_error('Unable to get list child channels. Please check logs')
    smtools.log_info("Updating the following channels with latest patches and packages")
    smtools.log_info("================================================================")
    if args.backup:
        date = ("%s%02d%02d" % (datetime.datetime.now().year, datetime.datetime.now().month, \
            datetime.datetime.now().day))
        buc = "bu-"+date+"-"+parent
        try:
            client.channel.software.getDetails(session, buc)
        except xmlrpc.client.Fault:
            create_backup(client, session, parent, date)
        else:
            smtools.fatal_error('The backupchannel %s already exists. Aborting operation.' % buc)
    for channel in child_channels:
        if not "pool" in channel.get('label') or "iso" in channel.get('label'):
            clone_channel(client, session, channel)
            time.sleep(20)
    smtools.close_program()

if __name__ == "__main__":
    SystemExit(main())
