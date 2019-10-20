# SUSE-Manager-Tools

General configuration:
- configsm.yaml
In this yaml the SUSE Manager Server and the credentials have to be entered. Also the are more options:
- location of the log dirs
- Should a mail being send in case of an error and to whom
- information needed for SP migration for system update
- information needed for channel cloner script.


The following scripts are included:
- sync_channel.py
This will clone the give channel with the channel it is cloned from.

- sync_stage.py
This will clone the given basechannel and all its child channels from the channels they are cloned from. Or it will update the given environment in the given project.

- create_software_project.py
This will create a new software content lifecycle project. It can also be used to add or remove source channels from an existing project.

- system_update.py
This script will can perform several tasks:
* based on the settings in configsm.yaml it can do a Support Pack Migration
* it will apply the latest updates available in assigned channels to the server
* will apply configuration channels, if defined
* if updates are being applied it will reboot the server. This can be prevented with a parameter.

- group_system_update.py
This script will update all systems in the given system group.

- channel_cloner.py
The script will create cloned channels. This is based on the information stored in configsm.yaml

- cve_report.py
This script will report all systems with the given CVE(s)

Each script will have a --help to see all available parameters.

More documentation will follow............

How to use:
- The file configsm.yaml should be in the same directory as the scripts. And before using check the file and correct the information.
- Each script will have a help option: --help 

GNU Public License. No warranty. No Support 
For question/suggestions/bugs mail: michael.brookhuis@suse.com
Created by: SUSE Michael Brookhuis 2019



