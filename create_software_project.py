#!/usr/bin/env python3
#
# Create_software_project
#
# (c) 2018 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting
#
# Version: 2019-10-20
#
# Created by: SUSE Michael Brookhuis
#
# This script will perform the following actions:
# - Will create a new content lifecycle software project
# - Will create the given environments.
# - Will add the give channels (parent or separate channels)
#
# What is not present on the moment:
# - add a filter
#
# The script will not build or promote the project environments.
# Run sync_state.py --project <project> --environment <environment>
# Start with the first environment and give the system enough time to perform the update.
#
# Releases:
# 2019-04-29 M.Brookhuis - Initial release
#
#

"""
This script will create a new content lifecycle software project
"""

import argparse
from argparse import RawTextHelpFormatter
import xmlrpc.client
import datetime
import smtools

__smt = None


def check_if_projectexists(project):
    """
    check if the given projects exists and return a bool depending on result
    """
    try:
        smt.client.contentmanagement.lookupProject(smt.session, project)
    except xmlrpc.client.Fault:
        return False
    else:
        return True

def add_channels_to_project(project,channels):
    """
    Add the channels to the project
    """
    for channel in channels.split(","):
        smt.log_info("Adding channel '{}' to project '{}'".format(channel, project))
        try:
            smt.client.channel.software.getDetails(smt.session, channel)
        except xmlrpc.client.Fault:
            smt.log_warning("channel '{}' doesn't exist, skipping".format(channel))
        else:
            try:
                smt.client.contentmanagement.attachSource(smt.session, project, "software", channel)
            except xmlrpc.client.Fault:
                smt.log_warning("unable to add channel '{}'. Skipping".format(channel))
            else:
                smt.log_info("completed")


def delete_channels_from_project(project,channels):
    """
    remove the channels from the project
    """
    for channel in channels.split(","):
        smt.log_info("Removing channel '{}' to project '{}'".format(channel, project))
        try:
            smt.client.channel.software.getDetails(smt.session, channel)
        except xmlrpc.client.Fault:
            smt.log_warning("channel '{}' doesn't exist, skipping".format(channel))
        else:
            try:
                smt.client.contentmanagement.detachSource(smt.session, project, "software", channel)
            except xmlrpc.client.Fault:
                smt.log_warning("unable to remove channel '{}'. Skipping".format(channel))
            else:
                smt.log_info("completed")


def create_project(project, environment, basechannel, addchannel, description):
    """
    Create a new software project
    """
    if not description:
        dat = ("%s-%02d-%02d" % (datetime.datetime.now().year, datetime.datetime.now().month,
                                 datetime.datetime.now().day))
        description = "Created on {}".format(dat)
    smt.log_info("Creating project {}".format(project))
    try:
        smt.client.contentmanagement.createProject(smt.session, project, project, description)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to create project {}. Please see logs for more details".format(project))
    pre_env = ""
    for env in environment.split(","):
        smt.log_info("Adding environment {}".format(env))
        env_desc = env + " " + description
        try:
            smt.client.contentmanagement.createEnvironment(smt.session, project, pre_env, env, env, env_desc)
        except xmlrpc.client.Fault:
             smt.fatal_error("Unable to create environment {}. Please see logs for more details".format(env))
        pre_env = env
    all_channels = ""
    if basechannel:
        try:
            smt.client.channel.software.getDetails(smt.session, basechannel)
        except xmlrpc.client.Fault:
            smt.log_warning("The given basechannel {} doesn't exist. Please check. Continue with next step.".format(basechannel))
        else:
            all_channels = basechannel + "," + add_child_channels(basechannel)
    if addchannel:
        if all_channels:
            all_channels = all_channels + "," + addchannel
        else:
            all_channels = addchannel
    if all_channels:
        add_channels_to_project(project,all_channels)

def add_child_channels(basechannel):
    """
    collect the child channels of the given basechannel
    """
    try:
        children = smt.client.channel.software.listChildren(smt.session, basechannel)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to get the child channels from  basechannel {}. Please see logs for more details".format(basechannel))
    channels_to_add = ""
    for child in children:
        if not channels_to_add:
            channels_to_add = child.get('label')
        else:
            channels_to_add += ","
            channels_to_add += child.get('label')
    return channels_to_add



def manage_project(args):
    """
    creating project
    valid options (m manadatory, o optional:
    - create new project: project (m), environment (m), basechannel (o), addchannel (o)
    - add channel to existing project: project (m), addchannel (m)
    - delete channel from existing project: project (m), deletechannel (m)
    """
    project_present = check_if_projectexists(args.project)
    if project_present:
        # project is present so only add and delete channel is valid
        if args.environment or args.basechannel:
            smt.fatal_error("Project {} already exists and the options given can only be used for creation new project. Aborting".format(args.project))
        if args.addchannel:
            add_channels_to_project(args.project, args.addchannel)
        if args.deletechannel:
            delete_channels_from_project(args.project, args.deletechannel)
    else:
        # project is not present so needs to be created.
        create_project(args.project, args.environment, args.basechannel, args.addchannel, args.description)


def main():
    """
    Main function
    """
    global smt
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
        Usage:
        create_software_project.py 
            '''))
    parser.add_argument('-p', '--project', help='name of the project to be created. Required')
    parser.add_argument("-e", "--environment", help="Comma delimited list without spaces of the environments to be created. Required")
    parser.add_argument("-b", '--basechannel', help="The base channel on which the project should be based.")
    parser.add_argument("-a", '--addchannel', help="Comma delimited list without spaces of the channels to be added. Can be used together with --basechannel")
    parser.add_argument("-d", '--deletechannel', help="Comma delimited list without spaces of the channels to be removed from the project.")
    parser.add_argument("-m", '--description', help="Description of the project to be created.")

    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1, October 20, 2019')
    args = parser.parse_args()
    if not args.project:
        smt = smtools.SMTools("system_update")
        smt.log_error("The option --project is mandatory. Exiting script")
        smt.exit_program(1)
    else:
        smt = smtools.SMTools("create_software_project")
    # login to suse manager
    smt.log_info("Start")
    smt.suman_login()
    manage_project(args)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
