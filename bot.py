import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import imageio_ffmpeg

TOKEN = '9009932540:AAHdMhc-6gMyPrwm8WEI_MCnu0RgVTQPIPU'
SECRET_PASSWORD = "IHf23sP"

authenticated_users = set()

# ساخت اپلیکیشن تلگرام
telegram_app = ApplicationBuilder().token(TOKEN).build()

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    authenticated_users.discard(user_id)
    
    await update.message.reply_text(
        "سلام عمو جواد عزیز! 🎵\n"
        "برای استفاده از بات، لطفاً ابتدا رمز عبور خود را وارد کنید:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in authenticated_users:
        if text == SECRET_PASSWORD:
            authenticated_users.add(user_id)
            await update.message.reply_text("✅ رمز عبور صحیح است! حالا لینک آهنگ یوتیوب یا نام خواننده را بفرستید تا موزیک را دانلود کنم 🎧")
        else:
            await update.message.reply_text("❌ رمز عبور اشتباه است. لطفاً رمز صحیح را وارد کنید:")
        return

    await update.message.reply_text(f"🔍 در حال جستجو و دانلود: {text} ... صبور باشید عمو جواد!")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
            'noplaylist': True
        }
        
        os.makedirs('downloads', exist_ok=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{text}", download=True)
            if 'entries' in info:
                info = info['entries'][0]
            filename = ydl.prepare_filename(info)
            audio_path = os.path.splitext(filename)[0] + ".mp3"
            
        with open(audio_path, 'rb') as audio:
            await update.message.reply_audio(audio, title=info.get('title', 'Music'))
            
        try:
            os.remove(audio_path)
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ خطایی رخ داد عمو جواد: {str(e)}")

# ثبت دستورات و پیام‌ها
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    # اجرای آپدیت تلگرام در لوپ رویداد
    asyncio.run(telegram_app.process_update(update))
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    # راه‌اندازی وب‌هوک تلگرام روی رندر
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/{TOKEN}"
        # تنظیم وب‌هوک به صورت سنکرون در شروع
        asyncio.run(telegram_app.bot.set_webhook(webhook_url))
        print(f"Webhook set to: {webhook_url}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
