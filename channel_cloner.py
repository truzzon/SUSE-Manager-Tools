#!/usr/bin/env python3
#
# channel_cloner
#
# (c) 2019 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting)
#
# Version: 2019-01-16
#
# Created by: SUSE Michael Brookhuis
#
# This script will create a clone of a base channel from a given data.
#
# Releases:
# 2019-01-16 M.Brookhuis    - initial release.
# 2019-09-18 M.Brookhuis    - update to python3.

import argparse
import xmlrpc.client
import datetime
import time
from argparse import RawTextHelpFormatter
import smtools

VERSION = '0.0.2'
__smt = None


def clone_channel(cs, cv, par, ori):
    """
    clone_channel
    :param cs: source channel
    :param cv: target channel
    :param par: parent target should be in
    :param ori: include patches and packages
    :return:
    """
    clone = {'name': cv, 'label': cv, 'summary': cv, 'parent_label': par, 'checksum': 'sha256'}
    try:
        smt.client.channel.software.clone(smt.session, cs, clone, ori)
    except xmlrpc.client.Fault:
        smt.log_error("Unable to clone channel {} from {}.".format(cv, cs))


def add_packages(cv):
    """
    Add the packages from the Errata to the channel
    """
    time.sleep(10)
    try:
        erratas = smt.client.channel.software.listErrata(smt.session, cv)
    except xmlrpc.client.Fault:
        smt.log_error("Unable to get list of Errate for  {}.".format(cv))
        return
    packages = []
    ep = None
    for errata in erratas:
        try:
            ep = smt.client.errata.listPackages(smt.session, errata.get('advisory_name'))
        except xmlrpc.client.Fault:
            smt.log_error("Unable to get package list for {}.".format(errata.get('advisory_name')))
        for pack in ep:
            packages.append(pack.get('id'))
    try:
        smt.client.channel.software.addPackages(smt.session, cv, packages)
    except xmlrpc.client.Fault:
        smt.log_error("Unable to add packages to channel {}.".format(cv))


def valid_date(s):
    """
    Checks if the given date is valid
    """
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'. Format YYYY-MM-DD".format(s)
        raise argparse.ArgumentTypeError(msg)


######################################################################
# main
######################################################################
def main():
    """
    Main Function
    """
    global smt
    smt = smtools.SMTools("channel_cloner")

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         make-activation-key.py 

               '''))
    parser.add_argument("-r", "--release", help="VCT release. Mandatory", required=True)
    parser.add_argument("-s", "--source", help="OS Version. Mandatory", required=True)
    parser.add_argument("-t", "--todate",
                        help="Patches until (and including) this date will be added. Format YYYY-MM-DD.", required=True,
                        type=valid_date)
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="If channel already exists, override")
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1, January 16, 2019')
    args = parser.parse_args()

    if not args.release:
        smt.fatal_error("ERROR: Option --release is mandatory. Aborting operation")
    else:
        release = args.release
    bcsuse = None
    if not args.source:
        smt.fatal_error("Option --source is mandatory. Aborting operation")
    else:
        try:
            bcsuse = smtools.CONFIGSM['channel_cloner'][args.source]['base_channel']
        except xmlrpc.client.Fault:
            smt.fatal_error('The given Source {} does not exist. Aborting operation'.format(args.source))
    smt.suman_login()
    smt.log_info("Cloning channels with patches and packages from the given data")
    smt.log_info("==============================================================")

    # check if source base channel exists
    try:
        smt.client.channel.software.getDetails(smt.session, bcsuse)
    except xmlrpc.client.Fault:
        smt.fatal_error(
            "The base channel {} set in configuration file is not present. Aborting operation".format(bcsuse))

    # check if release is already present and when overwrite has been set delete otherwise exit.
    bcvct = args.release + "-" + bcsuse
    try:
        smt.client.channel.software.getDetails(smt.session, bcvct)
    except xmlrpc.client.Fault:
        # Channel doesn't exist and can be cloned
        smt.log_info("Cloning channel {} to {}".format(bcsuse, bcvct))
    else:
        # channels exist. If overwrite is set delete stage else abort
        if args.overwrite:
            smt.log_info("Channel {} exists. Channel will be deleted first".format(bcvct))
            all_child_channels = None
            try:
                all_child_channels = smt.client.channel.software.listChildren(smt.session, bcvct)
            except xmlrpc.client.Fault:
                smt.fatal_error("unable to get a list of child channels for {}".format(bcvct))
            for child_channel in all_child_channels:
                try:
                    smt.client.channel.software.delete(smt.session, child_channel.get('label'))
                except xmlrpc.client.Fault:
                    smt.log_error("unable to delete channel {}".format(child_channel.get('label')))
            try:
                smt.client.channel.software.delete(smt.session, bcvct)
            except xmlrpc.client.Fault:
                smt.fatal_error("unable to delete channel {}. Aborting".format(bcvct))
            time.sleep(30)
        else:
            smt.fatal_error(
                "Channel {} exists. To delete channel first set -o option. Aborting operation.".format(bcvct))
    smt.log_info("Start cloning")
    # clone base channel
    clone_channel(bcsuse, bcvct, "", False)

    # clone SUSE channels
    for channel in smtools.CONFIGSM['channel_cloner'][args.source]['channels']:
        if "update" in channel:
            clone_channel(channel.split(",")[0], channel.split(",")[1].replace("RELEASE", release), bcvct, True)
            try:
                smt.client.channel.software.mergeErrata(smt.session, channel.split(",")[0],
                                                        channel.split(",")[1].replace("RELEASE", release), "2000-01-01",
                                                        args.todate.strftime("%Y-%m-%d"))
            except xmlrpc.client.Fault:
                smt.log_error("adding errata to {} failed.".format(channel.split(",")[1].replace("RELEASE", release)))
            else:
                smt.log_info("merging errate for channel {}".format(channel.split(",")[1].replace("RELEASE", release)))
                time.sleep(120)
        else:
            clone_channel(channel.split(",")[0], channel.split(",")[1].replace("RELEASE", release), bcvct, False)
    for channel in smtools.CONFIGSM['channel_cloner'][args.source]['channels']:
        if "update" in channel:
            add_packages(channel.split(",")[1].replace("RELEASE", release))

    # Set description to channel
    try:
        smt.client.channel.software.setDetails(smt.session, bcvct,
                                               {'description': ("Release Date: {}".format(args.todate))})
    except xmlrpc.client.Fault:
        smt.log_error("Error setting description for {}".format(bcvct))
    smt.log_info("Finished")
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
