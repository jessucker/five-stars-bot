import discord
from discord.ext import commands, tasks
import datetime
import os
import logging
import pytz
import asyncio
import json
from datetime import datetime as dt

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Settings ---
ROLE_NAME = "main character"
REQUIRED_MESSAGES = 3
ACTIVE_WINDOW = 5
INACTIVE_LIMIT = 15
BONK_FILE = "horny_counts.json"
COOLDOWN_SECONDS = 300
HALL_OF_SHAME_CHANNEL = "hall-of-shame"
BOOSTER_ROLE = "hype squad"
HORNY_ROLE = "horny jail"
SHITTY_ROLE = "shithead prison"

message_log = {}
horny_counts = {}
bonk_cooldowns = {}
logged_messages = set()

logging.basicConfig(level=logging.INFO)

if os.path.exists(BONK_FILE):
    with open(BONK_FILE, "r") as f:
        horny_counts = json.load(f)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    cleanup_roles.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = datetime.datetime.utcnow()
    user_id = message.author.id

    if user_id not in message_log:
        message_log[user_id] = []
    message_log[user_id].append(now)

    message_log[user_id] = [
        t for t in message_log[user_id]
        if (now - t).total_seconds() <= ACTIVE_WINDOW * 60
    ]

    logging.info(f"[DEBUG] {message.author.display_name} has {len(message_log[user_id])} messages in the last {ACTIVE_WINDOW} minutes.")

    if len(message_log[user_id]) >= REQUIRED_MESSAGES:
        role = discord.utils.get(message.guild.roles, name=ROLE_NAME)
        if role and role not in message.author.roles:
            await message.author.add_roles(role)
            await message.channel.send(f"{message.author.mention} just gained the **main character** role!")
            logging.info(f"[DEBUG] Assigned role to {message.author.display_name}")

    await bot.process_commands(message)

@tasks.loop(minutes=5)
async def cleanup_roles():
    now = datetime.datetime.utcnow()
    logging.info(f"[CLEANUP] Running cleanup at {now.strftime('%H:%M:%S')}")

    for guild in bot.guilds:
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if not role:
            continue

        for member in role.members:
            user_id = member.id
            timestamps = message_log.get(user_id, [])
            timestamps = [t for t in timestamps if (now - t).total_seconds() <= INACTIVE_LIMIT * 60]
            message_log[user_id] = timestamps

            if len(timestamps) < REQUIRED_MESSAGES:
                await member.remove_roles(role)
                logging.info(f"[DEBUG] Removed role from {member.display_name} (inactive)")
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        async for msg in channel.history(limit=50):
                            if msg.author == member:
                                await channel.send(f"{member.mention} come back soon xoxo 💔")
                                break
                        break

@bot.command()
async def time(ctx, *args):
    zones = {
        "est": ("America/New_York", "Eastern (New York)"),
        "cst": ("America/Chicago", "Central (Chicago)"),
        "mst": ("America/Denver", "Mountain (Denver)"),
        "pst": ("America/Los_Angeles", "Pacific (Los Angeles)"),
        "gmt": ("Europe/London", "United Kingdom (London)")
    }
    zone_abbr = {abbr: tz for abbr, (tz, _) in zones.items()}

    if not args:
        output = ""
        for abbr, (tz_name, label) in zones.items():
            tz = pytz.timezone(tz_name)
            time_str = dt.now(tz).strftime("%-I:%M %p")
            output += f"<:fsstar:1376386701445828730> **`{abbr.upper()}`** — {label.lower()}: **{time_str}**\n"
        embed = discord.Embed(title="current time in key timezones:", description=output, color=10534607)
        embed.set_thumbnail(url="https://i.ibb.co/5gR6MThN/image.png")
        embed.set_image(url="https://i.ibb.co/g4Z9SNx/1dividerstuff.png")
        await ctx.send(embed=embed)
    else:
        try:
            input_time = args[0]
            input_zone = args[1].lower()
            if input_zone not in zone_abbr:
                await ctx.send("<:fserror:1376386668671533176> i don’t recognize that timezone! try one like `est`, `pst`, `cst`, `mst`, or `gmt` instead.")
                return

            parsed_time = dt.strptime(input_time, "%I%p") if ":" not in input_time else dt.strptime(input_time, "%I:%M%p")
            now_date = dt.now(pytz.timezone(zone_abbr[input_zone])).date()
            local_dt = pytz.timezone(zone_abbr[input_zone]).localize(datetime.datetime.combine(now_date, parsed_time.time()))
            unix_ts = int(local_dt.timestamp())

            desc = f"<:fsstar:1376386701445828730> **{parsed_time.strftime('%-I:%M %p')} `{input_zone.upper()}`** is **<t:{unix_ts}:t>** where you live.\n\n"
            desc += "**converted time in other timezones:**\n"
            for abbr, (tz_name, label) in zones.items():
                if abbr == input_zone:
                    continue
                converted = local_dt.astimezone(pytz.timezone(tz_name)).strftime("%-I:%M %p")
                desc += f"\u2003<:fsstar:1376386701445828730> **`{abbr.upper()}`** — {label.lower()}: **{converted}**\n"

            embed = discord.Embed(title="time converted:", description=desc, color=10534607)
            embed.set_thumbnail(url="https://i.ibb.co/5gR6MThN/image.png")
            embed.set_image(url="https://i.ibb.co/g4Z9SNx/1dividerstuff.png")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("<:fserror:1376386668671533176> i couldn’t understand that! try `!time 2:35pm est` or `!time 5pm pst` instead.")
            logging.error(f"[TIME PARSE ERROR] {e}")

@bot.command()
async def hornystats(ctx, member: discord.Member = None):
    target = member or ctx.author
    count = horny_counts.get(str(target.id), 0)
    if count >= 10:
        comment = "put them in the horny hall of fame."
    elif count >= 5:
        comment = "someone please unplug their router."
    elif count >= 3:
        comment = "triple repeat offender! they knew better."
    elif count == 1:
        comment = "first offense… interesting."
    else:
        comment = "a clean record... for now."
    await ctx.send(f"{target.mention} has been bonked {count} times. {comment}")

@bot.command()
async def hornytop(ctx):
    guild_user_ids = {str(m.id) for m in ctx.guild.members}
    filtered = {uid: count for uid, count in horny_counts.items() if uid in guild_user_ids}
    top = sorted(filtered.items(), key=lambda x: x[1], reverse=True)[:5]
    if not top:
        await ctx.send("no one is in horny jail... yet.")
        return
    lines = []
    for i, (uid, count) in enumerate(top, start=1):
        user = ctx.guild.get_member(int(uid))
        name = user.display_name if user else f"User {uid}"
        lines.append(f"{i}. {name} — {count} bonks")
    await ctx.send("🔥 hornytop 5:\n" + "\n".join(lines))

@bot.command()
async def horny(ctx, member: discord.Member = None):
    booster_role = discord.utils.get(ctx.guild.roles, name=BOOSTER_ROLE)
    jail_role = discord.utils.get(ctx.guild.roles, name=HORNY_ROLE)
    now = datetime.datetime.utcnow()

    if bonk_cooldowns.get(ctx.author.id) and (now - bonk_cooldowns[ctx.author.id]).total_seconds() < COOLDOWN_SECONDS:
        await ctx.send("<:fserror:1376386668671533176> you just sent someone to horny jail! wait a few minutes, karen.")
        return
    if booster_role not in ctx.author.roles:
        await ctx.send("<:fserror:1376386668671533176> this command is for hype squad members only. boost the server to abuse your power!")
        return
    if member is None:
        await ctx.send("<:fserror:1376386668671533176> you need to mention someone to bonk.")
        return
    if HORNY_ROLE in [r.name for r in member.roles]:
        await ctx.send("<:fserror:1376386668671533176> babe. they’re already locked up. take a seat.")
        return

    await member.add_roles(jail_role)
    horny_counts[str(member.id)] = horny_counts.get(str(member.id), 0) + 1
    with open(BONK_FILE, "w") as f:
        json.dump(horny_counts, f)
    bonk_cooldowns[ctx.author.id] = now

    embed = discord.Embed(
        description=f"{member.mention} has been sent to horny jail for 30 minutes. stop being horny, bitch. this is an animal crossing server.",
        color=16711775
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/892167654679396353.webp?size=96&quality=lossless")
    await ctx.send(embed=embed)
    await asyncio.sleep(1800)
    await member.remove_roles(jail_role)

@horny.error
async def horny_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("<:fserror:1376386668671533176> i couldn’t find that user. try actually mentioning them.")

@bot.command()
@commands.cooldown(1, 300, commands.BucketType.user)
async def shitty(ctx, member: discord.Member):
    booster = discord.utils.get(ctx.author.roles, name=BOOSTER_ROLE)
    if booster is None:
        await ctx.send("<:fserror:1376386668671533176> this command is for hype squad members only. boost the server to abuse your power!")
        return
    role = discord.utils.get(ctx.guild.roles, name=SHITTY_ROLE)
    if not role:
        await ctx.send("<:fserror:1376386668671533176> the shithead prison role doesn’t exist. check with an admin!")
        return
    if role in member.roles:
        await ctx.send("<:fserror:1376386668671533176> babe. they’re already locked up. take a seat.")
        return
    await member.add_roles(role)
    embed = discord.Embed(
        description=f"{member.mention} has been sent to shithead prison for 5 minutes. stop being shitty, bitch. take a break from discord and go touch grass.",
        color=10638614
    )
    embed.set_thumbnail(url="https://i.ibb.co/F30hxqt/shitheadprison.png")
    await ctx.send(embed=embed)
    logging.info(f"[SHITTY] {ctx.author.display_name} sent {member.display_name} to shithead prison.")
    await asyncio.sleep(300)
    await member.remove_roles(role)

@shitty.error
async def shitty_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("<:fserror:1376386668671533176> you just sent someone to shithead prison! wait a few minutes, karen.")

bot.run(os.getenv("TOKEN"))
