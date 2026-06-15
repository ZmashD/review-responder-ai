import os
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. Configure your API access token safely
os.environ["GOOGLE_API_KEY"] = "AQ.Ab8RN6KePNRtawcrQk1Qbi1xz3ry_KolsX9eWtRF6ajd1N__Wg"

print("📡 Connecting to Gemini Engine...")

# 2. Initialize the lightweight, fast model variant
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

# 3. Fire a quick baseline validation diagnostic
try:
    response = llm.invoke("Say 'System Connection Successful!' if you can read this message.")
    print("\n🚀 Response Received from AI:")
    print(response.content)
except Exception as e:
    print("\n❌ Connection Failed. Check your API key.")
    print(f"Error details: {e}")