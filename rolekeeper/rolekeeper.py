import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from typing import List, Optional
import logging

log = logging.getLogger("red.rolekeeper")


class RoleKeeper(commands.Cog):
    """
    A cog that maintains role hierarchy chains.
    
    Ensures users have all roles lower than their highest role in the chain.
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Guild-specific config for role chains
        default_guild = {
            "role_chains": {}  # Format: {"chain_name": [role_id1, role_id2, role_id3]}
        }
        self.config.register_guild(**default_guild)
    
    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    async def rolechain(self, ctx):
        """Manage role chains for this server."""
        pass
    
    @rolechain.command(name="add")
    async def rolechain_add(self, ctx, chain_name: str, *roles: discord.Role):
        """
        Add a new role chain.
        
        Roles should be listed from lowest to highest in the hierarchy.
        Example: `[p]rolechain add progression Member Regular Veteran Elite`
        """
        if not roles:
            await ctx.send("You must specify at least one role.")
            return
        
        if len(roles) < 2:
            await ctx.send("A role chain must have at least 2 roles.")
            return
        
        # Check if bot can manage these roles
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if not bot_member:
            await ctx.send("Could not find bot member in guild.")
            return
        
        unmanageable_roles = []
        for role in roles:
            if role >= bot_member.top_role:
                unmanageable_roles.append(role.name)
        
        if unmanageable_roles:
            await ctx.send(f"I cannot manage these roles (they are above my highest role): {', '.join(unmanageable_roles)}")
            return
        
        # Store the role chain
        role_ids = [role.id for role in roles]
        async with self.config.guild(ctx.guild).role_chains() as chains:
            chains[chain_name] = role_ids
        
        role_names = [role.name for role in roles]
        await ctx.send(f"Role chain '{chain_name}' created with roles: {' -> '.join(role_names)}")
    
    @rolechain.command(name="remove")
    async def rolechain_remove(self, ctx, chain_name: str):
        """Remove a role chain."""
        async with self.config.guild(ctx.guild).role_chains() as chains:
            if chain_name in chains:
                del chains[chain_name]
                await ctx.send(f"Role chain '{chain_name}' removed.")
            else:
                await ctx.send(f"Role chain '{chain_name}' not found.")
    
    @rolechain.command(name="list")
    async def rolechain_list(self, ctx):
        """List all role chains for this server."""
        chains = await self.config.guild(ctx.guild).role_chains()
        
        if not chains:
            await ctx.send("No role chains configured for this server.")
            return
        
        embed = discord.Embed(title="Role Chains", color=discord.Color.blue())
        
        for chain_name, role_ids in chains.items():
            roles = []
            for role_id in role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role.name)
                else:
                    roles.append(f"<Deleted Role: {role_id}>")
            
            embed.add_field(
                name=chain_name,
                value=" -> ".join(roles),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    async def roleaudit(self, ctx):
        """
        Audit all members and fix missing roles in role chains.
        
        This will check all members against configured role chains and add
        any missing roles they should have based on their highest role.
        """
        chains = await self.config.guild(ctx.guild).role_chains()
        
        if not chains:
            await ctx.send("No role chains configured for this server.")
            return
        
        # Get all valid role chains (filter out chains with deleted roles)
        valid_chains = {}
        for chain_name, role_ids in chains.items():
            roles = []
            for role_id in role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role)
            
            if len(roles) == len(role_ids):  # All roles still exist
                valid_chains[chain_name] = roles
        
        if not valid_chains:
            await ctx.send("No valid role chains found (all contain deleted roles).")
            return
        
        total_fixes = 0
        total_members = len(ctx.guild.members)
        
        # Send initial message
        progress_msg = await ctx.send(f"Starting audit of {total_members} members...")
        
        # Process members in batches to avoid rate limits
        processed = 0
        for member in ctx.guild.members:
            if member.bot:
                processed += 1
                continue
            
            member_fixes = await self._fix_member_roles(member, valid_chains)
            total_fixes += member_fixes
            processed += 1
            
            # Update progress every 50 members
            if processed % 50 == 0:
                await progress_msg.edit(content=f"Processed {processed}/{total_members} members. Fixed {total_fixes} roles so far.")
        
        await progress_msg.edit(content=f"Audit complete! Processed {processed} members and fixed {total_fixes} missing roles.")
    
    async def _fix_member_roles(self, member: discord.Member, chains: dict) -> int:
        """Fix roles for a single member. Returns number of roles added."""
        fixes = 0
        
        for chain_name, roles in chains.items():
            # Find the highest role the member has in this chain
            highest_role_index = -1
            for i, role in enumerate(roles):
                if role in member.roles:
                    highest_role_index = i
            
            # If member has a role in this chain, ensure they have all lower roles
            if highest_role_index >= 0:
                for i in range(highest_role_index):
                    role = roles[i]
                    if role not in member.roles:
                        try:
                            await member.add_roles(role, reason=f"RoleKeeper: Adding missing role from {chain_name} chain")
                            fixes += 1
                            log.info(f"Added role {role.name} to {member} in {member.guild}")
                        except discord.Forbidden:
                            log.warning(f"Could not add role {role.name} to {member} - insufficient permissions")
                        except discord.HTTPException as e:
                            log.error(f"Failed to add role {role.name} to {member}: {e}")
        
        return fixes
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Listen for role updates and ensure role chain compliance."""
        # Only process if roles actually changed
        if before.roles == after.roles:
            return
        
        # Skip bots
        if after.bot:
            return
        
        # Get role chains for this guild
        chains = await self.config.guild(after.guild).role_chains()
        if not chains:
            return
        
        # Get valid role chains
        valid_chains = {}
        for chain_name, role_ids in chains.items():
            roles = []
            for role_id in role_ids:
                role = after.guild.get_role(role_id)
                if role:
                    roles.append(role)
            
            if len(roles) == len(role_ids):  # All roles still exist
                valid_chains[chain_name] = roles
        
        if not valid_chains:
            return
        
        # Fix member roles
        await self._fix_member_roles(after, valid_chains)
    
    async def cog_command_error(self, ctx, error):
        """Handle cog-specific errors."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don't have the necessary permissions to perform this action.")
        else:
            log.exception("Unexpected error in RoleKeeper cog", exc_info=error)