#!/usr/bin/python
#
# sync-channel
#
# (c) 2017 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting)
#
# Version: 2019-01-14
#
# Created by: SUSE Michael Brookhuis
#
# This script will clone the given channel.
#
# Releases:
# 2017-01-23 M.Brookhuis - initial release.
# 2019-01-14 M.Brookhuis - Added yaml
#                        - Added logging

import os, sys, subprocess, xmlrpclib, time, datetime, argparse, getpass, yaml, logging
from argparse import RawTextHelpFormatter

if os.path.isfile("configsm.yaml"):
   configsm=yaml.load(open('configsm.yaml'))
   useconfigsm=True
else:
   useconfigsm=False

def check_if_exist(ag,g):
    exist = False
    for x in ag:
        if not exist:
           if x == g:
              exist = True
    return exist

def set_logging():
    global logging
    if not os.path.exists("/var/log/rhn"):
          os.makedirs("/var/log/rhn")
    logname="/var/log/rhn/sync-channel.log"
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(filename=logname,
       filemode='a',
       format='%(asctime)s,%(msecs)d %(levelname)s %(message)s',
       datefmt='%H:%M:%S',
       level=logging.DEBUG)


################
# Main Section # 
################

def main():
    # Check if parameters have been given
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-c", "--channel", help="name of the cloned parent channel to be updates")
    parser.add_argument("-u", "--user", help="User with enough rights to perform the need operations. Not needed when set in configsm.yaml")
    parser.add_argument("-p", "--password", help="Password of User. When not given and no configsm.yaml exists, it will be asked")
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1, April 5, 2017')
    args = parser.parse_args()
    
    set_logging()
 
    if not args.channel:
       print("No parent channel to be cloned given. Aborting operation")
       logging.error("No parent channel to be cloned given. Aborting operation")
       sys.exit(1)
    else:
       channel = args.channel
    
    if not args.user and useconfigsm:
       user = configsm['suman']['user']
    elif args.user:
       user = args.user
    else:
       print("No --user given. Aborting operation")
       logging.error("No --user given. Aborting operation")
       sys.exit(1)

    if not args.password and useconfigsm:
       password = configsm['suman']['password']
    elif args.password:
       password = args.password
    else:
       password = getpass.getpass('Password:')

    if useconfigsm:
       server = configsm['suman']['server']
    else:
       server = "127.0.0.1"
 
    client = xmlrpclib.Server("http://"+server+"/rpc/api", verbose=0)
    try:
        session = client.auth.login(user, password)
    except xmlrpclib.Fault, e:
        print ('Failed to log into SUSE Manager Server')
        logging.error('Failed to log into SUSE Manager Server')
        sys.exit(1)
    
    # create a variable containing all channel labels
    try:
        all_channels = client.channel.listSoftwareChannels(session)
    except xmlrpclib.Fault, e:
        print ("Unable to connect SUSE Manager to login to get a list of all software channels")
        logging.error("Unable to connect SUSE Manager to login to get a list of all software channels")
        logging.error("Program: ChangeSoftwareChannel    Section: MAIN  Call: channel.listSoftwareChannels")
        sys.exit(7)
    all_channel_labels = [ c.get('label') for c in all_channels ]
    
    if not check_if_exist(all_channel_labels,channel):
       print ("Given parent channel to be updated doesn't exist. Aborting operation")
       logging.error("Given parent channel to be updated doesn't exist. Aborting operation")
       client.auth.logout(session)
       sys.exit(1)
    
    logging.info("Updating the following channel with latest patches and packages")
    logging.info("===============================================================")
    logging.info("Updating: %s" % channel) 
    try:
       clone_from_label = client.channel.software.getDetails(session,channel).get('clone_original')
    except xmlrpclib.Fault, e:
       print ('Problems accessig the SUSE Manager server. Call: client.channel.software.getDetails')
       logging.error('Problems accessig the SUSE Manager server. Call: client.channel.software.getDetails')
       sys.exit(1)
 
    logging.info('     Errata .....')

    try:
        erratas = client.channel.software.mergeErrata(session,clone_from_label,channel)
    except xmlrpclib.Fault, e:
        print ('Problems accessig the SUSE Manager server. Call: client.channel.software.mergeErrata')
        logging.error('Problems accessig the SUSE Manager server. Call: client.channel.software.mergeErrata')
        sys.exit(1)
    time.sleep(10)
    logging.info('     Packages .....')
    try:
        packages = client.channel.software.mergePackages(session,clone_from_label,channel)
    except xmlrpclib.Fault, e:
        print ('Problems accessig the SUSE Manager server. Call: client.channel.software.mergePackages')
        logging.error('Problems accessig the SUSE Manager server. Call: client.channel.software.mergePackages')
        sys.exit(1)
    time.sleep(20)
    logging.info("FINISHED")
    print("\n========\nFINISHED \n========\n")
     
    client.auth.logout(session)

if __name__ == "__main__":
    SystemExit(main())

