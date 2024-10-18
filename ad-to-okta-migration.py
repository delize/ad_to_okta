#!/bin/python3

# Created by Andrew Doering
# Version 1.0 - Updated for 2024

import requests
import pandas as pd
import time
import json
import argparse
import sys

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process user input for Active Directory to Okta transition")
    
    parser.add_argument('-u', '--url', type=str, required=True, 
                        help='Replace company with the name of your org')
    parser.add_argument('-t', '--token', type=str, required=True, 
                        help='API Token from Okta instance')
    
    parser.add_argument('--execute', action='store_true', help='Execute changes to Okta instance')
    parser.add_argument('--groups', action='store_true', help='Creates Okta group from Active Directory Group')
    parser.add_argument('--rules', action='store_true', help='Create group rules for transition with prefix "API-AD2O"')
    parser.add_argument('--transitiongroups', action='store_true', help='Sync group members during transition')
    parser.add_argument('--appmembershipgroup', action='store_true', help='Application membership group transition')
    parser.add_argument('--apppushgroup', action='store_true', help='Application push group transition (future use)')
    parser.add_argument('--rmuserad', action='store_true', help='Remove user from Active Directory and reset password')
    parser.add_argument('--comparegroups', action='store_true', help='Compare created Okta and AD groups')
    parser.add_argument('--users', action='store_true', help='Display non-prettified list of users')
    parser.add_argument('--activaterules', action='store_true', help='Activate group rules starting with "API-AD2O"')
    parser.add_argument('--deactivaterules', action='store_true', help='Deactivate group rules starting with "API-AD2O"')
    
    return parser.parse_args()

def request_get(url, headers, **kwargs):
    """Handles paginated API requests."""
    response = requests.get(url, params=kwargs, headers=headers)
    response.raise_for_status()  # Raise an error for failed requests
    response_data = response.json()

    # Handle pagination
    while 'next' in response.links:
        next_url = response.links['next']['url']
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        response_data.extend(response.json())  # Append paginated data
    
    return response_data

def get_okta_users(url, headers):
    """Fetch Okta users."""
    return request_get(f'https://{url}/api/v1/users', headers)

def get_okta_groups(url, headers):
    """Fetch Okta groups."""
    return request_get(f'https://{url}/api/v1/groups', headers)

def get_application_list(url, headers):
    """Fetch a list of active Okta applications."""
    return request_get(f'https://{url}/api/v1/apps?filter=status eq "ACTIVE"', headers)

def get_group_rules(url, headers):
    """Fetch group membership rules."""
    return request_get(f'https://{url}/api/v1/groups/rules', headers)

def assign_group_to_application(url, application_id, group_id, profile, headers):
    """Assign a group to an application."""
    response = requests.put(f'https://{url}/api/v1/apps/{application_id}/groups/{group_id}', 
                            json=profile, headers=headers)
    response.raise_for_status()
    return response

def remove_user_from_app(url, application_id, user_id, headers):
    """Remove a user from an application."""
    response = requests.delete(f'https://{url}/api/v1/apps/{application_id}/users/{user_id}', 
                               headers=headers)
    response.raise_for_status()
    return response

def create_okta_groups(url, headers, group_info):
    """Create Okta groups from AD group information."""
    for group_name, group_desc, _ in group_info:
        group_payload = {"profile": {"name": group_name, "description": f"AD2OKTA-API - {group_desc}"}}
        response = requests.post(f"https://{url}/api/v1/groups", json=group_payload, headers=headers)
        
        if response.status_code == 200:
            print(f"Group {group_name} created successfully.")
        elif response.status_code == 400:
            print(f"Group {group_name} already exists.")
        else:
            print(f"Error creating group {group_name}: {response.text}")

def create_dataframe(ad_groups, okta_groups):
    """Create a dataframe for group comparison."""
    pd.options.display.width = 0  # Auto-adjust dataframe width
    
    ad_df = pd.DataFrame(ad_groups, columns=['name', 'ad_desc', 'ad_id']).applymap(lambda x: x.lower() if isinstance(x, str) else x)
    okta_df = pd.DataFrame(okta_groups, columns=['name', 'okta_desc', 'okta_id']).applymap(lambda x: x.lower() if isinstance(x, str) else x)
    
    merged_df = pd.merge(ad_df, okta_df, on='name', how='inner')
    return merged_df

def main():
    args = parse_args()
    headers = {
        'Authorization': f'SSWS {args.token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    if not args.execute:
        print("Dry run mode - No changes will be made to the Okta instance.")
        
        if args.users:
            print("Fetching Okta users...")
            users = get_okta_users(args.url, headers)
            print(users)

        if args.groups:
            print("Fetching AD and Okta groups...")
            ad_groups = return_ad_group_attributes()
            okta_groups = return_okta_group_attributes()
            print("AD Groups:", ad_groups)
            print("Okta Groups:", okta_groups)

        if args.comparegroups:
            print("Comparing AD and Okta groups...")
            ad_groups = return_ad_group_attributes()
            okta_groups = return_okta_group_attributes()
            comparison_df = create_dataframe(ad_groups, okta_groups)
            print(comparison_df)

        sys.exit(0)

    if args.execute:
        print(f"Executing changes in Okta instance at {args.url}")
        time.sleep(3)  # Short pause before execution

        if args.groups:
            ad_groups = return_ad_group_attributes()
            create_okta_groups(args.url, headers, ad_groups)

        if args.rules:
            create_group_rules(args.url, headers)

        if args.transitiongroups:
            activate_rules(args.url, headers)
            deactivate_rules(args.url, headers)

        if args.activaterules:
            activate_rules(args.url, headers)

        if args.deactivaterules:
            deactivate_rules(args.url, headers)

        if args.rmuserad:
            disassociate_from_ad(args.url, headers)
            reset_user_password(args.url, headers)

        print("Execution complete.")
    else:
        print("Invalid argument combination.")
        sys.exit(1)

if __name__ == '__main__':
    main()
