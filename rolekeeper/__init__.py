from .rolekeeper import RoleKeeper


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(RoleKeeper(bot))