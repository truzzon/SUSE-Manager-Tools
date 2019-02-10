#!/usr/bin/env python2
#
# Script: smtools.py
#
# (c) 2013 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting)
#
# Version: 2017-10-11
#
# Created by: SUSE Michael Brookhuis,
#
# Description: This script contains standard function that can be used in several other scripts
#
# Releases:
# 2017-10-14 M.Brookhuis - initial release.
# 2018-11-15 M.Brookhuis - Moved to python3.
#                        - Moved config to YAML
#


import logging, os, sys, subprocess, xmlrpclib, datetime, time, re, smtplib, base64, yaml, inspect
from email.mime.text import MIMEText

error_found=False
error_text=""
hostname=""

if not os.path.isfile(os.path.dirname(__file__)+"/configsm.yaml"):
   print("ERROR: configsm.yaml doesn't exist. Please create file")
   sys.exit(1)
else:
    configsm=yaml.load(open(os.path.dirname(__file__)+'/configsm.yaml'))

####################################sm#########
#
# Functions
#

def set_logging(hn="",fb=False):
    global logger
    if fb:
       if not os.path.exists(configsm['dirs']['log_dir']+"/"+sys.argv[0].split('/')[-1].split('.')[0]):
          os.makedirs(configsm['dirs']['log_dir']+"/"+sys.argv[0].split('/')[-1].split('.')[0])
       logname=configsm['dirs']['log_dir']+"/"+sys.argv[0].split('/')[-1].split('.')[0]+"/"+"server-"+hn+".log"
    else:
       if not os.path.exists(configsm['dirs']['log_dir']):
          os.makedirs(configsm['dirs']['log_dir'])
       logname=configsm['dirs']['log_dir']+"/"+sys.argv[0].split('/')[-1].split('.')[0]+".log"
    logging.basicConfig(filename=logname,
       filemode='a',
       format='%(asctime)s : %(name)s : %(levelname)s - %(message)s',
       datefmt='%d-%m-%Y %H:%M:%S',
       level=logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(console)    
    logger = logging.getLogger(hn)

def read_yaml():
    if not os.path.isfile(os.path.dirname(__file__)+"/configsm.yaml"):
       print("ERROR: configsm.yaml doesn't exist. Please create file")
       sys.exit(1)
    else:
       return yaml.load(open(os.path.dirname(__file__)+'configsm.yaml'))

def suman_login():
    clt = xmlrpclib.Server("http://"+configsm['suman']['server']+"/rpc/api")
    try:
       ses = clt.auth.login(configsm['suman']['user'], configsm['suman']['password'])
    except xmlrpclib.Fault as e:
       logger.error("| %s | Unable to login to SUSE Manager server" % hostname)
       sys.exit(1)
    return clt,ses

def suman_logout(clt,ses):
    try:
        clt.auth.logout(ses)
    except xmlrpclib.Fault as e:
        logger.error("| %s | Unable to logout from SUSE Manager" % hostname)
        error_found=True
        error_text=error_text+"\n Problem closing connection to SUSE Manager"

def minor_error(errtxt):
    global error_found
    global error_text
    error_found=True
    logger.warning("| %s" % (errtxt))
    error_text=error_text+"\n"+errtxt

def fatal_error(errtxt,rc=1):
    global error_found
    global error_text
    error_found=True
    error_text=error_text+"\n"+errtxt
    logger.error("| %s" % (errtxt))
    close_program(rc)

def log_info(txt):
    logger.info("| %s" % (txt))

def log_error(txt):
    logger.error("| %s" % (txt))


def send_mail():
    global error_found
    global error_text
    script=os.path.basename(sys.argv[0])
    try:
       s = smtplib.SMTP(configsm['smtp']['server'])
    except:
       print ("error when sending mail")
    #s.set_debuglevel(1)
    txt=("Dear admin,\n\nThe job %s has run today at %s. Unfortunately there have been some errors.\n\nPlease see the following list:\n" % (script,datetime.datetime.now()))
    error_text=txt+error_text
    msg = MIMEText(error_text)
    sender = configsm['smtp']['sender']
    recipients = configsm['smtp']['receivers']
    msg['Subject'] = ("[%s] on server %s from %s has errors" % (script,hostname,datetime.datetime.now()))
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    try:
       s.sendmail(sender, recipients, msg.as_string())
    except:
       loggeer.error("sending mail failed")
       
def set_hostname(hn):
    global hostname
    hostname=hn

def close_program(rc=0):
    logging.info("| Finished %s" % (datetime.datetime.now()))
    if error_found:
       if configsm['smtp']['sendmail']:
          send_mail()
    sys.exit(rc)

   

