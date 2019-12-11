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
# This script will clone channels from the give environment.
#
# Releasmt.session:
# 2019-10-239M.Brookhuis - initial release.
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
                smt.log_info('Updating environment {} in the project {}.'.format(args.environment, project.get('label')))
                dat = ("%s-%02d-%02d" % (datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day))
                build_message = "Created on {}".format(dat)
                if number_in_list == 1:
                    project_env = environment_details.get('label')
                    try:
                        smt.client.contentmanagement.buildProject(smt.session, project.get('label'), build_message)
                    except xmlrpc.client.Fault:
                        message = (
                            'Unable to update environment {} in the project {}.'.format(args.environment, project.get('label')))
                        smt.fatal_error(message)
                    check_build_progress(project.get('label'), project_env)
                    break
                else:
                    project_env = environment_details.get('label')
                    try:
                        smt.client.contentmanagement.promoteProject(smt.session, project.get('label'), environment_details.get('previousEnvironmentLabel'))
                    except xmlrpc.client.Fault:
                        message = (
                            'Unable to update environment {} in the project {}.'.format(args.environment, project.get('label')))
                        smt.fatal_error(message)
                    check_build_progress(project.get('label'), project_env)
                    break
            number_in_list += 1




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
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.2, October 17, 2019')
    args = parser.parse_args()
    smt.suman_login()
    if args.environment:
        update_environment(args)
    else:
        smt.fatal_error("Option --environment is not given. Aborting operation")

    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
