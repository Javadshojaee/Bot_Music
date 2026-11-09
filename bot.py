import os
import asyncio
import imageio_ffmpeg
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp
from telegram.request import HTTPXRequest

# توکن و رمز عبور
TOKEN = '9009932540:AAHdMhc-6gMyPrwm8WEI_MCnu0RgVTQPIPU'
SECRET_PASSWORD = "IHf23sP"

authenticated_users = set()

# راه‌اندازی Flask برای Webhook روی Render
app_flask = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    authenticated_users.discard(user_id)
    
    await update.message.reply_text(
        "سلام عمو جواد عزیز! 🎵\n"
        "برای استفاده از بات، لطفاً ابتدا رمز عبور خود را وارد کنید:"
    )

def download_audio(query: str):
    os.makedirs("downloads", exist_ok=True)
    
    query = query.replace("دانلود", "").replace("آهنگ", "").replace("اهنگ", "").strip()
    
    if not (query.startswith("http://") or query.startswith("https://")):
        query = f"ytsearch1:{query}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'socket_timeout': 180,
        'retries': 20,
        'quiet': False,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
                
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"
            
            return {
                'filepath': mp3_filename,
                'title': info.get('title', 'Unknown Title'),
                'performer': info.get('uploader', 'Unknown Artist'),
                'duration': info.get('duration', 0)
            }
    except Exception as e:
        print(f"❌ خطای دقیق yt-dlp: {e}")
        raise e

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not text:
        return

    if user_id not in authenticated_users:
        if text.strip() == SECRET_PASSWORD:
            authenticated_users.add(user_id)
            await update.message.reply_text(
                "✅ رمز عبور با موفقیت تایید شد!\n"
                "حالا اسم آهنگ یا لینکشو بفرست تا برات دانلودش کنم و بفرستم! 🚀"
            )
        else:
            await update.message.reply_text("❌ رمز عبور اشتباه است! لطفاً رمز صحیح را وارد کنید:")
        return

    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text("🔍 دارم با سرعت دنبال آهنگ می‌گردم، صبور باش عمو جواد...")

    try:
        loop = asyncio.get_running_loop()
        audio_info = await loop.run_in_executor(None, download_audio, text)

        file_path = audio_info['filepath']

        await status_msg.edit_text("📤 در حال آپلود موزیک توی تلگرام...")
        
        with open(file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                title=audio_info['title'],
                performer=audio_info['performer'],
                duration=audio_info['duration'],
                read_timeout=300,
                write_timeout=300,
                connect_timeout=60
            )

        if os.path.exists(file_path):
            os.remove(file_path)

        await status_msg.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text(f"❌ خطا در دانلود یا آپلود: {str(e)[:100]}")

# تنظیم اپلیکیشن تلگرام و اتصال به وب‌هوک
request_opts = HTTPXRequest(connect_timeout=60.0, read_timeout=300.0, write_timeout=300.0)
telegram_app = ApplicationBuilder().token(TOKEN).request(request_opts).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app_flask.route('/')
def home():
    return "Bot is active and running!"

@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "OK", 200

async def setup_webhook():
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/{TOKEN}"
        await telegram_app.bot.set_webhook(webhook_url)
        print(f"✅ Webhook set to: {webhook_url}")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(telegram_app.initialize())
    asyncio.get_event_loop().run_until_complete(setup_webhook())
    asyncio.get_event_loop().run_until_complete(telegram_app.start())
    
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)
