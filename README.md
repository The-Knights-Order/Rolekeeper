# TKO-Rolekeeper

A RedBot cog for the TKO Rolekeeper Discord bot

## Features

-   **Group Role Management**: Define groups, each with a group role and a list of member roles. When a user is given a member role, the bot ensures they also have the group role (but does not add or remove other roles).
-   **Automatic Group Role Enforcement**: Listens for role updates and ensures users with a member role in a group always have the group role.
-   **Audit Command**: Sweep through all server members to check and fix missing group roles according to configured groups.
-   **Admin-Only Commands**: All commands require administrator permissions.
-   **Permission Checks**: Ensures the bot has proper permissions before attempting role modifications.

## Installation

1. Add this repository to your Red Bot instance:
    ```
    [p]repo add tko-rolekeeper <repo_url>
    ```
    Replace `<repo_url>` with the actual URL of this repository.
2. Install the cog:
    ```
    [p]cog install tko-rolekeeper rolekeeper
    ```
3. Load the cog:
    ```
    [p]load rolekeeper
    ```

## Commands

All commands require administrator permissions.

### Group Management

-   `[p]group add <group_name> <group_role> <member_role1> <member_role2> ...` - Create a new group (first role is the group role, rest are member roles)
-   `[p]group remove <group_name>` - Remove a group
-   `[p]group list` - List all configured groups and their roles
-   `[p]addroletogroup <group_name> <role>` - Add a role to a group's member roles (if not already present)
-   `[p]deletegroup <group_name>` - Delete a group outright
-   `[p]listgroups` - List all groups and their roles

### Auditing

-   `[p]groupaudit` - Audit all members and fix missing group roles
-   `[p]groupcheck <member>` - Check a specific member's group role status

## Example Usage

```
[p]group add Council Council Advisor Officer
[p]addroletogroup Council SeniorAdvisor
[p]groupaudit
```

This creates a group called "Council" with "Council" as the group role and "Advisor" and "Officer" as member roles. If a user is given "Advisor", the bot ensures they also have the "Council" role.

## Permissions

-   All commands require Administrator permissions
-   Bot needs `Manage Roles` permission and must be higher in role hierarchy than managed roles
