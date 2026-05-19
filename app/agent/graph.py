from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agent.state import AgentState
from app.schemas.receipt import ReceiptSchema
from app.core.config import settings

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0, 
    api_key=settings.OPENAI_API_KEY
)

# Bind the Pydantic schema for structured output extraction
structured_llm = llm.with_structured_output(ReceiptSchema)

def extract_receipt_info(state: AgentState):
    """
    Node that takes the image URL and asks the Vision LLM to extract the receipt data.
    """
    image_url = state["image_url"]
    
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
