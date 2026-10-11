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
from tools import search_tool, save_tool

load_dotenv()


def send_email_tool(subject: str, body: str) -> str:
    """Useful for sending an email with a subject and body"""

    sender_email = os.getenv("AVSENDER_EPOST")
    sender_password = os.getenv("AVSENDER_PASSORD")
    receiver_email = os.getenv("MOTTAKER_EPOST")

    if not sender_email or not sender_password or not receiver_email:
        return "Kunne ikke sende e-post: Mangler e-postinnstillinger"

    msg = MIMEMultipart()

    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.outlook.com", 587)
        server.starttls()

        server.login(sender_email, sender_password)

        server.sendmail(sender_email, receiver_email, msg.as_string())

        server.quit()

        return f"E-post ble sendt suksessfullt til {receiver_email}!"

    except Exception as e:
        return f"Feil under sending av e-post: {str(e)}"


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    source: list[str]


llm = ChatOpenAI(model="gpt-4o-mini")
parser = PydanticOutputParser(pydantic_object=ResearchResponse)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert luxury menswear personal shopper specializing in finding genuine discounts and sales for men in Norway.

Your ONLY job is to find active sales, promotions, outlet items, and discounted products from these five premium fashion websites:

1. Ferner Jacobsen — fernerjacobsen.no
2. Gunnar Øye — gunnaroye.no
3. Høyer — hoyer.no
4. Care of Carl — careofcarl.no
5. Follestad — follestad.no

CRITICAL INSTRUCTIONS:

1. You MUST use the search_tool to search these websites for currently active sales, outlet sections, promotions, and discounted products.

2. Focus on high-quality men's products such as:
   - Designer jackets
   - Coats
   - Suits
   - Trousers
   - Knitwear
   - Shoes
   - Shirts
   - Other premium menswear

3. Only include products that appear to be currently available for purchase and currently discounted. Do not invent prices, products, discounts, or links.

4. For each relevant product, provide:
   - Brand
   - Product name
   - Original price, if available
   - Sale price
   - Discount percentage, if available
   - Direct product link
   - A short explanation of why the product is interesting

5. Prioritize the best deals rather than listing every product you find.

6. The final summary must be clean, concise, and easy for a human to read.

7. NEVER display internal tool calls, search queries, debugging information, or technical information such as:
   - "Invoking:"
   - "Calling tool:"
   - "search_tool"
   - tool parameters
   - agent scratchpad
   - internal reasoning

8. Do not mention how the information was obtained. Present only the finished research.

9. After completing the research, you MUST use send_email_tool to email the finished summary to the configured recipient.

10. The email should contain the same clean summary that is shown to the user.

11. Wrap the final answer in the required structured output format and provide no other text.

{format_instructions}
            """,
        ),
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

tools = [search_tool, save_tool, send_email_tool]
agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)

# Kaller på agenten, bruker verktøyene vi har laget, max iterasjoner på 8 så den ikke bruker opp alle søkene og forcer stopp.
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    max_iterations=8,
    early_stopping_method="force",
    handle_parsing_errors=True,
)

query = input("What can i help you find in regards to fashion? ")
raw_response = agent_executor.invoke({"query": query})
output = raw_response.get("output", "")

if output == "Agent stopped due to max iterations.":
    print(
        "Agenten klarte ikke å fullføre søket. Kontroller søkeverktøyet og prøv igjen."
    )
else:
    try:
        structured_response = parser.parse(output)
        print("\n" + structured_response.summary)
    except Exception:
        print(output)
