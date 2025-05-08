import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pytube import YouTube
from yt_dlp import YoutubeDL
import instaloader

API_ID = "24436545"
API_HASH = "afa5558d3561cb2241ed836088b56098"
BOT_TOKEN = "7917489800:AAFvqTFOIWwcVR0IPEwxJCbFRF9EwWE-Fxw"

bot = Client("media_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------- YouTube ----------
@bot.on_message(filters.command("youtube"))
async def youtube_handler(client, message: Message):
    try:
        url = message.text.split(maxsplit=1)[1]
        yt = YouTube(url)
        buttons = []

        for stream in yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
            buttons.append([InlineKeyboardButton(f"{stream.resolution}", callback_data=f"yt_{stream.itag}_{url}")])

        if yt.streams.filter(only_audio=True):
            buttons.append([InlineKeyboardButton("Audio Only", callback_data=f"yt_audio_{url}")])

        await message.reply("Select Quality:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await message.reply(f"Error: {e}")

@bot.on_callback_query(filters.regex("^yt_"))
async def youtube_download(client, callback_query):
    await callback_query.answer()
    data = callback_query.data.split("_")
    if data[1] == "audio":
        url = "_".join(data[2:])
        yt = YouTube(url, on_progress_callback=lambda stream, chunk, bytes_remaining: show_progress(callback_query.message, stream, bytes_remaining))
        stream = yt.streams.filter(only_audio=True).first()
    else:
        itag = int(data[1])
        url = "_".join(data[2:])
        yt = YouTube(url, on_progress_callback=lambda stream, chunk, bytes_remaining: show_progress(callback_query.message, stream, bytes_remaining))
        stream = yt.streams.get_by_itag(itag)

    filename = stream.download()
    await callback_query.message.reply_document(filename)
    os.remove(filename)

def show_progress(message, stream, bytes_remaining):
    total_size = stream.filesize
    downloaded = total_size - bytes_remaining
    percent = int(downloaded / total_size * 100)
    try:
        asyncio.run_coroutine_threadsafe(
            message.edit(f"Downloading... {percent}%"), asyncio.get_event_loop()
        )
    except:
        pass

# ---------- Instagram Reels ----------
@bot.on_message(filters.command("instagram"))
async def insta_handler(client, message: Message):
    try:
        url = message.text.split(maxsplit=1)[1]
        loader = instaloader.Instaloader()
        shortcode = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        filename = f"{shortcode}.mp4"
        loader.download_post(post, target=shortcode)
        video_path = next((f"{shortcode}/{f}" for f in os.listdir(shortcode) if f.endswith(".mp4")), None)
        if video_path:
            await message.reply_document(video_path)
            os.remove(video_path)
            os.rmdir(shortcode)
        else:
            await message.reply("Video not found.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ---------- Facebook ----------
@bot.on_message(filters.command("facebook"))
async def fb_handler(client, message: Message):
    try:
        url = message.text.split(maxsplit=1)[1]
        opts = {
            'outtmpl': '%(title)s.%(ext)s',
            'format': 'best',
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await message.reply_document(filename)
        os.remove(filename)
    except Exception as e:
        await message.reply(f"Error: {e}")

# ---------- Start Bot ----------
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Welcome! Send /youtube <URL>, /instagram <URL>, or /facebook <URL> to download."
    )

bot.run()