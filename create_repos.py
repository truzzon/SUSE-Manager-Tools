#!/usr/bin/env python3
#
# create_repos.py
#
# (c) 2017 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2020-01-30
#
# Created by: SUSE Michael Brookhuis
#
# This script will clone the given channel.
#
# Releases:
# 2020-01-30 M.Brookhuis - initial release.
#
"""This program will create the needed channels and repositories"""

import argparse
from argparse import RawTextHelpFormatter
import os
import xmlrpc.client
import smtools

__smt = None


def check_present(wanted, item_list):
    """
    check if item is present in the list
    """
    for item in item_list:
        if item.get('description') == wanted:
            return True
    return False


def do_repo_config(repo_config, sync):
    """
    Evaluate the repo config
    """
    all_crypto_keys = None
    try:
        all_crypto_keys = smt.client.kickstart.keys.listAllKeys(smt.session)
    except  xmlrpc.client.Fault:
        smt.minor_error("Unable to get a list of keys.")
    for repo, repo_info in repo_config['repository'].items():
        # check if key, cert, ca exist
        if repo_info['key']:
            if not check_present(repo_info['key'], all_crypto_keys):
                smt.minor_error(
                    "The given key {} for repository {} doesn't skip. Continue with next item.".format(repo_info['key'],
                                                                                                       repo))
                continue
        if repo_info['ca']:
            if not check_present(repo_info['ca'], all_crypto_keys):
                smt.minor_error(
                    "The given ca {} for repository {} doesn't skip. Continue with next item.".format(repo_info['ca'],
                                                                                                      repo))
                continue
        if repo_info['cert']:
            if not check_present(repo_info['cert'], all_crypto_keys):
                smt.minor_error("The given key {} for repository {} doesn't skip. Continue with next item.".format(
                    repo_info['cert'], repo))
                continue
        # check if repository exist
        try:
            smt.client.channel.software.getRepoDetails(smt.session, repo)
        except xmlrpc.client.Fault:
            smt.log_info("Repository {} will be created if channel is not present".format(repo))
        else:
            smt.minor_error("The repository {} already exists. Skipping to next".format(repo))
            continue
        # check if channel exist
        try:
            smt.client.channel.software.getDetails(smt.session, repo)
        except xmlrpc.client.Fault:
            smt.log_info("Channel {} will be created if parent channel is present".format(repo))
        else:
            smt.minor_error("The channel {} already exists. Skipping to next".format(repo))
            continue
        # check if parent exist
        try:
            smt.client.channel.software.getDetails(smt.session, repo_info['parent'])
        except xmlrpc.client.Fault:
            smt.minor_error(
                "Parent channel not present. No repository {} or channel {} will be created".format(repo, repo))
            continue
        # create repo
        if repo_info['key']:
            try:
                smt.client.channel.software.createRepo(smt.session, repo, repo_info['type'], repo_info['url'],
                                                       repo_info['ca'], repo_info['cert'], repo_info['key'])
            except xmlrpc.client.Fault:
                smt.log_error("Something went wrong when creating repository {}".format(repo))
                continue
        else:
            try:
                smt.client.channel.software.createRepo(smt.session, repo, repo_info['type'], repo_info['url'])
            except xmlrpc.client.Fault:
                smt.log_error("Something went wrong when creating repository {}".format(repo))
                continue
        # create channel
        try:
            smt.client.channel.software.create(smt.session, repo, repo, repo, "channel-x86_64", repo_info['parent'])
        except xmlrpc.client.Fault:
            smt.log_error("Something went wrong when creating channel {}".format(repo))
            continue
        # add channel to repo
        try:
            smt.client.channel.software.associateRepo(smt.session, repo, repo)
        except xmlrpc.client.Fault:
            smt.log_error("Unable to associate repository {} with channel {}".format(repo, repo))
        try:
            smt.client.channel.software.syncRepo(smt.session, repo, repo_info['schedule'])
        except xmlrpc.client.Fault:
            smt.log_error("Unable to set schedule \'{}\' for repository {}".format(repo_info['schedule'], repo))
            continue
        # if sync == True start sync
        if sync:
            try:
                smt.client.channel.software.syncRepo(smt.session, repo)
            except xmlrpc.client.Fault:
                smt.log_error("Unable to sync repository {}".format(repo))
            else:
                smt.log_info("Sync of repository {} started.".format(repo))
        smt.log_info("Repositoriy {} and Channel {} created".format(repo, repo))
        smt.log_info(" ")


def main():
    """
    Main Function
    """
    global smt
    smt = smtools.SMTools("create_repos")
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-r", "--repos", help="file containing the reposotiries to be created")
    parser.add_argument("-s", '--sync', action="store_true", default=0,
                        help="Synchronizechannel after creation. Default off")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.1, January 30, 2020')
    args = parser.parse_args()
    if not args.repos:
        smt.fatal_error("No file with repositories is given. Aborting operation")
    else:
        if not os.path.exists(args.repos):
            smt.fatal_error("The given file {} doesn't exist.".format(args.repos))
        else:
            with open(args.repos) as repo_cfg:
                repo_config = smtools.load_yaml(repo_cfg)
    smt.suman_login()
    do_repo_config(repo_config, args.sync)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
