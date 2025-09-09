# TKO-Rolekeeper
A RedBot cog for the TKO Rolekeeper Discord bot

## Features

- **Role Chain Management**: Define hierarchical role chains where users automatically receive all lower roles when they get a higher role
- **Automatic Role Enforcement**: Listens for role updates and ensures users have all prerequisite roles in their chains
- **Audit Command**: Sweep through all server members to check and fix missing roles according to configured chains
- **Permission Checks**: Ensures the bot has proper permissions before attempting role modifications

## Installation

1. Add this repository to your Red Bot instance
2. Load the cog: `[p]load rolekeeper`

## Commands

### Role Chain Management
- `[p]rolechain add <chain_name> <role1> <role2> <role3> ...` - Create a new role chain (roles listed from lowest to highest)
- `[p]rolechain remove <chain_name>` - Remove a role chain
- `[p]rolechain list` - List all configured role chains

### Auditing
- `[p]roleaudit` - Audit all members and fix missing roles in chains
- `[p]rolecheck <member>` - Check a specific member's role status against all chains

## Example Usage

```
[p]rolechain add progression Member Regular Veteran Elite
[p]roleaudit
```

This creates a progression chain where:
- Users with "Regular" role automatically get "Member" role
- Users with "Veteran" role automatically get both "Member" and "Regular" roles  
- Users with "Elite" role automatically get "Member", "Regular", and "Veteran" roles

## Permissions

- Commands require `Manage Roles` permission or Administrator
- Bot needs `Manage Roles` permission and must be higher in role hierarchy than managed roles
