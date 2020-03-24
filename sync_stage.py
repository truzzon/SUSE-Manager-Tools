#!/usr/bin/env python3
#
# (c) 2019 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2019-10-17
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
# 2019-10-17 M.Brookhuis - Added support for projects and environments
# 2020-03-23 M.Brookhuis - Added backup option

"""
This program will sync the give channel
"""

import argparse
import datetime
import time
import xmlrpc.client
import smtools
from argparse import RawTextHelpFormatter

__smt = None


def create_backup(par):
    """
    Create backup from stage
    """
    dat = ("%s%02d%02d" % (datetime.datetime.now().year, datetime.datetime.now().month, \
                           datetime.datetime.now().day))
    clo = "bu-" + dat + "-" + par
    try:
        smt.client.channel.software.getDetails(smt.session, clo)
    except xmlrpc.client.Fault:
        smt.log_info("Creating backup of current channel. Channel will be called with: {}".format(clo))
    else:
        smt.minor_error('The backupchannel {} already exists. Aborting operation.'.format(clo))
    clo = "bu-" + dat + "-" + par
    clo_str = {'name': clo, 'label': clo, 'summary': clo}
    try:
        smt.client.channel.software.clone(smt.session, par, clo_str, False)
    except xmlrpc.client.Fault:
        smt.minor_error('Unable to create backup. Please check logs')
    child_channels = None
    try:
        child_channels = smt.client.channel.software.listChildren(smt.session, par)
    except xmlrpc.client.Fault:
        smt.fatal_error('Unable to get list child channels for parent channel {}.'.format(par))
    for channels in child_channels:
        clo_str = {}
        new_clo = "bu-" + dat + "-" + channels.get('label')
        clo_str['name'] = clo_str['label'] = clo_str['summary'] = new_clo
        clo_str['parent_label'] = clo
        try:
            smt.client.channel.software.clone(smt.session, channels.get('label'), clo_str, False)
        except xmlrpc.client.Fault:
            smt.fatal_error('Unable to clone child channel {}. Please check logs'.format(new_clo))
    smt.log_info("Creating backup finished")


def clone_channel(channel):
    """
    Clone channel
    """
    total = []
    chan = channel.get('label')
    smt.log_info('Updating %s' % chan)
    try:
        clone_label = smt.client.channel.software.getDetails(smt.session, chan).get('clone_original')
    except xmlrpc.client.Fault:
        smt.minor_error('Unable to get parent data for channel {}. Has this channel been cloned. Skipping'.format(chan))
        return
    smt.log_info('     Errata .....')
    try:
        total = smt.client.channel.software.mergeErrata(smt.session, clone_label, chan)
    except xmlrpc.client.Fault:
        smt.minor_error('Unable to get errata for channel {}.'.format(chan))
    smt.log_info('     Merging {} patches'.format(len(total)))
    time.sleep(120)
    smt.log_info('     Packages .....')
    try:
        total = smt.client.channel.software.mergePackages(smt.session, clone_label, chan)
    except xmlrpc.client.Fault:
        smt.minor_error('Unable to get packages for channel {}.'.format(chan))
    smt.log_info('     Merging {} packages'.format(len(total)))


def update_project(args):
    """
    Updating an environment within a project
    """
    project_details = None
    environment_present = False
    try:
        project_details = smt.client.contentmanagement.listProjectEnvironments(smt.session, args.project)
    except xmlrpc.client.Fault:
        message = ('Unable to get details of given project {}.'.format(args.project))
        message += ' Does the project exist?'
        smt.fatal_error(message)
    number_in_list = 1
    for environment_details in project_details:
        if environment_details.get('label') == args.environment.rstrip():
            environment_present = True
            smt.log_info('Updating environment {} in the project {}.'.format(args.environment, args.project))
            if args.backup:
                channel_start = args.project + "-" + args.environment
                try:
                    all_channels = smt.client.channel.listSoftwareChannels(smt.session)
                except xmlrpc.client.Fault as e:
                    smtools.fatal_error(
                        "Unable to connect SUSE Manager to login to get a list of all software channels")
                all_channels_label = [c.get('label') for c in all_channels]
                for channel in all_channels_label:
                    if channel.startswith(channel_start):
                        try:
                            channel_details = smt.client.channel.software.getDetails(smt.session, channel)
                        except xmlrpc.client.Fault as e:
                            smtools.fatal_error(
                                "Unable to connect SUSE Manager to login to get a list of all software channels")
#                        if not channel_start in channel_details.get('parent_channel_label') and not "bu-" in channel_details.get('parent_channel_label'):
                        if not channel_details.get('parent_channel_label').startswith(channel_start):
                            create_backup(channel)
                            break
            if args.message:
                build_message = args.message
            else:
                dat = ("%s-%02d-%02d" % (datetime.datetime.now().year, datetime.datetime.now().month, \
                                       datetime.datetime.now().day))
                build_message = "Created on {}".format(dat)
            if number_in_list == 1:
                try:
                    smt.client.contentmanagement.buildProject(smt.session, args.project, build_message)
                except xmlrpc.client.Fault:
                    message = (
                        'Unable to update environment {} in the project {}.'.format(args.environment, args.project))
                    smt.fatal_error(message)
                break
            else:
                try:
                    smt.client.contentmanagement.promoteProject(smt.session, args.project, environment_details.get('previousEnvironmentLabel'))
                except xmlrpc.client.Fault:
                    message = (
                        'Unable to update environment {} in the project {}.'.format(args.environment, args.project))
                    smt.fatal_error(message)
                break
        number_in_list += 1
    if not environment_present:
        message = ('Unable to get details of environment {} for project {}.'.format(args.environment, args.project))
        message += ' Does the environment exist?'
        smt.fatal_error(message)


def update_stage(args):
    """
    Updating the stages.
    """
    parent_details = child_channels = None
    try:
        parent_details = smt.client.channel.software.getDetails(smt.session, args.parent)
    except xmlrpc.client.Fault:
        message = ('Unable to get details of parent channel {}.'.format(args.parent))
        message += ' Does the channel exist or is it a cloned channel?'
        smt.fatal_error(message)
    if parent_details.get('parent_channel_label'):
        smt.fatal_error("Given parent channel {}, is not a parent channel.".format(args.parent))
    try:
        child_channels = smt.client.channel.software.listChildren(smt.session, args.parent)
    except xmlrpc.client.Fault:
        smt.fatal_error('Unable to get list child channels. Please check logs')
    smt.log_info("Updating the following channels with latest patches and packages")
    smt.log_info("================================================================")
    if args.backup:
        create_backup(args.parent)
    for channel in child_channels:
        if "pool" not in channel.get('label'):
            clone_channel(channel)
            time.sleep(10)


def main():
    """
    Main section
    """
    global smt
    smt = smtools.SMTools("sync_stage")
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-c", "--channel", help="name of the cloned parent channel to be updates")
    parser.add_argument("-b", "--backup", action="store_true", default=0, \
                        help="creates a backup of the stage first.")
    parser.add_argument("-p", "--project", help="name of the project to be updated. --environment is also mandatory")
    parser.add_argument("-e", "--environment", help="the project to be updated. Mandatory with --project")
    parser.add_argument("-m", "--message", help="Message to be displayed when build is updated")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.3, March 23, 2020')
    args = parser.parse_args()
    smt.suman_login()
    if args.channel:
        update_stage(args)
    elif args.project and args.environment:
        update_project(args)
    else:
        smt.fatal_error("Option --channel or options --project and --environment are not given. Aborting operation")

    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
