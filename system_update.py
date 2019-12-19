#!/usr/bin/env python3
#
# SystemUpdate
#
# (c) 2018 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting
#
# Version: 2019-04-29
#
# Created by: SUSE Michael Brookhuis
#
# This script will perform the following actions:
# - will check spmig and see if for the given system a SPMigration can be done. 
# - if not SPMigration can be performed, the system will be updated.
#
# Releases:
# 2019-04-29 M.Brookhuis - Initial release
#
#

"""
This script will perform a complete system maintenance
"""

import argparse
from argparse import RawTextHelpFormatter
import xmlrpc.client
import time
import datetime
import smtools

__smt = None


def do_apply_updates_errata(system_id, updateble_patches, salt_minion_patch_id, zypper_patch_id):
    """
    schedule action chain with updates for errata
    """
    schedule_id = None
    patches = []
    for patch in updateble_patches:
        no_zypper = True
        no_salt = True
        for id in salt_minion_patch_id:
            if patch.get('id') == id:
                no_salt = False
                break
        for id in zypper_patch_id:
            if patch.get('id') == id:
                no_salt = False
                break
        if no_zypper and no_salt:
            patches.append(patch.get('id'))
    if not patches:
        return 0
    try:
        schedule_id = smt.client.system.scheduleApplyErrata(smt.session, system_id, patches, datetime.datetime.now())
    except xmlrpc.client.Fault as e:
        smt.fatal_error("unable to schedule job for server. Error: {}".format(e))
    smt.log_info("Errata update running")
    time.sleep(90)
    return schedule_id[0]


def do_update_minion(system_id, updateble_patches):
    """
    schedule action chain with updates for errata
    """
    system_entitlement = None
    try:
        system_entitlement = smt.client.system.getDetails(smt.session, system_id).get('base_entitlement')
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to get a list of updatable rpms")
    if not "salt" in system_entitlement:
        return 0
    patches = []
    for patch in updateble_patches:
        if "salt" in patch.get('advisory_synopsis').lower():
            patches.append(patch.get('id'))
            print(patch)
    if not patches:
        smt.log_info('No update for salt-minion"')
        return []
    idp = 0
    for patch in patches:
        if patch > idp:
            idp = patch
    patchid = [idp]
    print(patchid)
    try:
        smt.client.system.scheduleApplyErrata(smt.session, system_id, patchid, datetime.datetime.now())
    except xmlrpc.client.Fault as e:
        smt.fatal_error("unable to schedule job for server. Error: {}".format(e))
    smt.log_info("Updating salt-minion")
    time.sleep(30)
    try:
        smt.client.system.schedulePackageRefresh(smt.session, system_id, datetime.datetime.now())
    except xmlrpc.client.Fault:
        smt.fatal_error("Package refresh failed for system ")
    time.sleep(15)
    return patches


def do_update_zypper(system_id, updateble_patches):
    """
    schedule action chain with updates for errata
    """
    patches = []
    for patch in updateble_patches:
        if "zlib" in patch.get('advisory_synopsis').lower() or "zypp" in patch.get('advisory_synopsis').lower():
            patches.append(patch.get('id'))
    if not patches:
        smt.log_info('No update for zypper"')
        return []
    try:
        smt.client.system.scheduleApplyErrata(smt.session, system_id, patches, datetime.datetime.now())
    except xmlrpc.client.Fault as e:
        smt.fatal_error("unable to schedule job for server. Error: {}".format(e))
    smt.log_info("Updating zypper")
    time.sleep(30)
    try:
        smt.client.system.schedulePackageRefresh(smt.session, system_id, datetime.datetime.now())
    except xmlrpc.client.Fault:
        smt.fatal_error("Package refresh failed for system")
    time.sleep(15)
    return patches


def do_apply_updates_packages(system_id):
    """
    schedule action chain with updates
    """
    rpms = []
    updatable_rpms = schedule_id = None
    try:
        updatable_rpms = smt.client.system.listLatestUpgradablePackages(smt.session, system_id)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to get a list of updatable rpms")
    for rpm in updatable_rpms:
        rpms.append(rpm.get('to_package_id'))
    if not rpms:
        smt.log_info('no package updates available')
        return 0
    try:
        schedule_id = smt.client.system.schedulePackageInstall(smt.session, system_id, rpms, datetime.datetime.now())
    except xmlrpc.client.Fault as e:
        smt.fatal_error("unable to schedule job for server. Error: {}".format(e))
    smt.log_info("Package update running")
    time.sleep(90)
    return schedule_id


def do_upgrade(system_id, server, no_reboot):
    """
    do upgrade of packages
    """
    updateble_patches = None
    timeout = smtools.CONFIGSM['suman']['timeout']
    try:
        updateble_patches = smt.client.system.getRelevantErrata(smt.session, system_id)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to get a list of updatable rpms")
    if updateble_patches:
        salt_minion_patch_id = do_update_minion(system_id, updateble_patches)
        zypper_patch_id = do_update_zypper(system_id, updateble_patches)
        schedule_id = do_apply_updates_errata(system_id, updateble_patches, salt_minion_patch_id, zypper_patch_id)
        reboot_needed_errata = True
    else:
        smt.log_info('no errata updates available')
        schedule_id = 0
        reboot_needed_errata = False
    reboot_needed_package = True
    if schedule_id == 0:
        smt.log_info("Errata update not needed. Checking for package update")
    else:
        (result_failed, result_completed, result_message) = check_progress(schedule_id, system_id, server, timeout,
                                                                           "Errata Update")
        if result_completed == 1 and not no_reboot:
            smt.log_info("Errata update completed successful.")
        elif result_completed == 1 and no_reboot:
            smt.log_info("Errata update completed successful.")
            smt.log_info("But server {} will not be rebooted. Please reboot manually ASAP.".format(server))
        else:
            smt.fatal_error(
                "Errata update failed!!!!! Server {} will not be updated!\n\nThe error messages is:\n{}".format(server,
                                                                                                                result_message))
        try:
            smt.client.system.schedulePackageRefresh(smt.session, system_id, datetime.datetime.now())
        except xmlrpc.client.Fault:
            smt.fatal_error("Package refresh failed for system %s!".format(server))
        time.sleep(30)
        timeout -= 30
    schedule_id = do_apply_updates_packages(system_id)
    if schedule_id == 0:
        smt.log_info("Package update not needed.")
        if reboot_needed_errata:
            reboot_needed_package = True
        else:
            reboot_needed_package = False
    else:
        (result_failed, result_completed, result_message) = check_progress(schedule_id, system_id, server, timeout,
                                                                           "Package Update")
        if result_completed == 1 and not no_reboot:
            smt.log_info("Package update completed successful.")
        elif result_completed == 1 and no_reboot:
            smt.log_info("Package update completed successful.")
            smt.log_info("But server {} will not be rebooted. Please reboot manually ASAP.".format(server))
        else:
            smt.fatal_error(
                "Package update failed!!!!! Server {} will not be updated!!\n\nThe error messages is:\n{}".format(
                    server, result_message))
        try:
            smt.client.system.schedulePackageRefresh(smt.session, system_id, datetime.datetime.now())
        except xmlrpc.client.Fault:
            smt.fatal_error("Package refresh failed for system %s!".format(server))
        try:
            smt.client.system.scheduleHardwareRefresh(smt.session, system_id, datetime.datetime.now())
        except xmlrpc.client.Fault:
            smt.fatal_error("Package refresh failed for system %s!".format(server))
    if not no_reboot and reboot_needed_package and reboot_needed_errata:
        try:
            schedule_id = smt.client.system.scheduleReboot(smt.session, system_id, datetime.datetime.now())
        except xmlrpc.client.Fault:
            smt.fatal_error("Unable to reboot server {}!".format(server))
        smt.log_info("Rebooting server")
        timeout = smtools.CONFIGSM['suman']['timeout'] - 240
        time.sleep(240)
        (result_failed, result_completed, result_message) = check_progress(schedule_id, system_id, server, timeout,
                                                                           "Reboot")
        if result_completed == 1:
            smt.log_info("Reboot completed successful.")
        else:
            smt.log_info("Reboot failed. Please reboot manually ASAP.")
            smt.fatal_error("Reboot failed. Please reboot manually ASAP.")
    return


def do_spmigrate(system_id, server, new_basechannel, no_reboot):
    """
    Perform a sp migration for the given server
    """
    checked_new_child_channels = []
    old_basechannel = new_child_channels = all_child_channels = action_id = None
    try:
        old_basechannel = smt.client.system.getSubscribedBaseChannel(smt.session, system_id)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to receive currently assigned childchannels for system {}".format(server))
    (migration_available, migration_targets) = check_spmigration_available(system_id, old_basechannel)
    if not migration_available:
        smt.fatal_error(
            "For the system {} no higher SupportPack is available. Please check in SUSE Manager GUI!!".format(server))
    sp_old = "sp" + str(old_basechannel.get('label').split("sp")[1][:1])
    sp_new = "sp" + str(new_basechannel.split("sp")[1][:1])
    try:
        smt.client.channel.software.getDetails(smt.session, new_basechannel)
    except xmlrpc.client.Fault:
        smt.log_info("There is a newer SP available, but that has not been setup for the stage the server is in")
        return
    try:
        new_child_channels = [c.get('label').replace(sp_old, sp_new) for c in
                              smt.client.system.listSubscribedChildChannels(smt.session, system_id)]
    except xmlrpc.client.Fault:
        smt.fatal_error("Getting new child channels for the system {} failed!".format(server))
    if smtools.CONFIGSM['maintenance']['sp_migration_project']:
        temp_child_channels = []
        for child_channel in new_child_channels:
            for project, new_pr in smtools.CONFIGSM['maintenance']['sp_migration_project'].items():
                if project == child_channel.split("-")[0]:
                    temp_child_channels.append(child_channel.replace(project, new_pr))
        new_child_channels = temp_child_channels
    try:
        all_child_channels = [c.get('label') for c in
                              smt.client.channel.software.listChildren(smt.session, new_basechannel)]
    except xmlrpc.client.Fault:
        smt.fatal_error("Getting all child channels failed!")
    for channel in new_child_channels:
        if check_channel(channel, all_child_channels):
            checked_new_child_channels.append(channel)
    do_upgrade(system_id, server, False)
    time.sleep(30)
    try:
        action_id = smt.client.system.scheduleSPMigration(smt.session, system_id, new_basechannel,
                                                          checked_new_child_channels,
                                                          True, datetime.datetime.now())
    except xmlrpc.client.Fault:
        smt.fatal_error(
            "Unable to schedule dry run for Support Pack migration for system {} failed!\nThe error is: {}".format(
                server, get_script_output(action_id)))
    smt.log_info("SupportPack Migration dry run running for system {}".format(server))
    smt.log_info("New basechannel will be: {}".format(new_basechannel))
    time.sleep(60)
    timeout = smtools.CONFIGSM['suman']['timeout'] - 90
    (result_failed, result_completed, result_message) = check_progress(action_id, system_id, server, timeout,
                                                                       "SP Migration dry run")
    res_o = get_spmig_details(action_id, system_id, server)
    if result_failed == 0:
        try:
            action_id = smt.client.system.scheduleSPMigration(smt.session, system_id, new_basechannel,
                                                              checked_new_child_channels, False,
                                                              datetime.datetime.now())
        except xmlrpc.client.Fault as e:
            smt.fatal_error(
                "Unable to schedule Support Pack migration for system {} failed!\nThe error is: {}".format(server, e))
    else:
        smt.fatal_error(
            "SupportPack Migration Dry Run failed!!!!! Server {} will not be updated!\nOutput: \n{}".format(server,
                                                                                                            res_o))
    smt.log_info("SupportPack Migration running for system {}".format(server))
    timeout = smtools.CONFIGSM['suman']['timeout'] - 300
    time.sleep(300)
    (result_failed, result_completed, result_message) = check_progress(action_id, system_id, server, timeout,
                                                                       "SP Migration")
    if result_completed == 1 and not no_reboot:
        smt.log_info("Support Pack migration completed successful, rebooting server {}".format(server))
        try:
            smt.client.system.scheduleReboot(smt.session, system_id, datetime.datetime.now())
        except xmlrpc.client.Fault:
            smt.fatal_error("Unable to reboot server {}!".format(server))
    elif result_completed == 1 and no_reboot:
        smt.log_info(
            "Support Pack migration completed successful, but server {} will not be rebooted. Please reboot manually ASAP.".format(
                server))
    else:
        smt.fatal_error(
            "SupportPack Migration failed!!!!! Server {} will not be updated!\nOutput: \n{}".format(server, res_o))
    try:
        smt.client.system.schedulePackageRefresh(smt.session, system_id, datetime.datetime.now())
    except xmlrpc.client.Fault:
        smt.fatal_error("Package refresh failed for system {}!".format(server))
    # Perform hardware refresh to ensure that SUSE Manager knows about the update
    try:
        smt.client.system.scheduleHardwareRefresh(smt.session, system_id, datetime.datetime.now())
    except xmlrpc.client.Fault:
        smt.fatal_error("Package refresh failed for system {}!".format(server))
    smt.log_info("Support pack migration is successful. Output:\n{}".format(res_o))
    # change_systemgroups(clt,ses,sd,nbc,hae_present)


def get_spmig_details(action_id, system_id, server):
    """
    output from running script
    """
    results = outp = None
    try:
        results = smt.client.system.listSystemEvents(smt.session, system_id)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to get system events for system {}!".format(server))
    for result in results:
        if result.get('id') == action_id:
            outp = result.get('result_msg')
            return outp
    smt.fatal_error("System {} is not having a event ID. Aborting!".format(server))
    return outp


def get_script_output(action_id):
    """
    output from running script
    """
    script_output = script_results = None
    try:
        script_results = smt.client.system.getScriptResults(smt.session, action_id)
    except xmlrpc.client.Fault:
        script_output = "No output available"
    for result in script_results:
        script_output = result.get('output')
    return script_output


def check_channel(channel, channel_all):
    """
    Check if the channel exists.
    """
    for chan in channel_all:
        if channel in chan:
            return True
    return False


def check_spmigration_available(system_id, base_channel):
    """
    Check if there is a SP migration is available
    """
    migration_targets = []
    try:
        migration_targets = smt.client.system.listMigrationTargets(smt.session, system_id)
    except xmlrpc.client.Fault as e:
        smt.fatal_error(("Unable to receive SP Migration targets. Error: \n{}".format(e)))
    sp = "sp" + str(int(base_channel.get('label').split("sp")[1][:1]) + 1)
    for x in migration_targets:
        if sp.lower() in x.get('friendly').lower():
            return True, migration_targets
    return False, migration_targets


def check_for_sp_migration(server, sid):
    """
    Check if a sp migration is released for this server
    """
    current_version = current_bc = None
    try:
        current_bc = smt.client.system.getSubscribedBaseChannel(smt.session, sid).get('label')
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to connect SUSE Manager to login to get the base channel for a system")
    if "sle" not in current_bc:
        smt.log_info("System is not running SLE. SP Migration not possible")
        return False, ""
    if "11-" in current_bc:
        current_version = "sles11-"
    elif "12-" in current_bc:
        current_version = "sles12-"
    elif "15-" in current_bc:
        current_version = "sles15-"
    if "sp" not in current_bc:
        current_sp = "sp0"
    else:
        current_sp = "sp" + str(current_bc.split("sp")[1].split("-")[0])
    current_version += current_sp
    if smtools.CONFIGSM['maintenance']['sp_migration_project']:
        for project, new_pr in smtools.CONFIGSM['maintenance']['sp_migration_project'].items():
            if server_is_exception(server, new_pr):
                return False, ""
            if project == current_bc.split("-")[0] and not server_is_exception(server, new_pr):
                current_bc = current_bc.replace(project, new_pr)
                new_sp = "sp" + str(int(current_bc.split('sp')[1].split('-')[0]) + 1)
                return True, current_bc.replace(current_sp, new_sp)
    if smtools.CONFIGSM['maintenance']['sp_migration']:
        for key, value in smtools.CONFIGSM['maintenance']['sp_migration'].items():
            if key == current_version and not server_is_exception(server, value):
                return True, current_bc.replace(current_sp, value.split("-")[1])
    return False, ""


def server_is_exception(server, new_channel):
    """
    Check if server is an exception
    """
    if smtools.CONFIGSM['maintenance']['exception_sp']:
        for key, value in smtools.CONFIGSM['maintenance']['exception_sp'].items():
            if key == new_channel:
                for server_exception in value:
                    if server == server_exception:
                        return True
    return False


def event_status(action_id, system_id, server):
    """
    Check status of event
    """
    results = None
    try:
        results = smt.client.system.listSystemEvents(smt.session, system_id)
    except xmlrpc.client.Fault:
        smt.fatal_error("Unable to get system events for system {}!".format(server))
    for result in results:
        if result.get('id') == action_id:
            return result.get('failed_count'), result.get('successful_count'), result.get('result_msg')
    smt.fatal_error("System {} is not having a event ID. Aborting!".format(server))


def check_progress(action_id, system_id, server, timeout, action):
    """
    Check progress of action
    """
    (failed_count, completed_count, result_message) = event_status(action_id, system_id, server)
    while failed_count == 0 and completed_count == 0 and timeout > 0:
        (failed_count, completed_count, result_message) = event_status(action_id, system_id, server)
        smt.log_info("Still Running")
        time.sleep(15)
        timeout -= 15
    if timeout <= 0:
        smt.fatal_error("Action {} run in timeout. Please check server {}. Aborting process".format(action, server))
    return failed_count, completed_count, result_message


def system_is_inactive(system_id):
    """
    Check if the system is not inactive for at least 1 day
    """
    try:
        inactive_systems = smt.client.system.listInactiveSystems(smt.session, 1)
    except xmlrpc.client.Fault as e:
        smt.fatal_error(("Unable to receive list of inactive systems. Error: \n{}".format(e)))
    for system in inactive_systems:
        if system_id == system.get('id'):
            return True
    return False


def server_is_exception_update(server):
    """
    Check if server is an exception for updating
    """
    if smtools.CONFIGSM['maintenance']['exclude_for_patch']:
        for server_exl in smtools.CONFIGSM['maintenance']['exclude_for_patch']:
            if server_exl == server:
                return True
    return False


def do_deploy_config(server, sid):
    """
    Apply configuration
    """
    entitlement = action_id = None
    try:
        entitlement = smt.client.system.getDetails(smt.session, sid)
    except xmlrpc.client.Fault:
        smt.fatal_error('Unable to retrieve entitlement data')
    if entitlement.get('base_entitlement') == "salt_entitled":
        smt.log_info("System is salt, performing highstate")
        try:
            action_id = smt.client.system.scheduleApplyHighstate(smt.session, sid,
                                                                 xmlrpc.client.DateTime(datetime.datetime.now()), False)
        except xmlrpc.client.Fault:
            smt.fatal_error("Error deploying configuration")
        timeout = smtools.CONFIGSM['suman']['timeout']
        (result_failed, result_completed, result_message) = check_progress(action_id, sid, server, timeout,
                                                                           "Deploy Configuration")
        if result_completed == 1:
            smt.log_info("Highstate completed successful.")
        else:
            smt.log_info("Highstate failed. Continuing")
            smt.minor_error("Highstate failed. Please check.")


def update_server(args):
    """
    start update process
    """
    system_id = smt.get_server_id()
    if server_is_exception_update(args.server):
        smt.fatal_error("Server {} is in list of exceptions and will not be updated.".format(args.server))
    if system_is_inactive(system_id):
        smt.fatal_error(
            "Server {} is inactive for at least a day. Please check. System will not be updated.".format(args.server))
    if args.applyconfig:
        do_deploy_config(args.server, system_id)
    (do_spm, new_basechannel) = check_for_sp_migration(args.server, system_id)
    if do_spm:
        smt.log_info("Server {} will get a SupportPack Migration to {} ".format(args.server, new_basechannel))
        do_spmigrate(system_id, args.server, new_basechannel, args.noreboot)
    else:
        smt.log_info("Server {} will be upgraded with latest available patches".format(args.server))
        do_upgrade(system_id, args.server, args.noreboot)
    if args.applyconfig:
        do_deploy_config(args.server, system_id)


def main():
    """
    Main function
    """
    global smt
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
        Usage:
        system_update.py 
            '''))
    parser.add_argument('-s', '--server', help='name of the server to receive config update. Required')
    parser.add_argument("-n", "--noreboot", action="store_true", default=0,
                        help="Do not reboot server after patching or supportpack upgrade.")
    parser.add_argument("-c", '--applyconfig', action="store_true", default=0,
                        help="Apply configuration after and before patching")
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.2, November 16, 2018')
    args = parser.parse_args()
    if not args.server:
        smt = smtools.SMTools("system_update")
        smt.log_error("The option --server is mandatory. Exiting script")
        smt.exit_program(1)
    else:
        smt = smtools.SMTools("system_update", args.server.lower(), True)
        smt.set_hostname(args.server.lower())
    # login to suse manager
    smt.log_info("Start")
    smt.suman_login()
    update_server(args)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
