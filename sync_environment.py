#!/usr/bin/env python3
#
# (c) 2019 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2020-03-23
#
# Created by: SUSE Michael Brookhuis
#
# This script will clone channels from the give environment.
#
# Release:
# 2019-10-23 M.Brookhuis - initial release.
# 2020-02-03 M.Brookhuis - Bug fix: there should be no fatal error.
# 2020-03-21 M.Brookhuis - RC 1 if there has been an error
# 2020-03-23 M.Brookhuis - Added backup option
#

"""
This program will sync the give environment in all projects
"""

import argparse
import datetime
import time
import xmlrpc.client
from argparse import RawTextHelpFormatter

import smtools

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


def check_build_progress(project_name, project_env):
    smt.log_info("In progress")
    try:
        progress = smt.client.contentmanagement.lookupEnvironment(smt.session, project_name, project_env)
    except xmlrpc.client.Fault:
        smt.log_error("Unable to get status for project {} environment {}".format(project_name, project_env))
    while progress.get('status') == "building":
        time.sleep(60)
        smt.log_info("In progress")
        try:
            progress = smt.client.contentmanagement.lookupEnvironment(smt.session, project_name, project_env)
        except xmlrpc.client.Fault:
            smt.log_error("Unable to get status for project {} environment {}".format(project_name, project_env))


def update_environment(args):
    """
    Updating an environment within a project
    """
    project_list = None
    environment_found = False
    try:
        project_list = smt.client.contentmanagement.listProjects(smt.session)
    except xmlrpc.client.Fault:
        message = ('Unable to get list of projects. Problem with SUSE Manager')
        smt.fatal_error(message)

    for project in project_list:
        project_details = None
        try:
            project_details = smt.client.contentmanagement.listProjectEnvironments(smt.session, project.get('label'))
        except xmlrpc.client.Fault:
            message = ('Unable to get details of given project {}.'.format(project.get('label')))
            smt.log_error(message)
            break
        number_in_list = 1
        for environment_details in project_details:
            if environment_details.get('label') == args.environment:
                environment_found = True
                smt.log_info('Updating environment {} in the project {}.'.format(args.environment, project.get('label')))
                if args.backup:
                    channel_start = project.get('label') + "-" + args.environment
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
                dat = ("%s-%02d-%02d" % (datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day))
                build_message = "Created on {}".format(dat)
                if number_in_list == 1:
                    project_env = environment_details.get('label')
                    try:
                        smt.client.contentmanagement.buildProject(smt.session, project.get('label'), build_message)
                    except xmlrpc.client.Fault:
                        message = (
                            'Unable to update environment {} in the project {}.'.format(args.environment, project.get('label')))
                        smt.minor_error(message)
                    check_build_progress(project.get('label'), project_env)
                    break
                else:
                    project_env = environment_details.get('label')
                    try:
                        smt.client.contentmanagement.promoteProject(smt.session, project.get('label'), environment_details.get('previousEnvironmentLabel'))
                    except xmlrpc.client.Fault:
                        message = (
                            'Unable to update environment {} in the project {}.'.format(args.environment, project.get('label')))
                        smt.minor_error(message)
                    check_build_progress(project.get('label'), project_env)
                    break
            number_in_list += 1
    if not environment_found:
        smt.minor_error("The given environment {} does not exist".format(args.environment))


def main():
    """
    Main section
    """
    global smt
    smt = smtools.SMTools("sync_environment")
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         sync_environment.py
    
               '''))
    parser.add_argument("-e", "--environment", help="the project to be updated. Mandatory with --project")
    parser.add_argument("-b", "--backup", action="store_true", default=0, help="creates a backup of the stage first.")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.3, March 23, 2020')
    args = parser.parse_args()
    smt.suman_login()
    if args.environment:
        update_environment(args)
    else:
        smt.fatal_error("Option --environment is not given. Aborting operation")

    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
