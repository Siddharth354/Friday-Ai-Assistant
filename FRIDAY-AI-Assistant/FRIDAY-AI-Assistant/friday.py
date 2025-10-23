import os
import pyttsx3
import datetime
import smtplib
import time
import requests
import base64
import webbrowser
import spotipy  
from spotipy.oauth2 import SpotifyOAuth
from email.message import EmailMessage
import speech_recognition as sr
from openai import OpenAI
import sys
import re
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="#######################################"
)
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
engine = pyttsx3.init()
engine.setProperty("rate", 190)
engine.setProperty("volume", 1.0)
voices = engine.getProperty("voices")
engine.setProperty("voice", voices[1].id)
SPOTIFY_CLIENT_ID = "############################"
SPOTIFY_CLIENT_SECRET = "############################"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
))
def sanitize(text: str) -> str:
    return re.sub(r"[\*#]", "", text)
def speak(text: str) -> None:
    clean = sanitize(text)
    print(f"Assistant: {clean}")
    engine.say(clean)
    engine.runAndWait()
def get_time() -> None:
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is {now}")
def get_date() -> None:
    today = datetime.datetime.now().strftime("%d %B %Y")    
    speak(f"Today's date is {today}")
def wish_me() -> None:
    """Greet the user without providing date/time automatically."""
    speak("Hello Boss! How can I assist you today?")
def take_command() -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source)
    try:
        print("Recognizing...")
        query = recognizer.recognize_google(audio, language="en-in")
        print(f"You said: {query}")
        if isinstance(query, list):
            query = " ".join(str(item) for item in query)
        return query.lower()
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that. Could you please repeat?")
    except sr.RequestError:
        speak("Sorry, the speech service is down right now.")
    return "none"
def ask_gemma(prompt: str) -> str:
    user_msg = f"{prompt}\n\nPlease limit your answer to at most four lines"
    try:
        response = client.chat.completions.create(
            model="google/gemma-3n-e4b-it:free",
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.7,
            max_tokens=300
        )
        content = response.choices[0].message.content or ""
        lines = [line for line in content.strip().splitlines() if line.strip()]
        return "\n".join(lines[:4]) or "No response received"
    except Exception as e:
        return f"Error contacting Gemma: {e}"
def send_email(to: str, subject: str, body: str) -> None:
    sender = os.environ.get('EMAIL_ADDRESS')
    password = os.environ.get('EMAIL_PASSWORD')
    if not sender or not password:
        speak("Email credentials not set. Configure environment variables.")
        return
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(msg)
        speak(f"Email successfully sent to {to}")
    except Exception as e:
        speak(f"Failed to send email: {e}")
def get_spotify_token():
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
    
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(url, headers=headers, data=data)
    json_data = response.json()
    return json_data["access_token"]
def search_spotify_track(token: str, query: str):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "q": query,
        "type": "track",
        "limit": 1,
        "market": "IN"
    }
    response = requests.get(url, headers=headers, params=params)
    json_data = response.json()
    try:
        return json_data["tracks"]["items"][0]
    except (KeyError, IndexError):
        return None
def handle_play_command_legacy(query: str):
    try:
        token = get_spotify_token()
    except Exception as e:
        speak("Failed to connect to Spotify.")
        return
    match = re.search(r"play (?:songs?|music) (?:by|from)?\s*(.+)", query, re.IGNORECASE)
    if not match:
        speak("Please specify what you want to play.")
        return
    search_query = match.group(1).strip()
    track = search_spotify_track(token, search_query)
    if not track:
        speak("Couldn't find that track on Spotify.")
        return
    track_name = track["name"]
    artists = ", ".join([artist["name"] for artist in track["artists"]])
    track_url = track["external_urls"]["spotify"]
    
    speak(f"Playing {track_name} by {artists}")
    webbrowser.open(track_url)
def control_playback(action: str):
    try:
        if action == "play":
            sp.start_playback()
            speak("Resuming playback")
        elif action == "pause":
            sp.pause_playback()
            speak("Playback paused")
        elif action == "stop":
            sp.pause_playback()
            speak("Playback stopped")
    except Exception as e:
        speak(f"Couldn't {action} playback: {str(e)}")
def handle_play_command(query: str):
    try:
        search_query = re.sub(r"play\s+", "", query, flags=re.IGNORECASE).strip()
        if not search_query:
            sp.start_playback()
            speak("Resuming playback")
            return
        result = sp.search(q=search_query, limit=1, type='track')
        if not result or not result.get('tracks') or not result['tracks'].get('items') or not result['tracks']['items']:
            speak("Couldn't find that track on Spotify.")
            return
        track = result['tracks']['items'][0]
        track_name = track['name']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        sp.start_playback(uris=[track['uri']])
        speak(f"Playing {track_name} by {artists}")

    except Exception as e:
        speak(f"Playback failed: {str(e)}")
if __name__ == "__main__":
    wish_me()
    while True:
        query = take_command()
        if query == "none": continue

        if "date and time" in query:
            get_date()
            get_time()
        elif "date" in query:
            get_date()
        elif "time" in query:
            get_time()
        elif "send email to" in query:
            parts = query.replace('send email to', '').split('subject')
            if len(parts) == 2:
                to = parts[0].strip()
                rest = parts[1].split('body')
                subject = rest[0].strip()
                body = rest[1].strip() if len(rest)>1 else ''
                send_email(to, subject, body)
            else:
                speak("Specify: send email to [address] subject [subject] body [message]")
        elif any(kw in query for kw in ["information", "info about", "info on", "search for", "about"]):
            cleaned = query
            for kw in ["information", "info about", "info on", "search for", "about"]:
                cleaned = cleaned.replace(kw,"")
            prompt = f"Please give me detailed information about {cleaned.strip()}"
            speak("Let me look that up for you.")
            ans = ask_gemma(prompt)
            print(ans)
            speak(ans)
        elif any(kw in query for kw in ["offline","exit","quit"]):
            speak("Going offline. Goodbye, sir!")
            break
        elif any(kw in query for kw in [
            "search in chrome",
            "google",
            "google it",
            "open google",
            "search google",
            "open chrome",
            "search on google",
            "search on chrome"
        ]):
            speak("What should I search?")
            chromepath = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
            search = take_command().lower()
            if any(kw in query for kw in ["open google"]):
                webbrowser.get(chromepath).open_new_tab("https://www.google.com")
            else:
                webbrowser.get(chromepath).open_new_tab(search + ".com")
        elif any(kw in query for kw in ["play songs", "play music", "play track", "play song"]):
            speak("What would you like to play?")
            print("What would you like to play?")
            print("Listening for play command...")
            handle_play_command(query)
        elif "play" in query:
            if "pause" in query or "resume" in query:
                control_playback("play")
            else:
                handle_play_command(query)
        elif "pause" in query:
            control_playback("pause")
        elif "stop" in query:
            control_playback("stop")
        elif 'logout' in query:
            speak("Logging out...")
            os.system("shutdown -l")
        elif 'shutdown' in query:
            speak("Shutting down...")
            os.system("shutdown /s /t 1")
        elif 'restart' in query:
            speak("Restarting...")
            os.system("shutdown /r /t 1")
        else:
            speak("Let me think...")
            ans = ask_gemma(query)
            print(ans)
            speak(ans)
