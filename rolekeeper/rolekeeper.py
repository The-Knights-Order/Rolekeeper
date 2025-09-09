import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from typing import List, Optional
import logging

log = logging.getLogger("red.rolekeeper")


class RoleKeeper(commands.Cog):
    """
    A cog that maintains group-based role hierarchies.

    When a user is given a role within a group, they receive the group role (not all lower roles).
    """

    def __init__(self, bot: Red):
        self.bot = bot  # Reference to the Red bot instance
        # Set up persistent config for this cog, unique identifier
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)

        # Guild-specific config for groups
        # Each group: {group_name: {"group_role": role_id, "member_roles": [role_id1, ...]}}
        default_guild = {
            "groups": {}
        }
        self.config.register_guild(**default_guild)
    

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def group(self, ctx):
        """
        Command group for managing role groups.
        Usage: [p]group <subcommand>
        """
        pass
    @commands.command(name="listgroups")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def listgroups(self, ctx):
        """
        List all groups and their roles.
        """
        groups = await self.config.guild(ctx.guild).groups()
        if not groups:
            await ctx.send("No groups configured for this server.")
            return
        embed = discord.Embed(title="Groups and Roles", color=discord.Color.purple())
        for group_name, data in groups.items():
            group_role = ctx.guild.get_role(data["group_role"])
            member_roles = [ctx.guild.get_role(rid) for rid in data["member_roles"]]
            group_role_name = group_role.name if group_role else f"<Deleted Role: {data['group_role']}>"
            member_role_names = [r.name if r else f"<Deleted Role: {rid}>" for r, rid in zip(member_roles, data["member_roles"])]
            embed.add_field(
                name=group_name,
                value=f"Group Role: {group_role_name}\nMembers: {' -> '.join(member_role_names)}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="addroletogroup")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def addroletogroup(self, ctx, group_name: str, role: discord.Role):
        """
        Add a role to a group's member roles (appends if not duplicate).
        """
        async with self.config.guild(ctx.guild).groups() as groups:
            if group_name not in groups:
                await ctx.send(f"Group '{group_name}' not found.")
                return
            if role.id in groups[group_name]["member_roles"]:
                await ctx.send(f"Role '{role.name}' is already in group '{group_name}'.")
                return
            groups[group_name]["member_roles"].append(role.id)
            await ctx.send(f"Role '{role.name}' added to group '{group_name}'.")

    @commands.command(name="deletegroup")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def deletegroup(self, ctx, group_name: str):
        """
        Delete a group outright.
        """
        async with self.config.guild(ctx.guild).groups() as groups:
            if group_name in groups:
                del groups[group_name]
                await ctx.send(f"Group '{group_name}' deleted.")
            else:
                await ctx.send(f"Group '{group_name}' not found.")
    

    @group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def group_add(self, ctx, group_name: str, group_role: discord.Role, *member_roles: discord.Role):
        """
        Add a new group.

        Example: `[p]group add Knight KnightRole Squire Page`
        The first role is the group role, followed by member roles (from lowest to highest).
        """
        # Must specify at least one member role
        if not member_roles:
            await ctx.send("You must specify at least one member role (after the group role).")
            return

        # Check if bot can manage all specified roles
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if not bot_member:
            await ctx.send("Could not find bot member in guild.")
            return

        all_roles = [group_role] + list(member_roles)
        # Only roles below the bot's top role can be managed
        unmanageable_roles = [role.name for role in all_roles if role >= bot_member.top_role]
        if unmanageable_roles:
            await ctx.send(f"I cannot manage these roles (they are above my highest role): {', '.join(unmanageable_roles)}")
            return

        # Save group config to persistent storage
        async with self.config.guild(ctx.guild).groups() as groups:
            groups[group_name] = {
                "group_role": group_role.id,
                "member_roles": [role.id for role in member_roles]
            }

        role_names = [role.name for role in member_roles]
        await ctx.send(f"Group '{group_name}' created with group role: {group_role.name} and member roles: {' -> '.join(role_names)}")
    

    @group.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def group_remove(self, ctx, group_name: str):
        """
        Remove a group by name.
        """
        async with self.config.guild(ctx.guild).groups() as groups:
            if group_name in groups:
                del groups[group_name]
                await ctx.send(f"Group '{group_name}' removed.")
            else:
                await ctx.send(f"Group '{group_name}' not found.")
    

    @group.command(name="list")
    @commands.has_permissions(administrator=True)
    async def group_list(self, ctx):
        """
        List all groups for this server, showing group role and member roles.
        """
        groups = await self.config.guild(ctx.guild).groups()

        if not groups:
            await ctx.send("No groups configured for this server.")
            return

        embed = discord.Embed(title="Role Groups", color=discord.Color.blue())

        for group_name, data in groups.items():
            group_role = ctx.guild.get_role(data["group_role"])
            member_roles = [ctx.guild.get_role(rid) for rid in data["member_roles"]]
            group_role_name = group_role.name if group_role else f"<Deleted Role: {data['group_role']}>"
            member_role_names = [r.name if r else f"<Deleted Role: {rid}>" for r, rid in zip(member_roles, data["member_roles"])]
            embed.add_field(
                name=group_name,
                value=f"Group Role: {group_role_name}\nMembers: {' -> '.join(member_role_names)}",
                inline=False
            )

        await ctx.send(embed=embed)
    

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def groupcheck(self, ctx, member: discord.Member):
        """
        Check a specific member's role status against all groups.

        Shows what group roles and member roles they have or are missing.
        """
        groups = await self.config.guild(ctx.guild).groups()

        if not groups:
            await ctx.send("No groups configured for this server.")
            return

        embed = discord.Embed(
            title=f"Group Check: {member.display_name}",
            color=discord.Color.green()
        )

        for group_name, data in groups.items():
            group_role = ctx.guild.get_role(data["group_role"])
            member_roles = [ctx.guild.get_role(rid) for rid in data["member_roles"]]
            # Show if member has group role
            group_role_status = "✅" if group_role and group_role in member.roles else "❌"
            # Show which member roles they have
            member_status = []
            for r in member_roles:
                if r:
                    member_status.append(f"✅ {r.name}" if r in member.roles else f"❌ {r.name}")
                else:
                    member_status.append(f"<Deleted Role>")

            embed.add_field(
                name=f"Group: {group_name}",
                value=f"Group Role: {group_role_status} {group_role.name if group_role else '<Deleted Role>'}\n" +
                      "\n".join(member_status),
                inline=False
            )

        await ctx.send(embed=embed)
    

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def groupaudit(self, ctx):
        """
        Audit all members and fix missing group roles in groups.

        This will check all members against configured groups and add
        any missing group roles they should have (if they have a member role).
        """
        groups = await self.config.guild(ctx.guild).groups()

        if not groups:
            await ctx.send("No groups configured for this server.")
            return

        # Validate group roles and member roles (skip groups with deleted roles)
        valid_groups = {}
        for group_name, data in groups.items():
            group_role = ctx.guild.get_role(data["group_role"])
            member_roles = [ctx.guild.get_role(rid) for rid in data["member_roles"]]
            if group_role and all(member_roles):
                valid_groups[group_name] = {
                    "group_role": group_role,
                    "member_roles": member_roles
                }

        if not valid_groups:
            await ctx.send("No valid groups found (all contain deleted roles).")
            return

        total_fixes = 0
        total_members = len(ctx.guild.members)

        # Send initial progress message
        progress_msg = await ctx.send(f"Starting audit of {total_members} members...")

        processed = 0
        errors = 0

        for member in ctx.guild.members:
            # Skip bots
            if member.bot:
                processed += 1
                continue

            try:
                member_fixes = await self._fix_member_groups(member, valid_groups)
                total_fixes += member_fixes
            except Exception as e:
                log.error(f"Error processing member {member}: {e}")
                errors += 1

            processed += 1

            # Update progress every 50 members
            if processed % 50 == 0:
                status = f"Processed {processed}/{total_members} members. Fixed {total_fixes} roles"
                if errors > 0:
                    status += f", {errors} errors"
                await progress_msg.edit(content=status + "...")

        final_status = f"Audit complete! Processed {processed} members and fixed {total_fixes} missing roles."
        if errors > 0:
            final_status += f" Encountered {errors} errors (check logs for details)."

        await progress_msg.edit(content=final_status)
    

    async def _fix_member_groups(self, member: discord.Member, groups: dict) -> int:
        """
        Only add the group role if the user has any member role in the group and is missing the group role.
        Never add or remove member roles.
        Returns the number of group roles added.
        """
        fixes = 0
        for group_name, data in groups.items():
            group_role = data["group_role"]  # discord.Role
            member_roles = data["member_roles"]  # list of discord.Role

            # Defensive: skip if any are None (deleted roles)
            if not group_role or not member_roles or any(r is None for r in member_roles):
                continue

            # If the user has any member role in this group, add the group role if missing
            has_member_role = any(role in member.roles for role in member_roles)
            if has_member_role and group_role not in member.roles:
                try:
                    await member.add_roles(group_role, reason=f"RoleKeeper: Adding missing group role from {group_name} group")
                    fixes += 1
                    log.info(f"Added group role {group_role} to {member} in {member.guild} from group {group_name}")
                except discord.Forbidden:
                    log.warning(f"Could not add group role to {member} - insufficient permissions")
                except discord.HTTPException as e:
                    log.error(f"Failed to add group role to {member}: {e}")
        return fixes

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Listen for role updates and ensure group compliance.
        If a member's roles change, check if they need a group role added.
        """
        # Only process if roles actually changed
        if before.roles == after.roles:
            return
        # Skip bots
        if after.bot:
            return

        groups = await self.config.guild(after.guild).groups()
        if not groups:
            return

        # Validate group roles and member roles (skip groups with deleted roles)
        valid_groups = {}
        for group_name, data in groups.items():
            group_role = after.guild.get_role(data["group_role"])
            member_roles = [after.guild.get_role(rid) for rid in data["member_roles"]]
            if group_role and all(member_roles):
                valid_groups[group_name] = {
                    "group_role": group_role,
                    "member_roles": member_roles
                }

        if not valid_groups:
            return

        # Fix group roles for this member
        await self._fix_member_groups(after, valid_groups)
    
    async def cog_command_error(self, ctx, error):
        """
        Handle cog-specific errors and send user-friendly messages.
        """
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don't have the necessary permissions to perform this action.")
        else:
            log.exception("Unexpected error in RoleKeeper cog", exc_info=error)