# JIRA Branch Checker

This script scans both local and remote git branches for JIRA ticket numbers (like TINY-1234), then checks the status of each ticket on JIRA and produces a formatted report.

## Requirements

- Python 3.6+
- `requests` library: `pip install requests`
- Git installed and in PATH
- Access to a JIRA instance

## Installation

1. Clone this repository or download the script
2. Make the script executable:
   ```
   chmod +x jira_branch_checker.py
   ```
3. Install dependencies:
   ```
   pip install requests
   ```

## Usage

Run the script in a Git repository:

```
./jira_branch_checker.py
```

By default, the script will:
1. Get all local and remote Git branches
2. Extract JIRA ticket numbers using regex pattern matching (e.g., PROJ-123)
3. Prompt for JIRA authentication (required for the default server)
4. Show progress while checking ticket statuses
5. Sort tickets by status alphabetically
6. Print a formatted report with ticket numbers, statuses, and links

### Command Line Options

| Option | Description |
|--------|-------------|
| `--username` | JIRA username/email |
| `--jira-url` | JIRA base URL (default: https://ephocks.atlassian.net) |
| `--no-auth` | Skip authentication (only for non-default JIRA servers) |
| `--clear-token` | Clear any saved token before running |
| `--format` | Output format: `table` (default) or `csv` |
| `--no-progress` | Disable the progress indicator |
| `--sort` | Sort by: `status` (default) or `ticket` |

### Authentication

Authentication is **required** for the default JIRA server (https://ephocks.atlassian.net). You can provide your JIRA username in advance:

```
./jira_branch_checker.py --username your.email@example.com
```

The first time you run the script, you'll be prompted for your JIRA API token. You'll then be asked if you want to save this token for future use. If you choose to save it, the token will be stored securely in:

```
~/.config/jira-branch-checker/tokens.ini
```

The configuration file is secured with user-only read permissions (600).

For subsequent runs, if you have a saved token, the script will automatically use it without prompting. The script will validate the token before using it and prompt for a new one if it's invalid.

#### Clearing Saved Tokens

If you need to clear a saved token (e.g., if it's expired or invalid), use the `--clear-token` flag:

```
./jira_branch_checker.py --clear-token
```

This will remove any saved token for the specified JIRA server before running.

### JIRA Instance URL

By default, the script uses `https://ephocks.atlassian.net` as the JIRA instance. You can specify a different URL:

```
./jira_branch_checker.py --jira-url https://your-instance.atlassian.net
```

### Skipping Authentication

For non-default JIRA servers that don't require authentication, you can use the `--no-auth` flag:

```
./jira_branch_checker.py --jira-url https://public-jira.example.com --no-auth
```

Note that this flag will be ignored for the default server, which always requires authentication.

### Progress Indicator

By default, the script displays a progress indicator that updates in-place while checking ticket statuses. If you prefer to disable this behavior (e.g., when redirecting output to a file), use the `--no-progress` flag:

```
./jira_branch_checker.py --no-progress
```

### Sorting Options

By default, tickets are sorted by status alphabetically. You can change the sorting to be by ticket number instead:

```
./jira_branch_checker.py --sort ticket
```

## Output Format

The script provides two output formats:

### Table Format (Default)

By default, the script outputs a nicely formatted table with proper column widths:

```
Ticket      Status        Link
--------    ----------    ----
PROJ-123    In Progress   https://ephocks.atlassian.net/browse/PROJ-123
PROJ-456    Done          https://ephocks.atlassian.net/browse/PROJ-456
```

### CSV Format

For machine-readable output or when you want to import the data into a spreadsheet, use the CSV format:

```
./jira_branch_checker.py --format csv
```

Example CSV output:
```
Ticket,Status,Link
PROJ-123,In Progress,https://ephocks.atlassian.net/browse/PROJ-123
PROJ-456,Done,https://ephocks.atlassian.net/browse/PROJ-456
```

## Troubleshooting

- **Error getting git branches**: Make sure you're running the script in a Git repository
- **Authentication errors**: Verify your JIRA username and API token. If using a saved token that's not working, run with `--clear-token` to remove it and enter a new one.
- **No tickets found**: The script might not recognize your ticket number format. Check the regex pattern in the code
- **Permission errors with token file**: The script tries to secure the token file with user-only permissions. If this fails, you might need to manually set the permissions: `chmod 600 ~/.config/jira-branch-checker/tokens.ini`
- **Blank token error**: The script prevents saving empty tokens. If you encounter this error, simply provide a valid token when prompted.

### Additional Features

- **Progress Indicator**: Shows real-time progress while checking ticket statuses
- **Token Storage**: Securely saves your authentication token (with permission)
- **Multiple Output Formats**: Choose between human-readable tables or machine-readable CSV
- **Graceful Interruption**: Safely cancel the script with Ctrl+C without stack traces
- **Flexible Sorting**: Sort results by ticket status or ticket number 