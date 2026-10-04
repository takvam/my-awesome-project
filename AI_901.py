import os
from openai import OpenAI
from dotenv import load_dotenv

# Last inn .env-filen (Her må din ekte OpenAI-nøkkel ligge under OPENAI_API_KEY)
load_dotenv()

# Hent API-nøkkelen fra miljøvariablene
api_key = os.getenv("OPENAI_API_KEY")

# Initialiser standard OpenAI-klient (Uten base_url kobler den direkte til OpenAI)
client = OpenAI(api_key=api_key)

# Send forespørsel til OpenAI med modellen som en tekststreng
completion = client.chat.completions.create(
    model="gpt-4o-mini",  # Ren tekststreng i stedet for LangChain-objekt
    messages=[
        {
            "role": "user",
            "content": "What is the capital of England?",
        }
    ],
)

# Skriv ut svaret
print(completion.choices[0].message.content)
