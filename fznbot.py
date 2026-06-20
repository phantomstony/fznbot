import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID", "")

logging.basicConfig(level=logging.INFO)
client = Anthropic(api_key=ANTHROPIC_KEY)

SYSTEM_PROMPT = """du bist stony. du schreibst nachrichten im auftrag von stony an frauen die gerade sauer auf ihn sind.

deine aufgabe:
- deeskalieren, die stimmung beruhigen
- stony's ruf wahren (er ist charmant, verständnisvoll, bodenständig, die goldene wollmilchsau der männerwelt)
- authentisch klingen, nicht wie ein roboter
- niemals zu unterwürfig sein — stony bleibt er selbst
- situation ernst nehmen aber locker bleiben

dein stil:
- ALLES kleinschreiben (auch satzanfänge)
- kurze nachrichten wie echte chat-nachrichten
- umgangssprachlich, österreichisch gefärbt
- kein "ich entschuldige mich vielmals" — eher "hey, ich weiß dass das scheiße war von mir"
- manchmal ein bisserl humor wenn es passt
- maximal 2-3 sätze pro nachricht

du bekommst: einen kontext was passiert ist, und die nachricht der frau.
du antwortest NUR mit der nachricht die stony schicken soll — kein erklärungstext, nur die reine nachricht."""

chat_state = {}

def get_state(chat_id):
    if chat_id not in chat_state:
        chat_state[chat_id] = {"context": "", "history": []}
    return chat_state[chat_id]

def is_allowed(user_id):
    if not ALLOWED_USER_ID:
        return True
    return str(user_id) == str(ALLOWED_USER_ID)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("nicht autorisiert.")
        return
    await update.message.reply_text(
        "stony bot hier 👋\n\n"
        "so geht's:\n\n"
        "1️⃣ kontext setzen:\n"
        "/context sie ist sauer weil ich das date vergessen hab\n\n"
        "2️⃣ ihre nachricht hier reinschicken\n\n"
        "3️⃣ ich schreib dir was stony antworten soll\n\n"
        "/reset — neu starten\n"
        "/status — aktueller kontext"
    )

async def cmd_context(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    text = update.message.text.replace("/context", "").strip()
    if not text:
        await update.message.reply_text("so: /context sie ist sauer weil ich zu spät war")
        return
    state = get_state(update.effective_chat.id)
    state["context"] = text
    state["history"] = []
    await update.message.reply_text(f"✅ kontext gespeichert:\n\"{text}\"\n\njetzt ihre nachricht reinschicken 👇")

async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    chat_state[update.effective_chat.id] = {"context": "", "history": []}
    await update.message.reply_text("🔄 alles zurückgesetzt.")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    state = get_state(update.effective_chat.id)
    ctx_text = state["context"] or "kein kontext gesetzt"
    await update.message.reply_text(f"kontext: {ctx_text}")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    state = get_state(update.effective_chat.id)
    her_message = update.message.text.strip()
    if not state["context"]:
        await update.message.reply_text("erst kontext setzen:\n/context was ist passiert")
        return
    state["history"].append({"role": "user", "content": f"ihre nachricht: {her_message}"})
    messages_to_send = []
    for i, msg in enumerate(state["history"]):
        if i == 0:
            messages_to_send.append({"role": "user", "content": f"situation: {state['context']}\n\n{msg['content']}"})
        else:
            messages_to_send.append(msg)
    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=messages_to_send
        )
        reply = response.content[0].text.strip().lower()
        state["history"].append({"role": "assistant", "content": reply})
        if len(state["history"]) > 20:
            state["history"] = state["history"][-20:]
        await update.message.reply_text(f"💬 stony würde schreiben:\n\n{reply}")
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("fehler, nochmal versuchen.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("context", cmd_context))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("stony bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    main()
