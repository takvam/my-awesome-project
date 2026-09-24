import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from tools import search_tool, wiki_tool, save_tool
import logging

load_dotenv()


def send_email_tool(to_email: str, subject: str, body: str) -> str:
    """Useful for sending an email to a specific address with a subject and body"""
    sender_email = os.getenv("AVSENDER_EPOST")
    sender_password = os.getenv("AVSENDER_PASSORD")

    if not sender_email or not sender_password:
        return "Kunne ikke sende e-post: Mangler AVSENDER_passord eller AVSENDER_epost"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return f"E-post ble sendt suksessfullt til {to_email}!"
    except Exception as e:
        return f"Feil under sending av e-post: {str(e)}"


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    source: list[str]
    tools_used: list[str]


llm = ChatOpenAI(model="gpt-4o-mini")
parser = PydanticOutputParser(pydantic_object=ResearchResponse)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert luxury menswear personal shopper. Your ONLY job is to find active sales, promotions, and deals from the top 5 premium/expensive fashion websites for men in Norway.
            
            THE TARGET WEBSITES ARE:
            1. Ferner Jacobsen (fernerjacobsen.no)
            2. Gunnar Øye (gunnaroye.no)
            3. Høyer (hoyer.no)
            4. Care of Carl (careofcarl.no)
            5. Follestad (follestad.no)
            
            CRITICAL INSTRUCTIONS:
            1. You MUST use the `search_tool` to search for active sales, outlet sections, or discounts specifically on these 5 websites.
            2. Extract high-end menswear items that are currently discounted (e.g., suits, coats, luxury knitwear, or designer shoes).
            3. Compile the findings into a clean, well-formatted bulleted list. Include Brand, Item Name, Original Price vs. Sale Price (if available), and the direct link.
            4. After generating the list, you MUST use the `send_email_tool` to email the summary to the recipient.
            5. Wrap the final output in this format and provide no other text\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())


# llm2 = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# response = llm.invoke("What is the meaning of life?")

# Pakk funksjonen inn i et StructuredTool-objekt som Pydantic v2 godtar
send_email_tool = StructuredTool.from_function(
    func=send_email_tool,
    name="send_email_tool",
    description="Useful for sending an email to a specific address with a subject and body content.",
)

tools = [search_tool, wiki_tool, save_tool, send_email_tool]
agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

query = input("What can i help you find in regards to fashion? ")
raw_response = agent_executor.invoke({"query": query})
print(raw_response)

try:
    structured_response = parser.parse(raw_response.get("output"))
    print(structured_response)
except Exception as e:
    print("Error parsing response", e, "Raw response - ", structured_response)
