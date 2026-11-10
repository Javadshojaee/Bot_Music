
import os
import asyncio
import imageio_ffmpeg
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp
from telegram.request import HTTPXRequest

TOKEN = '9009932540:AAHdMhc-6gMyPrwm8WEI_MCnu0RgVTQPIPU'
SECRET_PASSWORD = "IHf23sP"

authenticated_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    authenticated_users.discard(user_id) # خارج کردن کاربر از حالت تایید شده
    
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

    # اگر کاربر خواست ریست کنه و از اول شروع کنه
    if text.strip() in ["شروع مجدد", "خروج", "reset"]:
        authenticated_users.discard(user_id)
        await update.message.reply_text("🔄 وضعیت شما ریست شد. لطفاً رمز عبور خود را وارد کنید:")
        return

    # بررسی رمز عبور
    if user_id not in authenticated_users:
        if text.strip() == SECRET_PASSWORD:
            authenticated_users.add(user_id)
            await update.message.reply_text(
                "✅ رمز عبور با موفقیت تایید شد!\n"
                "حالا اسم آهنگ یا لینکشو بفرست تا برات دانلودش کنم و بفرستم! 🚀\n"
                "(هر وقت خواستی خارج بشی کافیه بنویسی: شروع مجدد)"
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

def main():
    print("🤖 بات پایتونی روشن شد، عمو جواد آماده باش!")
    
    request = HTTPXRequest(connect_timeout=60.0, read_timeout=300.0, write_timeout=300.0)
    app = ApplicationBuilder().token(TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()