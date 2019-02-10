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

import os, sys, subprocess, xmlrpc.client, time, datetime, argparse, getpass, yaml, logging, smtools
from argparse import RawTextHelpFormatter

def create_backup(ses,par,dat):
    clo = "bu-"+dat+"-"+par
    clo_str={}
    clo_str['name']=clo
    clo_str['label']=clo
    clo_str['summary']=clo
    smtools.log_info("Creating backup of current channel. Channel will be called with: %s" % clo)
    try:
       dummy = client.channel.software.clone(ses,par,clo_str,False)
    except xmlrpc.client.Fault as e:
       smtools.fatal_error('Unable to create backup. Please check logs')
    try:
       cc = client.channel.software.listChildren(ses,par)
    except xmlrpc.client.Fault as e:
       smtools.fatal_error('Unable to get list child channels for parent channel %s. Please check logs' % par)
    for x in cc:
        clo_str={}
        clo_str['name']="bu-"+dat+"-"+x.get('label')
        clo_str['label']="bu-"+dat+"-"+x.get('label')
        clo_str['summary']="bu-"+dat+"-"+x.get('label')
        clo_str['parent_label']=clo
        temp=clo+"-"+x.get('label')
        try:
           dummy = client.channel.software.clone(ses,x.get('label'),clo_str,False)
        except xmlrpc.client.Fault as e:
           smtools.fatal_error('Unable to clone child channel %s. Please check logs' % clo+"-"+x.get('label') )
    smtools.log_info("Creating backup finished")

def main():
    # Check if parameters have been given
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,description=('''\
         Usage:
         sync_channel.py
    
               '''))
    parser.add_argument("-c", "--channel", help="name of the cloned parent channel to be updates")
    parser.add_argument("-b", "--backup", action="store_true", default=0, help="creates a backup of the stage first.")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.1, February 10, 2019')
    args = parser.parse_args()
    
    smtools.set_logging()
     
    if not args.channel:
       smtools.fatal_error("No parent channel to be cloned given. Aborting operation")
    else:
       parent = args.channel
    global client
    global session
    (client,session)=smtools.suman_login()
 
    try:
       pd = client.channel.software.getDetails(session,parent)
    except xmlrpc.client.Fault as e:
       smtools.fatal_error('Unable to get details of parent channel %s. Does the channel exist or is it a cloned channel?' % parent)
    
    if pd.get('parent_channel_label'):
       smtools.fatal_error("Given parent channel %s, is not a parent channel. Aborting operation" % parent)
    try:
       cc = client.channel.software.listChildren(session,parent)
    except xmlrpc.client.Fault as e:
       smtools.fatal_error('Unable to get list child channels. Please check logs')
    
    smtools.log_info("Updating the following channels with latest patches and packages")
    smtools.log_info("================================================================")
    
    if args.backup:
       date = ("%s%02d%02d" % (datetime.datetime.now().year,datetime.datetime.now().month,datetime.datetime.now().day))
       buc = "bu-"+date+"-"+parent
       try:
          pd = client.channel.software.getDetails(session,buc)
       except xmlrpc.client.Fault as e:
          create_backup(session,parent,date)
       else:
          smtools.fatal_error('The backupchannel %s already exists. Aborting operation.' % buc)
    
    for x in cc:
       if not "pool" in x.get('label') or "iso" in x.get('label') :
          smtools.log_info('Updating %s' % x.get('label') )
          try:
              clone_from_label = client.channel.software.getDetails(session,x.get('label')).get('clone_original')
          except xmlrpc.client.Fault as e:
              smtools.minor_error('Unable to get parent data for channel %s. Has this channel been cloned. Skipping' % x.get('label'))
              continue
    
          smtools.log_info('     Errata .....')
          try:
              erratas = client.channel.software.mergeErrata(session,clone_from_label,x.get('label'))
          except xmlrpc.client.Fault as e:
              smtools.minor_error('Unable to get errata for channel %s. Continue with next channel' % x.get('label'))
              continue
          time.sleep(10)
          smtools.log_info('     Packages .....')
          try:
              packages = client.channel.software.mergePackages(session,clone_from_label,x.get('label'))
          except xmlrpc.client.Fault as e:
              smtools.minor_error('Unable to get packages for channel %s. Continue with next channel' % x.get('label'))
              continue
          time.sleep(20)
    smtools.close_program()

if __name__ == "__main__":
    SystemExit(main())

