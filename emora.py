import os
import asyncio
import random
import tempfile
import warnings

import pygame
import pytz
import nltk
from textblob import TextBlob
from dotenv import load_dotenv
import speech_recognition as sr

from groq import Groq
from elevenlabs import ElevenLabs


# ---------------- CONFIG ----------------

warnings.filterwarnings("ignore")

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

WAKE_WORDS = ["emora", "memora", "amora", "imora"]
STOP_WORDS = ["bye", "goodbye", "stop", "exit"]

nltk.download("punkt", quiet=True)


# ---------------- ASSISTANT ----------------

class EMORA:

    def __init__(self):

        print("✅ Starting EMORA (Groq Mode)")

        self.timezone = pytz.timezone("Asia/Kolkata")

        pygame.mixer.init()

        # Speech Recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 1400
        self.recognizer.dynamic_energy_threshold = True

        # Conversation Mode
        self.active = False
        self.active_timeout = 0

        # ElevenLabs TTS
        if ELEVENLABS_API_KEY:
            self.tts = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            self.voice_id = "JBFqnCBsd6RMkjVDRZzb"
            print("✅ ElevenLabs Ready")
        else:
            self.tts = None
            print("⚠️ No ElevenLabs Key (Text Only Mode)")

        # Groq AI
        if GROQ_API_KEY:
            self.groq = Groq(api_key=GROQ_API_KEY)
            print("✅ Groq Connected")
        else:
            self.groq = None
            print("⚠️ No Groq Key (Fallback Mode)")


# ---------------- LISTEN ----------------

    def listen(self):

        try:

            with sr.Microphone() as source:

                print("🎤 Listening...")

                self.recognizer.adjust_for_ambient_noise(source, 1)

                audio = self.recognizer.listen(
                    source,
                    timeout=10,
                    phrase_time_limit=12
                )

                text = self.recognizer.recognize_google(audio)

                print("📝 You said:", text)

                return text.lower()

        except sr.UnknownValueError:
            print("⚠️ Could not understand audio")
            return None

        except sr.RequestError as e:
            print("❌ Google API Error:", e)
            return None

        except Exception as e:
            print("❌ Mic Error:", e)
            return None


# ---------------- SPEAK ----------------

    async def speak(self, text):

        if not text:
            print("⚠️ Empty reply, nothing to speak")
            return

        print("🔊 EMORA:", text)

        if not self.tts:
            return

        try:

            audio = self.tts.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128"
            )

            fd, path = tempfile.mkstemp(".mp3")
            os.close(fd)

            with open(path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.music.unload()
            os.remove(path)

        except Exception as e:
            print("❌ TTS Error:", e)


# ---------------- EMOTION ----------------

    def detect_emotion(self, text):

        blob = TextBlob(text)
        score = blob.sentiment.polarity

        if score > 0.3:
            return "Joy"
        elif score < -0.3:
            return "Sadness"
        else:
            return "Calm"


# ---------------- AI (GROQ) ----------------

    def ask_groq(self, query, emotion):

        if not self.groq:
            return self.fallback_reply(emotion)

        try:

            response = self.groq.chat.completions.create(

                model="llama-3.1-8b-instant",

                messages=[
                    {
                        "role": "system",
                        "content": "You are EMORA, a friendly and helpful voice assistant."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],

                max_tokens=200,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:

            print("❌ Groq Error:", e)

            return self.fallback_reply(emotion)


# ---------------- FALLBACK ----------------

    def fallback_reply(self, emotion):

        replies = {

            "Joy": [
                "That sounds wonderful!",
                "I'm happy to hear that!"
            ],

            "Sadness": [
                "I'm here for you.",
                "You're not alone."
            ],

            "Calm": [
                "How can I help you?",
                "I'm listening."
            ]
        }

        return random.choice(replies[emotion])


# ---------------- MAIN LOOP ----------------

    async def run(self):

        await self.speak("EMORA is ready. Say my name to begin.")

        while True:

            text = self.listen()

            if not text:
                continue

            print("DEBUG Heard:", text)


            # Wake word
            if any(w in text for w in WAKE_WORDS):

                self.active = True
                self.active_timeout = 6

                query = text

                for w in WAKE_WORDS:
                    query = query.replace(w, "")

                query = query.strip()

                if not query:
                    await self.speak("Yes, I'm listening.")
                    continue


            # Chat mode
            elif self.active:

                query = text
                self.active_timeout -= 1

                if self.active_timeout <= 0:

                    self.active = False
                    await self.speak("Going back to sleep.")
                    continue


            else:
                continue


            # Stop
            if any(w in query for w in STOP_WORDS):

                await self.speak("Goodbye. Take care.")
                break


            emotion = self.detect_emotion(query)

            print("😊 Emotion:", emotion)

            reply = self.ask_groq(query, emotion)

            print("🤖 AI Reply:", reply)

            await self.speak(reply)


# ---------------- START ----------------

async def main():

    emora = EMORA()

    await emora.run()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print("\n🛑 Closed")