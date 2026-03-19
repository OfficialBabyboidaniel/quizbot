import os
import discord
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from questions import QUESTIONS

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
QUIZ_TRIGGER_MESSAGE_ID = int(os.getenv("TRIGGER_MESSAGE_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# user_id -> {"current": question_index, "score": int, "answers": []}
sessions = {}


class AnswerView(View):
    def __init__(self, user_id: int, question_index: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.question_index = question_index

        for label in ["A", "B", "C", "D"]:
            btn = Button(label=label, style=discord.ButtonStyle.primary)
            btn.callback = self.make_callback(label)
            self.add_item(btn)

    def make_callback(self, label: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This isn't your quiz!", ephemeral=True)
                return

            session = sessions.get(self.user_id)
            if not session or session["current"] != self.question_index:
                await interaction.response.send_message("Already answered this one.", ephemeral=True)
                return

            correct = QUESTIONS[self.question_index]["answer"]
            if label == correct:
                session["score"] += 1
                result = "✅ Correct!"
            else:
                result = f"❌ Wrong! Answer was **{correct}**"

            session["current"] += 1
            self.stop()

            await interaction.response.edit_message(content=f"{result}", view=None)

            if session["current"] < len(QUESTIONS):
                await send_question(interaction.user, session["current"])
            else:
                score = session["score"]
                total = len(QUESTIONS)
                await interaction.user.send(f"🏁 Quiz done! You scored **{score}/{total}**.")
                del sessions[self.user_id]

        return callback


async def send_question(user: discord.User, index: int):
    q = QUESTIONS[index]
    text = f"**Q{index + 1}/{len(QUESTIONS)}: {q['question']}**\n" + "\n".join(q["options"])
    await user.send(text, view=AnswerView(user.id, index))


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.message_id != QUIZ_TRIGGER_MESSAGE_ID:
        return
    if payload.user_id == bot.user.id:
        return

    user = await bot.fetch_user(payload.user_id)
    if payload.user_id in sessions:
        await user.send("You already have an active quiz. Use `!reset` to restart.")
        return

    sessions[payload.user_id] = {"current": 0, "score": 0}
    await user.send("🎯 Quiz starting! Answer each question using the buttons.")
    await send_question(user, 0)


@bot.command()
async def reset(ctx):
    if ctx.author.id in sessions:
        del sessions[ctx.author.id]
        await ctx.send("🔄 Your quiz session has been reset. React to the quiz message to start again.")
    else:
        await ctx.send("You don't have an active session.")


@bot.command()
async def score(ctx):
    session = sessions.get(ctx.author.id)
    if not session:
        await ctx.send("No active quiz session.")
        return
    await ctx.send(f"Current score: **{session['score']}** | Question: **{session['current'] + 1}/{len(QUESTIONS)}**")


bot.run(TOKEN)
