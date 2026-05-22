import base64
import httpx
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from app.agent.state import AgentState
from app.schemas.receipt import ReceiptSchema
from app.core.config import settings

# Initialize the LLM using local Ollama vision model
llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=0,
    base_url=settings.OLLAMA_BASE_URL
)

# Bind the Pydantic schema for structured output extraction
structured_llm = llm.with_structured_output(ReceiptSchema)

def extract_receipt_info(state: AgentState):
    """
    Node that takes the image URL and asks the Vision LLM to extract the receipt data.
    """
    image_url = state["image_url"]
    
    # If using local mock storage in development, download the image and pass as base64 data URL
    # because OpenAI API cannot access local URLs like localhost/minio.
    if any(host in image_url for host in ["localhost", "minio", "127.0.0.1"]):
        try:
            # Map localhost to minio since we are running inside the container network
            fetch_url = image_url
            if "localhost" in fetch_url:
                fetch_url = fetch_url.replace("localhost", "minio")
            elif "127.0.0.1" in fetch_url:
                fetch_url = fetch_url.replace("127.0.0.1", "minio")
                
            response = httpx.get(fetch_url)
            if response.status_code == 200:
                base64_image = base64.b64encode(response.content).decode("utf-8")
                mime_type = response.headers.get("content-type", "image/jpeg")
                image_url = f"data:{mime_type};base64,{base64_image}"
        except Exception as e:
            print(f"Failed to fetch local image for base64 encoding: {e}")
            # Keep original URL as fallback
            
    # Construct the multimodal message
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Extract the receipt details from this image accurately."},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    )
    
    try:
        # Call the LLM to get structured Pydantic output
        receipt_data = structured_llm.invoke([message])
        return {"validated_receipt": receipt_data, "errors": []}
    except Exception as e:
        return {"errors": [str(e)]}

# Build the Graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("extract", extract_receipt_info)

# Set edges
builder.set_entry_point("extract")
builder.add_edge("extract", END)

# Compile graph
receipt_graph = builder.compile()
