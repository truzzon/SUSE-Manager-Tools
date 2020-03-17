#!/usr/bin/env python3
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
# coding: utf-8

"""
This library contains functions used in other modules
"""

from email.mime.text import MIMEText
import xmlrpc.client
import logging
import os
import sys
import datetime
import smtplib
import yaml


def load_yaml(stream):
    """
    Load YAML data.
    """
    loader = yaml.Loader(stream)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


if not os.path.isfile(os.path.dirname(__file__) + "/configsm.yaml"):
    print("ERROR: configsm.yaml doesn't exist. Please create file")
    sys.exit(1)
else:
    with open(os.path.dirname(__file__) + '/configsm.yaml') as h_cfg:
        CONFIGSM = load_yaml(h_cfg)

class SMTools:
    """
    Class to define needed tools.
    """
    error_text = ""
    error_found = False
    hostname = ""
    client = ""
    session = ""
    sid = ""
    program = "smtools"

    def __init__(self, program, hostname="", hostbased=False):
        """
        Constructor.
        """
        self.hostname = hostname
        self.hostbased = hostbased
        self.program = program
        log_dir = CONFIGSM['dirs']['log_dir']
        if self.hostbased:
            log_dir += "/"+self.program
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_name = log_dir + "/" + self.hostname + ".log"
        else:
            if not os.path.exists(CONFIGSM['dirs']['log_dir']):
                os.makedirs(CONFIGSM['dirs']['log_dir'])
            log_name = os.path.join(log_dir, self.program + ".log")
        logging.basicConfig(filename=log_name,
                            filemode='a',
                            format='%(asctime)s : %(levelname)s | %(message)s',
                            datefmt='%d-%m-%Y %H:%M:%S',
                            level=logging.DEBUG)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        if self.hostbased:
            self.log = logging.getLogger(self.hostname)
            self.log.addHandler(console)
        else:
            self.log = logging.getLogger('')
            self.log.addHandler(console)

    def minor_error(self, errtxt):
        """
        Print minor error.
        """
        self.error_text += errtxt
        self.error_text += "\n"
        self.error_found = True
        self.log_error(errtxt)
        #logging.warning("| {}".format(errtxt))

    def fatal_error(self, errtxt, return_code=1):
        """
        log fatal error and exit program
        """
        self.error_text += errtxt
        self.error_text += "\n"
        self.error_found = True
        self.log.error("| {}".format(errtxt))
        self.close_program(return_code)

    def log_info(self, errtxt):
        """
        Log info text
        """
        self.log.info("| {}".format(errtxt))

    def log_error(self, errtxt):
        """
        Log error text
        """
        self.log.error("| {}".format(errtxt))

    def log_warning(self, errtxt):
        """
        Log error text
        """
        self.log.warning("| {}".format(errtxt))

    def send_mail(self):
        """
        Send Mail.
        """
        script = os.path.basename(sys.argv[0])
        try:
            smtp_connection = smtplib.SMTP(CONFIGSM['smtp']['server'])
        except Exception:
            self.fatal_error("error when sending mail")
        datenow = datetime.datetime.now()
        txt = ("Dear admin,\n\nThe job {} has run today at {}.".format(script, datenow))
        txt += "\n\nUnfortunately there have been some error\n\nPlease see the following list:\n"
        txt += self.error_text
        msg = MIMEText(txt)
        sender = CONFIGSM['smtp']['sender']
        recipients = CONFIGSM['smtp']['receivers']
        msg['Subject'] = ("[{}] on server {} from {} has errors".format(script, self.hostname, datenow))
        msg['From'] = sender
        msg['To'] = ", ".join(recipients)
        try:
            smtp_connection.sendmail(sender, recipients, msg.as_string())
        except Exception:
            self.log.error("sending mail failed")

    def set_hostname(self, host_name):
        """
        Set hostnam for global use.
        """
        self.hostname = host_name

    def close_program(self, return_code=0):
        """Close program and send mail if there is an error"""
        self.suman_logout()
        self.log.info("| Finished")
        if self.error_found and CONFIGSM['smtp']['sendmail']:
            self.send_mail()
            if return_code == 0:
                sys.exit(1)
        sys.exit(return_code)

    def exit_program(self, return_code=0):
        """Exit program and send mail if there is an error"""
        self.log.info("| Finished")
        if self.error_found and CONFIGSM['smtp']['sendmail']:
            self.send_mail()
            if return_code == 0:
                sys.exit(1)
        sys.exit(return_code)

    def suman_login(self):
        """
        Log in to SUSE Manager Server.
        """
        self.client = xmlrpc.client.Server("http://" + CONFIGSM['suman']['server'] + "/rpc/api")
        try:
            self.session = self.client.auth.login(CONFIGSM['suman']['user'], CONFIGSM['suman']['password'])
        except xmlrpc.client.Fault:
            self.fatal_error("| {} | Unable to login to SUSE Manager server".format(CONFIGSM['suman']['server']))

    def suman_logout(self):
        """
        Logout from SUSE Manager Server.
        """
        try:
            self.client.auth.logout(self.session)
        except xmlrpc.client.Fault:
            self.log_error("| {} | Unable to logout from SUSE Manager".format(CONFIGSM['suman']['server']))

    def get_server_id(self):
        """
        Get system Id from host
        """
        all_sid = ""
        try:
            all_sid=self.client.system.getId(self.session, self.hostname)
        except xmlrpc.client.Fault:
            self.fatal_error("Unable to get systemid from system {}. Is this system registered?".format(self.hostname))
        system_id = 0
        for x in all_sid:
            if system_id == 0:
               system_id = x.get('id')
            else:
               self.fatal_error("Duplicate system {}. Please fix and run again.".format(self.hostname))
        if system_id == 0:
            self.fatal_error("Unable to get systemid from system {}. Is this system registered?".format(self.hostname))
        return system_id

    def get_server_id_nofatal(self):
        """
        Get system Id from host
        """
        all_sid = ""
        try:
            all_sid=self.client.system.getId(self.session, self.hostname)
        except xmlrpc.client.Fault:
            self.log_error("Unable to get systemid from system {}. Is this system registered?".format(self.hostname))
            return 0
        system_id = 0
        for x in all_sid:
            if system_id == 0:
               system_id = x.get('id')
            else:
               self.log_error("Duplicate system {}. Please fix and run again.".format(self.hostname))
        if system_id == 0:
            self.log_error("Unable to get systemid from system {}. Is this system registered?".format(self.hostname))
        return system_id
