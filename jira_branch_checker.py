#!/usr/bin/env python3

import subprocess
import re
import sys
import requests
from getpass import getpass
import argparse
from urllib.parse import quote
import os
import json
import configparser

# Configuration paths
CONFIG_DIR = os.path.expanduser("~/.config/jira-branch-checker")
TOKEN_FILE = os.path.join(CONFIG_DIR, "tokens.ini")

def get_git_branches():
    """Get all local and remote git branches"""
    branches = []
    
    try:
        # Get local branches
        local_result = subprocess.run(
            ['git', 'branch'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        local_branches = [branch.strip() for branch in local_result.stdout.split('\n') if branch]
        # Remove the asterisk from the current branch
        local_branches = [branch[2:] if branch.startswith('* ') else branch for branch in local_branches]
        branches.extend(local_branches)
        
        # Get remote branches
        remote_result = subprocess.run(
            ['git', 'branch', '-r'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        remote_branches = [branch.strip() for branch in remote_result.stdout.split('\n') if branch]
        # Clean up remote branch names (usually in the format 'origin/branch-name')
        remote_branches = [branch for branch in remote_branches if '->' not in branch]  # Filter out HEAD refs
        branches.extend(remote_branches)
        
        return branches
    except subprocess.CalledProcessError as e:
        print(f"Error getting git branches: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def extract_jira_tickets(branches):
    """Extract JIRA ticket numbers from branch names"""
    # Looking for patterns like PROJ-123 or ABC-456
    ticket_pattern = re.compile(r'([A-Z]+-\d+)')
    tickets = set()
    
    for branch in branches:
        matches = ticket_pattern.findall(branch)
        tickets.update(matches)
    
    return sorted(list(tickets))

def get_jira_status(ticket, jira_base_url, auth=None):
    """Get the status and resolution of a JIRA ticket"""
    url = f"{jira_base_url}/rest/api/2/issue/{quote(ticket)}"
    
    if auth is None and jira_base_url == "https://ephocks.atlassian.net":
        print("Error: Authentication is required for the default JIRA server", file=sys.stderr)
        sys.exit(1)
    
    try:
        response = requests.get(url, auth=auth)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('fields', {}).get('status', {}).get('name', 'Unknown')
            
            # Check if there's a resolution
            resolution = data.get('fields', {}).get('resolution', {})
            resolution_name = resolution.get('name') if resolution else None
            
            # If we have a resolution, include it with the status
            if resolution_name:
                return f"{status}: {resolution_name}"
            else:
                return status
        elif response.status_code == 401:
            print(f"Error: Authentication failed for {jira_base_url}", file=sys.stderr)
            sys.exit(1)
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def save_token(jira_url, username, token):
    """Save JIRA API token to configuration file"""
    # Create config directory if it doesn't exist
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    config = configparser.ConfigParser()
    
    # Load existing config if it exists
    if os.path.exists(TOKEN_FILE):
        config.read(TOKEN_FILE)
    
    # Get domain from URL for the section name
    # This simplifies by just using the full URL as the section name
    if not config.has_section(jira_url):
        config.add_section(jira_url)
    
    config[jira_url]['username'] = username
    config[jira_url]['token'] = token
    
    # Save the config
    with open(TOKEN_FILE, 'w') as configfile:
        config.write(configfile)
    
    # Set appropriate permissions (readable only by the user)
    os.chmod(TOKEN_FILE, 0o600)

def load_token(jira_url):
    """Load JIRA API token from configuration file"""
    if not os.path.exists(TOKEN_FILE):
        return None, None
    
    config = configparser.ConfigParser()
    config.read(TOKEN_FILE)
    
    if jira_url in config:
        username = config[jira_url].get('username')
        token = config[jira_url].get('token')
        return username, token
    
    return None, None

def get_auth_credentials(jira_url, provided_username=None):
    """Get authentication credentials for JIRA"""
    # Try to load saved credentials first
    saved_username, saved_token = load_token(jira_url)
    
    username = provided_username or saved_username
    token = None
    
    # If we have a saved token and either no username was provided or the provided username matches
    if saved_token and (not provided_username or provided_username == saved_username):
        print(f"Using saved credentials for {username} at {jira_url}")
        token = saved_token
        
        # Validate the token by making a test API call
        test_auth = (username, token)
        try:
            test_url = f"{jira_url}/rest/api/2/myself"
            response = requests.get(test_url, auth=test_auth, timeout=10)
            if response.status_code != 200:
                print("Saved token appears to be invalid. Please enter a new one.")
                token = None  # Force new token entry
        except Exception as e:
            print(f"Error testing saved token: {str(e)}")
            token = None  # Force new token entry
    
    # If no valid token, prompt for one
    if not token:
        # If no username provided and no saved username, prompt for username
        if not username:
            username = input(f"Enter your JIRA username for {jira_url}: ")
            if not username.strip():
                print("Error: Username cannot be empty")
                return None
        
        # Prompt for token
        token = getpass(f"Enter your JIRA API token for {username}: ")
        
        # Validate token is not empty
        if not token.strip():
            print("Error: Token cannot be empty")
            return None
            
        # Ask if user wants to save the token
        save_choice = input("Save this token for future use? (y/n): ").lower()
        if save_choice == 'y':
            save_token(jira_url, username, token)
            print(f"Token saved to {TOKEN_FILE}")
    
    return (username, token) if username and token else None

def clear_saved_token(jira_url):
    """Remove saved token for a specific JIRA URL"""
    if not os.path.exists(TOKEN_FILE):
        return
    
    config = configparser.ConfigParser()
    config.read(TOKEN_FILE)
    
    if jira_url in config:
        config.remove_section(jira_url)
        
        with open(TOKEN_FILE, 'w') as configfile:
            config.write(configfile)
        
        print(f"Cleared saved token for {jira_url}")

def main():
    parser = argparse.ArgumentParser(description='Check JIRA tickets in git branches')
    parser.add_argument('--username', help='JIRA username/email')
    parser.add_argument('--jira-url', default='https://ephocks.atlassian.net', help='JIRA base URL')
    parser.add_argument('--no-auth', action='store_true', help='Skip authentication (only for non-default JIRA servers)')
    parser.add_argument('--clear-token', action='store_true', help='Clear any saved token before running')
    parser.add_argument('--format', choices=['table', 'csv'], default='table', help='Output format (table or csv)')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress indicator')
    parser.add_argument('--sort', choices=['status', 'ticket'], default='status', help='Sort results by status (default) or ticket number')
    args = parser.parse_args()
    
    try:
        # Clear saved token if requested
        if args.clear_token:
            clear_saved_token(args.jira_url)
        
        # Get git branches
        branches = get_git_branches()
        
        # Extract JIRA tickets
        tickets = extract_jira_tickets(branches)
        
        if not tickets:
            print("No JIRA tickets found in branch names.")
            return
        
        # Authenticate with JIRA
        auth = None
        max_auth_attempts = 3
        current_attempt = 0
        
        while auth is None and current_attempt < max_auth_attempts:
            if not args.no_auth or args.jira_url == 'https://ephocks.atlassian.net':
                if current_attempt > 0:
                    print(f"Authentication attempt {current_attempt+1}/{max_auth_attempts}")
                
                auth = get_auth_credentials(args.jira_url, args.username)
                
                if not auth and args.jira_url == 'https://ephocks.atlassian.net':
                    if current_attempt == max_auth_attempts - 1:
                        print("Error: Authentication is required for the default JIRA server", file=sys.stderr)
                        sys.exit(1)
                elif auth:
                    break  # Successfully authenticated
                    
                current_attempt += 1
            else:
                break  # No auth required, exit the loop

        # Collect ticket data with progress indicator
        ticket_data = []
        total_tickets = len(tickets)
        
        print("Checking ticket statuses...")
        for idx, ticket in enumerate(tickets):
            # Update progress indicator (if not disabled)
            if not args.no_progress:
                progress = f"[{idx+1}/{total_tickets}] Checking {ticket}..."
                # Use carriage return (\r) to update in-place
                print(f"\r{progress}", end="", flush=True)
            
            status = get_jira_status(ticket, args.jira_url, auth)
            link = f"{args.jira_url}/browse/{ticket}"
            ticket_data.append((ticket, status, link))
        
        # Clear the progress line
        if not args.no_progress and total_tickets > 0:
            print("\r" + " " * 50 + "\r", end="", flush=True)
        
        # Sort the ticket data
        if args.sort == 'status':
            # Sort by status (alphabetically)
            ticket_data.sort(key=lambda x: x[1].lower())
        else:
            # Sort by ticket number
            ticket_data.sort(key=lambda x: x[0])
        
        # Output in the requested format
        if args.format == 'csv':
            # CSV format (good for machine processing)
            print("Ticket,Status,Link")
            for ticket, status, link in ticket_data:
                print(f"{ticket},{status},{link}")
        else:
            # Table format (good for human readability)
            # Find the maximum width of each column for proper alignment
            max_ticket_len = max(len("Ticket"), max(len(t[0]) for t in ticket_data))
            max_status_len = max(len("Status"), max(len(t[1]) for t in ticket_data))
            
            # Print header with proper alignment
            print(f"{'Ticket':{max_ticket_len}}  {'Status':{max_status_len}}  {'Link'}")
            print(f"{'-' * max_ticket_len}  {'-' * max_status_len}  {'-' * 4}")
            
            # Print each ticket with proper alignment
            for ticket, status, link in ticket_data:
                print(f"{ticket:{max_ticket_len}}  {status:{max_status_len}}  {link}")
    
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\n\nOperation cancelled by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        # Handle other exceptions
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 