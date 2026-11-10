import os
import asyncio
import imageio_ffmpeg
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp
from telegram.request import HTTPXRequest

TOKEN = '9009932540:AAHdMhc-6gMyPrwm8WEI_MCnu0RgVTQPIPU'
SECRET_PASSWORD = "IHf23sP"

authenticated_users = set()

# دکمه شروع مجدد به عنوان کیبورد آماده
restart_keyboard = ReplyKeyboardMarkup([["🔄 شروع مجدد"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "کاربر گرامی"

    authenticated_users.discard(user_id)  # خارج کردن کاربر از حالت تایید شده
    
    await update.message.reply_text(
        f"سلام {first_name} عزیز! 🎵\n"
        "برای استفاده از ربات، لطفاً ابتدا رمز عبور خود را وارد کنید:",
        reply_markup=ReplyKeyboardRemove()  # حذف کیبورد در صورت وجود قبلی
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
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "کاربر گرامی"
    text = update.message.text

    if not text:
        return

    # اگر کاربر دکمه ریست رو زد یا نوشت شروع مجدد
    if text.strip() in ["🔄 شروع مجدد", "شروع مجدد", "خروج", "reset"]:
        authenticated_users.discard(user_id)
        await update.message.reply_text(
            f"🔄 وضعیت شما ریست شد، {first_name}.\nلطفاً رمز عبور خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # بررسی رمز عبور
    if user_id not in authenticated_users:
        if text.strip() == SECRET_PASSWORD:
            authenticated_users.add(user_id)
            await update.message.reply_text(
                f"✅ خوش آمدید {first_name}! رمز عبور تایید شد.\n\n"
                "حالا اسم آهنگ یا لینکش رو بفرست تا برات دانلود کنم و بفرستم! 🚀\n"
                "هر وقت خواستی خارج بشی، دکمه «🔄 شروع مجدد» رو از پایین لمس کن.",
                reply_markup=restart_keyboard
            )
        else:
            await update.message.reply_text("❌ رمز عبور اشتباه است! لطفاً رمز صحیح را وارد کنید:")
        return

    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text(f"🔍 در حال جستجوی آهنگ، لطفاً صبور باشید {first_name}...")

    try:
        loop = asyncio.get_running_loop()
        audio_info = await loop.run_in_executor(None, download_audio, text)

        file_path = audio_info['filepath']

        await status_msg.edit_text("📤 در حال آپلود موزیک در تلگرام...")
        
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
    print("🤖 ربات تلگرام با موفقیت اجرا شد!")
    
    request = HTTPXRequest(connect_timeout=60.0, read_timeout=300.0, write_timeout=300.0)
    app = ApplicationBuilder().token(TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
