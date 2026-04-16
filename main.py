from flask import Flask, request, jsonify
import threading
import time
import discord
from discord.ext import commands
import random
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

SORCERER_ROLE_ID = 1493707922486591717
CURSE_ROLE_ID = 1493720668380991588
CURSE_USER_ROLE_ID = 1494358326329344050

code_to_uuid = {}  # code -> {uuid, expires}
uuid_to_discord = {}  # uuid -> discord_id

CODE_EXPIRY = 300  # five minutes

def get_roles(guild):
    sorcerer = guild.get_role(SORCERER_ROLE_ID)
    curse = guild.get_role(CURSE_ROLE_ID)
    return sorcerer, curse

def get_team(member):
    role_ids = [role.id for role in member.roles]

    # Priority order (important if someone somehow has multiple)
    if SORCERER_ROLE_ID in role_ids:
        return "sorcerer"
    elif CURSE_ROLE_ID in role_ids:
        return "curse"
    elif CURSE_USER_ROLE_ID in role_ids:
        return "curse_user"

    return "none"

app = Flask(__name__)

@app.route("/verify/start", methods=["POST"])
def start_verify():
    data = request.json
    uuid = data.get("uuid")

    if not uuid:
        return jsonify({"error": "missing uuid"}), 400

    code = f"JUJU-{random.randint(1000,9999)}"

    code_to_uuid[code] = {
        "uuid": uuid,
        "expires": time.time() + CODE_EXPIRY
    }

    print(f"[VERIFY START] {uuid} -> {code}")

    return jsonify({"code": code})

@app.route("/role", methods=["GET"])
def get_role():
    uuid = request.args.get("uuid")

    if uuid not in uuid_to_discord:
        return jsonify({"team": "none"})

    discord_id = uuid_to_discord[uuid]

    guild = bot.guilds[0]  # assumes 1 server
    member = guild.get_member(discord_id)

    if not member:
        return jsonify({"team": "none"})

    team = get_team(member)

    print(f"[ROLE CHECK] {uuid} -> {team}")

    return jsonify({"team": team})

@bot.event
async def on_ready():
    print(f"logged in as {bot.user} yay!pyt")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def rollall(ctx):
    guild = ctx.guild
    sorcerer_role, curse_role = get_roles(guild)

    if not sorcerer_role or not curse_role:
        await ctx.send("no roles :(  check role IDs.")
        return

    eligible = [
        member for member in guild.members
        if sorcerer_role not in member.roles
        and curse_role not in member.roles
        and not member.bot
    ]

    random.shuffle(eligible)

    half = len(eligible) // 2

    sorcerers = eligible[:half]
    curses = eligible[half:]

    for member in sorcerers:
        await member.add_roles(sorcerer_role)

    for member in curses:
        await member.add_roles(curse_role)

    await ctx.send(
        f"Rolled {len(eligible)} users:\n"
        f"{len(sorcerers)} became Sorcerers!!\n"
        f"{len(curses)} became Curses.. boo!!"
    )

@bot.command()
async def verify(ctx, code: str):
    if code not in code_to_uuid:
        await ctx.send("invalid or expired code")
        return

    data = code_to_uuid[code]

    if time.time() > data["expires"]:
        del code_to_uuid[code]
        await ctx.send("code expired.")
        return

    uuid = data["uuid"]

    uuid_to_discord[uuid] = ctx.author.id
    del code_to_uuid[code]

    await ctx.send("linked your account successfully!!")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def reroll(ctx, member: discord.Member):
    guild = ctx.guild
    sorcerer_role, curse_role = get_roles(guild)

    if not sorcerer_role or not curse_role:
        await ctx.send("roles not found..")
        return

    # Remove existing roles if they have any
    if sorcerer_role in member.roles:
        await member.remove_roles(sorcerer_role)
    if curse_role in member.roles:
        await member.remove_roles(curse_role)

    # Randomly assign
    new_role = random.choice([sorcerer_role, curse_role])
    await member.add_roles(new_role)

    await ctx.send(f"{member.mention} has been rerolled into {new_role.name}!!!!")

@bot.command()
async def hi(ctx):
    sora_id = 698207822206206088

    if ctx.author.id == sora_id:
        responses = [
            "OMG HI SORA IM UR BIGGEST FAN!!",
            "YOOO HOW ARE YOU!!",
            "hows jujustsu chronicles going! :D"
        ]
    else:
        responses = [
            "ew who is this bum..",
            "i guess bro..",
            "im busy go away!!"
        ]

    await ctx.send(random.choice(responses))

@bot.command()
async def list(ctx):
    sorcerer_role, curse_role = get_roles(ctx.guild)

    sorcerers = len(sorcerer_role.members)
    curses = len(curse_role.members)

    await ctx.send(
        f"sorcerers: {sorcerers}\n"
        f"curses: {curses}"
    )

@bot.command()
@commands.has_permissions(manage_roles=True)
async def balance(ctx):
    import asyncio

    guild = ctx.guild
    sorcerer_role, curse_role = get_roles(guild)

    sorcerers = sorcerer_role.members.copy()
    curses = curse_role.members.copy()

    diff = len(sorcerers) - len(curses)

    if diff == 0:
        await ctx.send("already perfectly balanced, your welcome sora heh!")
        return

    # Determine which side is bigger
    if diff > 0:
        bigger = sorcerers
        from_role = sorcerer_role
        to_role = curse_role
    else:
        bigger = curses
        from_role = curse_role
        to_role = sorcerer_role
        diff = abs(diff)

    # Number to move
    to_move = diff // 2

    random.shuffle(bigger)
    selected = bigger[:to_move]

    moved = 0

    for member in selected:
        try:
            await member.remove_roles(from_role)
            await member.add_roles(to_role)
            moved += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"failed on, pls check debug {member}: {e}")

    await ctx.send(f"balanced roles! moved {moved} ppl.")

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(os.getenv("DISCORD_TOKEN"))

bot.run(os.getenv("DISCORD_TOKEN"))
