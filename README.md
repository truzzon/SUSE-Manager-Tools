# SUSE-Manager-Tools

The following scripts are included:
- sync_channel.py
This will clone the give channel with the channel it is cloned from.

- sync_stage.py
This will clone the given basechannel and all its child channels from the channels they are cloned from.

- system_update.py
This script will can perform several tasks:
* based on the settings in configsm.yaml it can do a Support Pack Migration
* it will apply the latest updates available in assigned channels to the server
* will apply configuration channels, if defined
* if updates are being applied it will reboot the server. This can be prevented with a parameter.

- channel_cloner.py
The script will create cloned channels. This is based on the information stored in configsm.yaml

- cve_report.py
This script will report all systems with the given CVE(s)

Each script will have a --help to see all available parameters.

More documentation will follow............

For python3 the following packages are needed:
python3
python3-Jinja2
python3-simplejson
python-Jinja2
python-simplejson
python3-PyYAML
python3-pyaml  

How to use:
- The file configsm.yaml should be in the same directory as the scripts. And before using check the file and correct the information.


GNU Public License. No warranty. No Support 
For question/suggestions/bugs mail: michael.brookhuis@suse.com
Created by: SUSE Michael Brookhuis 2019


