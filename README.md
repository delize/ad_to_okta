# AD To Okta / AD2Okta
-----------------------

This script's primary function is to help ease the pain of migrating from/moving off of Active Directory as a Profile Master, to using a more Modern Profile Master such as an Human Resources Management System (HRMS), an External Identity Provider, or even using Okta as a Profile Master in a stand alone configuration. This ties back into a blog post that I wrote [located here](https://andrewdoering.org/blog/2020/08/08/transitioning-to-okta-from-active-directory-new-directory-service-infrastructure/).

Note: There is no support involved in this tool.

Note 2: An updated version (rewritten by ChatGPT) can be found under [optimizations branch](https://github.com/delize/ad_to_okta/blob/optimizations/ad-to-okta-migration.py). However, it has not been tested at all.

## Prerequisites

* Your Okta URL
* Super Admin in your Okta Tenant 
* Security Token/API Token in your Okta Tenant
* Python 3  (last confirmed working with 3.7.3)

## How to use

1. Clone the Github Repo into your favorite directory
 `git clone git@github.com:delize/ad_to_okta.git`
2. Run `python3 ad-to-okta-migration.py --help` to verify what arguments you want to run (or look below)
3. Run `python3 ad-to-okta-migration.py` with your list of arguments order to validate information
   **NOTE**: This will not execute or modify anything.
4. Once information is validated, run `python3 ad-to-okta-migration.py --execute` in preferably the following order:
    * Groups
    * Rules
    * Transitiongroups
    * Appmembershipgroup
    * Rmuseradd






--------------------

# Arguments

**-u, --url**
```
type=str,
default='company.okta.com'
help='Replace company with the name of your org'
```
**-t, --token**
```
type=str,
default='You did not submit a token'
help='API Token from Okta instance'
```
**--execute**
```
action='store_true'
help='Execute changes to Okta instance, Defaults to False'
```
**--groups**
```
action='store_true',
help='Creates Okta group from Active Directory Group, defaults to False'
```
**--rules**
```
action='store_true'
help='Create group rules to help with transitions - with a prefix of "API-AD2O", defaults to False'
```
**--transitiongroups**
```
action='store_true'
help='Activates and deactivates group rules to sync group members, defaults to False'
```
**--appmembershipgroup**
```
action='store_true',
help='Perform application membership group transition, defaults to False'
```
**--apppushgroup**
```
action='store_true',
help='Perform application push group transition using the private API/urls, defaults to False - not used yet, but for future use'
```
**--rmuserad**
```
action='store_true',
help='Remove user from Active Directory and reset password, be careful! '
```
**--comparegroups**
```
action='store_true',
help='Use this after creating okta groups, to compare the matched values. ')
```
**--users** 
```
action='store_true',
help='Display non-prettified list of users.'
```
**--activaterules**
```
action='store_true',
help='Use this after creating okta group rules, activates all rules starting with matching string "API-AD2O".'
```
**--deactivaterules**
```
action='store_true',
help='Use this after creating okta group rules, activates all rules starting with matching string "API-AD2O". '
```

# Where to find help
-------------

Feel free to raise an [issue](https://github.com/delize/ad_to_okta/issues) here on the repo.

Contact `@heimdall` on [MacAdmins Slack](https://www.macadmins.org/) or join the #okta channel.

-----

**Some future improvements that are planned**

* Add in app push groups (this will be officially unsupported as it uses Okta's private API which could change at any moment)
* Add an `--all` command, this previously existed but I removed it for the program to be more modular
* Always optimizations
