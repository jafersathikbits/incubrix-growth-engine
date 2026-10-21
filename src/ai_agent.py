import json
import os
from google import genai
from openai import OpenAI
from src.config import GEMINI_API_KEY, GEMINI_MODEL, GROQ_MODEL, GROQ_API_KEY
from dotenv import load_dotenv

load_dotenv()

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
) if GROQ_API_KEY else None

def generate_personalized_outreach(creator_name, recent_video_title, channel_name):
    prompt = f"""
    You are an expert growth marketer for IncuBrix (an AI operating system for creators).
    Target Creator: {creator_name} (YouTube: {channel_name})
    Recent Video: "{recent_video_title}"
    
    Task:
    1. Write a 1-sentence "personalization hook" mentioning their recent video.
    2. Write a 50-word Email message pitching IncuBrix based on their need to repurpose this video.
    3. Write a 30-word LinkedIn DM (more professional).
    4. Write a 30-word Instagram DM (casual).
    
    Rules: 
    - Address the creator directly. Use the exact provided creator name: "{creator_name}". Do NOT use placeholders like [Name] or [Creator]. If it is a show name, address the team.
    - Include a mandatory opt-out ("Reply STOP to opt-out") in the email. 
    - Do not use fake compliments.
    
    Return ONLY a valid JSON object with these keys: "hook", "email", "linkedin", "instagram".
    """
    
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception:
            pass 

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            text = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            print(f"     -> Groq failed: {e}")

    return {
        "hook": f"Loved your recent video: {recent_video_title}.",
        "email": f"Hi {creator_name}, loved your recent video '{recent_video_title}'. IncuBrix helps creators repurpose long-form content into shorts and blogs automatically. Reply STOP to opt-out.",
        "linkedin": f"Hi {creator_name}, loved your video on {recent_video_title}. IncuBrix can help you repurpose it into more formats.",
        "instagram": f"Hey {creator_name}! Loved your recent vid. We built a tool at IncuBrix to help you clip and repurpose content easily."
    }