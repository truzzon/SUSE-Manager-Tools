#!/usr/bin/env python3
#
# CVEReport
#
# (c) 2019 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2019-02-12
#
# Created by: SUSE Michael Brookhuis
#
# This script will generate an comma-delimited file with system effected.
#
# Releases:
# 2019-02-12 M.Brookhuis - initial release.
#
#
#
#

import os, re, sys, time, datetime, argparse, xmlrpc.client, socket, smtools
from argparse import RawTextHelpFormatter

error_found=False
error_text=""

######################################################################

def create_file_cve(cve_data,fn):
    file = open(fn, "w")
    if not cve_data:
         file.write("NO CVE\n")
    else:
         file.write("System Name;CVE;Patch-Name;Patch available,channel containing patch;Packages included\n")
         for x in cve_data:
              file.write(x[0])
              file.write(";")
              file.write(x[1])
              file.write(";")
              file.write(x[2])
              file.write(";")
              file.write(x[3])
              file.write(";")
              file.write(x[4])
              file.write(";")
              file.write(x[5])
              file.write("\n")
    file.close()
    return

def create_file_cve_reverse(cve_data,fn):
    file = open(fn, "w")
    if not cve_data:
         file.write("NO CVE\n")
    else:
         file.write("System Name;CVE\n")
         for x in cve_data:
              file.write(x[0])
              file.write(";")
              file.write(x[1])
              file.write("\n")
    file.close()
    return

def logfile_present(s):
    try:
        file=open(s, 'w')
    except:
        msg = "Not a valid file: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)
    file.close()
    return s


######################################################################
# main
######################################################################

def main():    
    smtools.set_logging()
    
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,description=('''\
         Usage:
         CVEReport.py 
                 
               '''))
    parser.add_argument("-c", "--cve", help="list of CVEs to be checked, comma delimeted, no spaces",required=True)
    parser.add_argument("-r", "--reverse", action="store_true", default=0, help="list systems that have the CVE installed")
    parser.add_argument("-f", "--filename", help="filename the data should be writen in. If no path is given it will be stored in directory where the script has been started. Mandatory", required=True,type=logfile_present)
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1, October 20, 2017')
    args = parser.parse_args()
    
    smtools.log_info("") 
    smtools.log_info("Start %s" %  datetime.datetime.now())
    smtools.log_info("") 
    smtools.log_info("Given list of CVEs: %s" % args.cve) 
    smtools.log_info("") 
    
    (client,session)=smtools.suman_login()
    cve_split=[]
    for i in args.cve.split(','):
      cve_split.append(i)

    cve_data_collected=[]
    for cve in cve_split:
        # Collecting a list of all systems that are vulnerable for this CVE
        cve_found=False
        # If there are items found in the CVE-list, continue. If the list is empty, print error. Empty files will be created.
        if not args.reverse:
           try:
               cve_list = client.audit.listSystemsByPatchStatus(session,cve,["AFFECTED_PATCH_INAPPLICABLE","AFFECTED_PATCH_APPLICABLE"])
           except:
               cve_list = []
           if not cve_list:
              smtools.log_warning("Given CVE %s does not exist." % cve)
              break
           else:
              smtools.log_info("Processing CVE %s." % cve)
           for cve_system in cve_list:
               cve_data=[]
               try: 
                   cve_data.append(client.system.getName(session,cve_system.get("system_id")).get("name"))
               except:
                   smtools.log_error("unable to get hostname for system with ID %s" % cve_system.get("system_id"))
                   break
               cve_data.append(cve)
               adv_list=""
               pack_list=""
               for adv in cve_system.get('errata_advisories'):
                   if adv_list:
                      adv_list=adv_list+", "+adv
                   else:
                      adv_list=adv
                   try:
                      cve_packages=client.errata.listPackages(session,adv)
                   except:
                      print("unable to find packages")
                   for package in cve_packages:
                      pack=package.get('name')+"-"+package.get('version')+"-"+package.get('release')+"-"+package.get('arch_label')
                      if pack_list:
                         pack_list=pack_list+", "+pack
                      else:
                         pack_list=pack
               cve_data.append(adv_list)
               cve_data.append(cve_system.get('patch_status'))
               chan_list=""
               for chan in cve_system.get("channel_labels"):
                   if chan_list:
                      chan_list=chan_list+", "+chan 
                   else:
                      chan_list=chan
               cve_data.append(chan_list)
               cve_data.append(pack_list)
               cve_data_collected.append(cve_data)
           smtools.log_info("Completed.")
        else:  
           try:
               cve_list = client.audit.listSystemsByPatchStatus(session,cve,["NOT_AFFECTED", "PATCHED"])
           except:
               cve_list = []
           if not cve_list:
              smtools.log_warning("Given CVE %s does not exist." % cve)
              break
           else:
              smtools.log_info("Processing CVE %s." % cve)
           for cve_system in cve_list:
               cve_data=[]
               try:
                   cve_data.append(client.system.getName(session,cve_system.get("system_id")).get("name"))
               except:
                   smtools.log_error("unable to get hostname for system with ID %s" % cve_system.get("system_id"))
                   break
               cve_data.append(cve)
               cve_data_collected.append(cve_data)
           smtools.log_info("Completed.")
    if not args.reverse:
       create_file_cve(cve_data_collected,args.filename)
    else:
       create_file_cve_reverse(cve_data_collected,args.filename)
    smtools.log_info("Result can be found in file %s" % args.filename)    
    smtools.suman_logout(client,session)
    smtools.close_program()


if __name__ == "__main__":
    SystemExit(main())
