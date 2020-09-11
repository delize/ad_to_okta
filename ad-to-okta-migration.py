#!/bin/python3

# Created by Andrew Doering
# Version 0.7 - 2020 / 08/ 17
# Thank you Gabriel Sroka, Greg Neagle, and other MacAdmins users.

import requests
import pandas as pd
import time
import json
import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process user input for Active Directory to Okta transition")
    parser.add_argument('-u', '--url', type=str,
                        default='company.okta.com',
                        help='Replace company with the name of your org')
    parser.add_argument('-t', '--token', type=str,
                        default='You did not submit a token',
                        help='API Token from Okta instance')
    parser.add_argument('--execute', action='store_true',
                        help='Execute changes to Okta instance, Defaults to False')
    parser.add_argument('--groups', action='store_true',
                        help='Creates Okta group from Active Directory Group, defaults to False')
    parser.add_argument('--rules', action='store_true',
                        help='Create group rules to help with transitions - with a prefix of "API-AD2O", defaults to False')
    parser.add_argument('--transitiongroups', action='store_true',
                        help='Activates and deactivates group rules to sync group members, defaults to False')
    parser.add_argument('--appmembershipgroup', action='store_true',
                        help='Perform application membership group transition, defaults to False')
    parser.add_argument('--apppushgroup', action='store_true',
                        help='Perform application push group transition using the private API/urls, defaults to False - not used yet, but for future use')
    parser.add_argument('--rmuserad', action='store_true',
                        help='Remove user from Active Directory and reset password, be careful! ')
    parser.add_argument('--comparegroups', action='store_true',
                        help='Use this after creating okta groups, to compare the matched values. ')
    parser.add_argument('--users', action='store_true',
                        help='Display non-prettified list of users. ')
    parser.add_argument('--activaterules', action='store_true',
                        help='Use this after creating okta group rules, activates all rules starting with matching string "API-AD2O". ')
    parser.add_argument('--deactivaterules', action='store_true',
                        help='Use this after creating okta group rules, activates all rules starting with matching string "API-AD2O". ')
    args = parser.parse_args()
    return (args.url, args.token, args.execute, args.groups, args.rules, args.transitiongroups, args.appmembershipgroup, args.apppushgroup, args.rmuserad, args.comparegroups, args.users, args.activaterules, args.deactivaterules)


def request_get(url, **kwargs):
    response = requests.get(url, params=kwargs, headers=HEADERS)
    response_data = response.json()
    while response.links.get('next'):
        links = response.links['next']['url']
        response = requests.get(links, headers=HEADERS)
        response_data += response.json()
    return response_data
    # while response:
    #     yield page
    #     page = get_next_page(page.links)
    

#Shortened function


def get_okta_users(url, **kwargs):
    url = f'https://{url}/api/v1/users'
    return request_get(url, **kwargs)


def get_okta_groups(url, **kwargs):
    url = f'https://{url}/api/v1/groups'
    return request_get(url, **kwargs)


def get_application_list(url, **kwargs):
    url = f'https://{url}/api/v1/apps?filter=status+eq+%22ACTIVE%22'
    return request_get(url, **kwargs)


def get_group_rules(url, **kwargs):
    print("Get Group Membership Rules")
    url = f'https://{url}/api/v1/groups/rules'
    return request_get(url, **kwargs)


def assign_group_to_application(application_id, group_id, profile, **kwargs):
    return requests.put(f'https://{url}/api/v1/apps/{application_id}/groups/{group_id}', json=profile, headers=HEADERS)


def get_groups_assigned_to_application(applicationid, **kwargs):
    r = requests.get(
        f'https://{url}/api/v1/apps/{applicationid}/groups', params=kwargs, headers=HEADERS)
    return r.json()


def remove_user_from_app(application_id, user_id, **kwargs):
    return requests.delete(f'https://{url}/api/v1/apps/{application_id}/users/{user_id}', params=kwargs, headers=HEADERS)


def return_groups(app_filter):
    """Searches the groups pulled by the get_groups function, returns names"""
    groups = ""
    if app_filter == 'APP_GROUP' or app_filter == 'OKTA_GROUP':
        groups = get_okta_groups(url, filter='type eq "' + app_filter + '"')
        #print(groups)
    else:
        print("Not a valid group filter, must be APP_GROUP or OKTA_GROUP.")
    return groups


def return_ad_group_attributes():
    ad_groups = return_groups("APP_GROUP")
    if len(ad_groups) == 0:
        print('0 groups found.')
        return
    found_groups_attributes, found_groups_id, found_groups_desc, found_groups_name = ([] for i in range(4))
    for group in ad_groups:
        if 'windowsDomainQualifiedName' in group['profile']:
            found_groups_id.append(group['id'])
        if 'windowsDomainQualifiedName' in group['profile']:
            found_groups_name.append(group['profile']['name'])
        if 'windowsDomainQualifiedName' in group['profile']:
            found_groups_desc.append(group['profile']['description'])
    found_groups_attributes = list(zip(found_groups_name, found_groups_desc, found_groups_id))
    return found_groups_attributes


def return_okta_group_attributes():
    okta_groups = return_groups("OKTA_GROUP")
    if len(okta_groups) == 0:
        print('0 groups found.')
        return
    found_groups_attributes, found_groups_id, found_groups_desc, found_groups_name = (
        [] for i in range(4))
    for group in okta_groups:
        found_groups_id.append(group['id'])
        found_groups_name.append(group['profile']['name'])
        found_groups_desc.append(group['profile']['description'])
    found_groups_attributes = list(
        zip(found_groups_name, found_groups_desc, found_groups_id))
    return found_groups_attributes


def create_okta_groups():
    group_info = return_ad_group_attributes()
    for group_name, group_desc, group_id in group_info:
        group = {"profile": {"name": group_name,
                             "description": "AD2OKTA-API - " + group_desc}}
        status = requests.post(f"https://{url}/api/v1/groups",
                               json=group, headers=HEADERS)
        if status.status_code == 200:
            print(f"Group {group_name} created. Success!")
        elif status.status_code == 400:
            print(f"Group {group_name} already exists. Bad Request.")
        elif status.status_code == 401:
            print('Not Authorized.')
        elif status.status_code == 404:
            print('Not Found.')
        else:
            print('Something fucked up!')
    return status

def create_dataframe():
    pd.options.display.width = 0
    okta_dataframe = return_okta_group_attributes()
    ad_dataframe = return_ad_group_attributes()
    okta_dataset = pd.DataFrame(okta_dataframe, columns=[
                                'name', 'okta_desc', 'okta_id'])
    for data in okta_dataset['name']:
        okta_dataset['name'] = okta_dataset['name'].str.lower()
    ad_dataset = pd.DataFrame(ad_dataframe, columns=[
                              'name', 'ad_desc', 'ad_id'])
    for data in ad_dataset['name']:
        ad_dataset['name'] = ad_dataset['name'].str.lower()
    joined_dataframe = pd.merge(
        how='inner', on='name', left=ad_dataset, right=okta_dataset)
    return joined_dataframe


def create_tuple_from_dataframe():
    joined_dataframe = create_dataframe()
    group_name = (joined_dataframe["name"].tolist())
    ad_id = (joined_dataframe["ad_id"].tolist())
    okta_id = (joined_dataframe["okta_id"].tolist())
    joined_tuple = list(zip(group_name, ad_id, okta_id))
    return joined_tuple


def create_group_rules():
    okta_tuple = create_tuple_from_dataframe()
    for group_name, oldgroupid, newgroupid in okta_tuple:
        ## TODO: Make rule prefix, a variable input
        rule_name = "API-AD2O" + " " + group_name
        group_rule = group_rule = {
            'type': 'group_rule',
            'name': rule_name,
            'conditions': {
                'expression': {
                    'value': f"isMemberOfAnyGroup('{oldgroupid}')",
                    'type': 'urn:okta:expression:1.0'
                }
            },
            'actions': {
                'assignUserToGroups': {
                    'groupIds': [
                        newgroupid
                    ]
                }
            }
        }
        status = requests.post(f"https://{url}/api/v1/groups/rules/",
                               json=group_rule, headers=HEADERS)
        if status.status_code == 200:
            print(f"Group rule for {group_name} created. Success!")
        elif status.status_code == 400:
            print('Bad Request.')
        elif status.status_code == 401:
            print('Not Authorized.')
        elif status.status_code == 404:
            print('Not Found.')
        else:
            print(requests.content)
            print('Something fucked up!')
    return status


def activate_rules(**kwargs):
    for rule in get_group_rules(url):
        if 'API-AD2O' in rule['name']:
            status = requests.post(
                f'https://{url}/api/v1/groups/rules/{rule["id"]}/lifecycle/activate', params=kwargs, headers=HEADERS)
            if status.status_code == 200:
                print(
                    f"Action for{rule['name']} / {rule['id']} completed. Success!")
                if "b''" in status.content.decode():
                    print(status.content)
                else:
                    continue
            elif status.status_code == 204:
                print(
                    f"Not sure why, but, action for {rule['name']} / {rule['id']}completed. Success!")
                if "b''" in status.content.decode():
                    print(status.content)
                else:
                    continue
            else:
                print(status.content)
                print('Something fucked up!')
                continue
        else:
            print("No groups were returned with the proper prefix.")
            continue


def deactivate_rules(**kwargs):
    for rule in get_group_rules(url):
        if 'API-AD2O' in rule['name']:
            status = requests.post(f"https://{url}/api/v1/groups/rules/{rule['id']}/lifecycle/deactivate", params=kwargs, headers=HEADERS)
            if status.status_code == 200:
                print(f"Action for{rule['name']} / {rule['id']} completed. Success!")
                if "b''" in status.content.decode():
                    print(status.content)
                else:
                    continue
            elif status.status_code == 204:
                print(f"Not sure why, but, action for {rule['name']} / {rule['id']}completed. Success!")
                if "b''" in status.content.decode():
                    print(status.content)
                else:
                    continue
            else:
                print(status.content)
                print('Something fucked up!')
                continue
        else:
            print("No groups were returned with the proper prefix.")
            continue

def transition_application_groups(**kargs):
    #    The logic here is that we are need to collect the list of all applications, and for each application print the name so you know the application Id associated with the application name.
    df = create_dataframe()
    application_info = []
    application_name = []
    for application in get_application_list(url):
        if application['name'] != 'active_directory':
            application_id = {"application_id": application['id']}
            application_info.append(application_id)
            application_name_1 = {"application_name": application['name']}
            application_name.append(application_name_1)
    # print(application_info, application_name)
    
    for application_id in application_info:
        time.sleep(.3)
        assigned_groups = get_groups_assigned_to_application(application_id['application_id'])
        print(type(assigned_groups))
        print(assigned_groups)
        group_ids = []
        group_profile = []
        for group in assigned_groups:
            application_id["group_ids"] = group_ids
            group_ids.append(group['id'])
            application_id["group_profile"] = group_profile
            group_profile.append(group['profile'])
    df = df.set_index(['ad_id'])
    pd.set_option('display.max_rows', None)
    for item in application_info:
        df1 = []
        if 'group_ids' in item:
            for assignedgroup in item['group_ids']:
                try:
                    oktaidarray = df.loc[assignedgroup, 'okta_id']
                    df1.append(oktaidarray)
                except KeyError:
                    pass
        if len(df1) != 0:
            item['group_ids'] = df1

    for item in application_info:
        application_id = item['application_id']
        if 'group_ids' in item:
            for group_entry, profile_entry in zip(item['group_ids'], item['group_profile']):
                group_id = group_entry
                print(f"Group ID: {group_id}")
                profile = profile_entry
                print(f"Profile Entry: {profile}")
                profile = json.dumps({'profile': profile})
                print(f"Profile Json Dumps{profile}")
                profile = json.loads(profile)
                print(f"Profile Json Loads{profile}")
                time.sleep(.3)
                status = assign_group_to_application(
                    application_id, group_id, profile)
                print(
                    f"Application ID: {application_id}, Group ID: {group_id}, Group Profile: {profile}, Status: {status}")

    return status


def disassociate_from_ad(**kwargs):
    list_applications = get_application_list(url)
    application_info = []
    for application in list_applications:
        if application['name'] == 'active_directory':
            application_id = application['id']
    for user in get_okta_users(url):
        print(f"Application ID: {application_id}, User ID: {user['id']}")
        status = remove_user_from_app(application_id, user['id'])
        print(status)
    return status


def reset_user_password(**kwargs):
    for user in get_okta_users(url):
        response = requests.post(f"https://{url}/api/v1/users/{user['id']}/lifecycle/reset_password?sendEmail=True", params=kwargs, headers=HEADERS)
    return response


if __name__ == '__main__':
    (url, token, execute, groups, rules, transitiongroups,
     appmembershipgroup, apppushgroup, rmuserad, comparegroups, users, activaterules, deactivaterules) = parse_args()

    HEADERS = {
        'Authorization': 'SSWS ' + token,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    if execute == False:
        print("Not changing Okta instance, only outputting information")
        if users:
            print("Printing User List:")
            print(get_okta_users(url))
        if groups:
            print("Print AD Groups:")
            print(return_ad_group_attributes())
            print("Print Okta Groups:")
            print(return_okta_group_attributes())
        if transitiongroups:
            print("Print group rules:")
            print(get_group_rules(url))
        if comparegroups:
            print("Comparing AD and Okta Group Alignment:")
            print(create_dataframe())
            print(create_tuple_from_dataframe())
        sys.exit(0)
    elif execute == True:
        print(f"Executing changes in your Okta instance {url}. Be sure you have done a dry run first, and compared changes. This only makes changes to the arguments you specifically want to execute. Waiting three seconds before executing changes")
        time.sleep(3)
        if groups:
            create_okta_groups()
        if rules:
            create_group_rules()
        if transitiongroups:
            activate_rules()
            deactivate_rules()
        if activaterules:
            activate_rules()
        if deactivaterules:
            deactivate_rules()    
        if appmembershipgroup:
            transition_application_groups()
        if apppushgroup:
            print("Haha funny, this does not exist yet ;)")
        if rmuserad:
            print("This is a breaking change, and you specified to remove all users from Active Directory and wipe out their password. Waiting ten seconds to confirm you wanted to make this change!")
            time.sleep(10)
            disassociate_from_ad()
            reset_user_password()
        print(
            f"Changes have been executed against {url}, please validate changes that have been displayed and correct where necessary.")
        sys.exit(0)
    else:
        print("Incorrect value specified")
        sys.exit(1)
