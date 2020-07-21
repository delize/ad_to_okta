#!/bin/python3

# Created by Andrew Doering
# Version 0.5 - 2020/03/25
# Needs optimizations and refinements. This code works (or at least worked for my company), but needs to be re-coded to be more appealing and less shitty.

#import python modules
import requests
import pandas as pd
import time
import json


# list variables
URL = ""
TOKEN = ""
HEADERS = {
    'Authorization': 'SSWS ' + TOKEN,
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# Okta's pagination sucks, excuse the mess of all this - it can be optimized.
def build_url_app_list(app_id=None):
    api = URL + '/api/v1/apps?limit=20&filter=status+eq+%22ACTIVE%22'
    if app_id:
        api += "&after={id}".format(id=app_id)
    return api

def applications_list(**kwargs):
    has_batch = True
    app_id = None
    application_list = []
    while has_batch:
        applications = requests.get(build_url_app_list(app_id), params=kwargs, headers=HEADERS).json()
        application_list = application_list + applications
        time.sleep(.2)
        if applications:
            app_id = applications[-1]["id"]
        else:
            has_batch = False
    return application_list

def get_users(**kwargs):
    return requests.get(URL + '/api/v1/users', params=kwargs, headers=HEADERS)

def get_user_pages(**kwargs):
    page = get_users(**kwargs)
    while page:
        yield page
        page = get_next_page(page.links)

def get_group_rules(**kwargs):
    return requests.get(URL + '/api/v1/groups/rules', params=kwargs, headers=HEADERS)

def get_group_rules_pages(**kwargs):
    page = get_group_rules(**kwargs)
    while page:
        yield page
        page = get_next_page(page.links)

def get_applications(**kwargs):
    return requests.get(URL + '/api/v1/apps', params=kwargs, headers=HEADERS)

def get_applications_pages(**kwargs):
    page = get_applications(**kwargs)
    while page:
        yield page
        page = get_next_page(page.links)

def get_next_page(links):
    next_page = links.get('next')
    if next_page:
        return requests.get(next_page['url'], headers=HEADERS)
    else:
        return None

def assign_group_to_application(application_id, group_id, profile, **kwargs):
    return requests.put(URL + '/api/v1/apps/'+application_id+'/groups/'+group_id, json=profile, headers=HEADERS)

def remove_user_from_app(application_id, user_id, **kwargs):
    return requests.delete(URL + '/api/v1/apps/'+application_id+'/users/'+user_id, params=kwargs, headers=HEADERS)

def get_groups_assigned_to_application(applicationid,**kwargs):
    """Get Okta groups. **kwargs: such as
    `q`, `filter`, `limit`, etc. see
    https://developer.okta.com/docs/reference/api/groups/#list-groups """
    return requests.get(URL + '/api/v1/apps/' + applicationid + '/groups',
    params=kwargs, headers=HEADERS).json()

def get_groups(**kwargs):
    """Get Okta groups.
    **kwargs: such as `q`, `filter`, `limit`, etc.
    see https://developer.okta.com/docs/reference/api/groups/#list-groups
    """
    return requests.get(URL + '/api/v1/groups', params=kwargs, headers=HEADERS)

def return_groups(app_filter):
    """Searches the groups pulled by the get_groups function, returns names"""
    groups = ""
    if app_filter == 'APP_GROUP' or app_filter == 'OKTA_GROUP':
        groups = get_groups(filter='type eq "'+ app_filter + '"').json()
    else:
        print("Not a valid group filter, must be APP_GROUP or OKTA_GROUP.")
    return groups

def return_ad_group_attributes():
    ad_groups = return_groups("APP_GROUP")
    if len(ad_groups) == 0:
        print('0 groups found.')
        return
    found_groups_attributes = []
    found_groups_id = []
    found_groups_desc = []
    found_groups_name = []
    for group in ad_groups:
        if 'windowsDomainQualifiedName' in group['profile']:
            found_groups_id.append(group['id'])
    for group in ad_groups:
        if 'windowsDomainQualifiedName' in group['profile']:
            found_groups_name.append(group['profile']['name'])
    for group in ad_groups:
        if 'windowsDomainQualifiedName' in group['profile']:
            found_groups_desc.append(group['profile']['description'])
    found_groups_attributes = list(zip(found_groups_name, found_groups_desc, found_groups_id))
    return found_groups_attributes

def return_okta_group_attributes():
    okta_groups = return_groups("OKTA_GROUP")
    if len(okta_groups) == 0:
        print('0 groups found.')
        return
    found_groups_attributes = []
    found_groups_id = []
    found_groups_desc = []
    found_groups_name = []
    for group in okta_groups:
        found_groups_id.append(group['id'])
        found_groups_name.append(group['profile']['name'])
        found_groups_desc.append(group['profile']['description'])
    found_groups_attributes = list(zip(found_groups_name, found_groups_desc, found_groups_id))
    return found_groups_attributes

def create_okta_groups():
    group_info = return_ad_group_attributes()
    for group_name, group_desc, group_id in group_info:
        group = {"profile": { "name": group_name, "description": "AD2OKTA-API - " + group_desc } }
        print(group)
        status = requests.post(URL + '/api/v1/groups', json=group, headers=HEADERS)
        if status.status_code == 200:
            print("Group " + group_name + " created. " + 'Success!')
        elif status.status_code == 400:
            print('Bad Request.')
        elif status.status_code == 401:
            print('Not Authorized.')
        elif status.status_code == 404:
            print('Not Found.')
        else:
            print('Something fucked up!')
    return status

# A lot of this duplicated, could be improved.
def create_dataframe():
    okta_dataframe = return_okta_group_attributes()
    ad_dataframe = return_ad_group_attributes()
    okta_dataset = pd.DataFrame(okta_dataframe, columns=['name', 'okta_desc', 'okta_id'])
    for data in okta_dataset['name']:
        okta_dataset['name'] = okta_dataset['name'].str.lower()
    ad_dataset = pd.DataFrame(ad_dataframe, columns=['name', 'ad_desc', 'ad_id'])
    for data in ad_dataset['name']:
        ad_dataset['name'] = ad_dataset['name'].str.lower()
    joined_dataframe = pd.merge(how='inner', on='name', left=ad_dataset, right=okta_dataset)
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
        print(rule_name)
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
        status = requests.post(URL + '/api/v1/groups/rules/', json=group_rule, headers=HEADERS)
        if status.status_code == 200:
            print("Group rule for " + group_name + " created. " + 'Success!')
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
    #list_of_rules = requests.get(URL + '/api/v1/groups/rules?search=' + "API-AD2O", params=kwargs, headers=HEADERS).json()

    for page in get_group_rules_pages(limit=200):
        for rule in page.json():
            if 'API-AD2O' in rule['name']:
                status = requests.post(URL + '/api/v1/groups/rules/' + rule['id'] + '/lifecycle/activate', params=kwargs, headers=HEADERS)
                # print("Rule Activation has started")
                if status.status_code == 200:
                    print("Action for " + rule['name'] +"/" + rule['id'] + " completed. " + 'Success!')
                    # if "b''" in status.content.decode():
                    #     print("API returned: " + status.content)
                    # else:
                    #     continue
                elif status.status_code == 204:
                    print("Not sure why, but, action for " + rule['name'] +" / ID: " + rule['id'] + " completed. " + 'Success!')
                    # print('HTTP Status Code: No content.')
                    # if "b''" in status.content.decode():
                    #     print("API returned: " + status.content)
                    # else:
                    #     continue
                elif status.status_code == 400:
                    print('HTTP Status Code: Bad Request.')
                    if "b''" in status.content.decode():
                        print("API returned: " + status.content)
                    else:
                        continue
                elif status.status_code == 401:
                    print('HTTP Status Code: Not Authorized.')
                    if "b''" in status.content.decode():
                        print("API returned: " + status.content)
                    else:
                        continue
                elif status.status_code == 403:
                    print('HTTP Status Code: Forbidden. Cause fuck you right?')
                    if "b''" in status.content.decode():
                        print("API returned: " + status.content)
                    else:
                        continue
                elif status.status_code == 404:
                    print('HTTP Status Code: Not Found.')
                    if "b''" in status.content.decode():
                        print("API returned: " + status.content)
                    else:
                        continue
                else:
                    print("API returned: " + status.content)
                    print('Something fucked up!')
                    continue
        else:
            print("No groups were returned with the proper prefix.")
            continue

def deactivate_rules(**kwargs):
   #list_of_rules = requests.get(URL + '/api/v1/groups/rules?search=' + "API-AD2O", params=kwargs, headers=HEADERS).json()

    for page in get_group_rules_pages(limit=200):
        for rule in page.json():
            if 'API-AD2O' in rule['name']:
                status = requests.post(URL + '/api/v1/groups/rules/' + rule['id'] + '/lifecycle/deactivate', params=kwargs, headers=HEADERS)
                
                if status.status_code == 200:
                    print("Action for " + rule['name'] +"/" + rule['id'] + " completed. " + 'Success!')
                    if "b''" in status.content.decode():
                        print(status.content)
                    else:
                        continue
                elif status.status_code == 204:
                    print("Not sure why, but, action for " + rule['name'] +"/" + rule['id'] + " completed. " + 'Success!')
                    print('No content.')
                    if "b''" in status.content.decode():
                        print(status.content)
                    else:
                        continue
                elif status.status_code == 400:
                    print('Bad Request.')
                    if "b''" in status.content.decode():
                        print(status.content)
                    else:
                        continue
                elif status.status_code == 401:
                    print('Not Authorized.')
                    if "b''" in status.content.decode():
                        print(status.content)
                    else:
                        continue
                elif status.status_code == 403:
                    print('Forbidden. Cause fuck you right?')
                    if "b''" in status.content.decode():
                        print(status.content)
                    else:
                        continue
                elif status.status_code == 404:
                    print('Not Found.')
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
    df = create_dataframe()
    application_info = []
    application_name = []
    for page in get_applications_pages(limit=200):
        for application in page.json():
            if application['name'] != 'active_directory':
                application_id = {"application_id": application['id']}
                application_info.append(application_id)
                application_name_1 = {"application_id": application['name']}
                application_name.append(application_name_1)
    print(application_info)
    print(application_name)

    for application_id in application_info:
        time.sleep(.2)
        assigned_groups = get_groups_assigned_to_application(application_id['application_id'])
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
            #df1 = []
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
                profile = profile_entry
                profile = json.dumps( {'profile': profile})
                profile = json.loads(profile)
                time.sleep(.2)
                status = assign_group_to_application(application_id, group_id, profile)
                print(F"Application ID: {application_id}, Group ID: {group_id}, Group Profile: {profile}, Status: {status}")

    return status

def disassociate_from_ad(**kwargs):
    list_applications = applications_list()
    application_info = []
    for application in list_applications:
        if application['name'] == 'active_directory':
            application_id = application['id']
    for page in get_user_pages(limit=200, filter=''):
        for user in page.json():
            print(F"Application ID: {application_id}, User ID: {user['id']}")
            status = remove_user_from_app(application_id, user['id'])
            print(status)
    return status

def reset_user_password(**kwargs):
    for page in get_user_pages(limit=200, filter=''):
        for user in page.json():
            response = requests.post(URL + '/api/v1/users/'+user['id']+'/lifecycle/reset_password?sendEmail=True', params=kwargs, headers=HEADERS)
    return response

print("Running code")
#create_okta_groups()
#create_group_rules()
#activate_rules()
#deactivate_rules()
#transition_application_groups()
#disassociate_from_ad()
#reset_user_password()
print("Code Finished")
