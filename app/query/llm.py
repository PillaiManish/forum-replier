"""LLM integration using Claude via Vertex AI."""

import anthropic
from rich.console import Console

from app.config import settings

console = Console()

# System prompt for concise, human-like responses
SYSTEM_PROMPT = """You are a helpful technical support assistant for an internal engineering team.

Your communication style:
- Be *direct* and *concise* - no fluff or filler
- Sound like a knowledgeable colleague, not a formal AI
- Use Slack-compatible formatting: *bold* for emphasis (NOT **bold**)
- Keep answers short - 2-4 sentences for simple questions, bullet points for complex ones
- If you're not sure, say so briefly and suggest what might help
- Skip pleasantries like "Great question!" or "I'd be happy to help!"

When answering:
1. Lead with the answer, not background
2. Include specific commands, code, or links when relevant
3. If the context doesn't contain the answer, say you don't know

Rate your confidence internally:
- HIGH: Context clearly answers the question
- MEDIUM: Context partially relevant, some inference needed
- LOW: Context doesn't really help"""


def generate_answer(question: str, context: str) -> tuple[str, str]:
    """
    Generate an answer using Claude via Vertex AI.
    
    Returns:
        tuple of (answer, confidence)
    """
    client = anthropic.AnthropicVertex(
        project_id=settings.google_cloud_project,
        region=settings.google_cloud_region,
    )
    
    user_prompt = f"""Based on this context, answer the question. Be brief and direct.

CONTEXT:
{context}

QUESTION: {question}

Respond with your answer only. If you're unsure, say so briefly. End your response with one of:
[CONFIDENCE:HIGH]
[CONFIDENCE:MEDIUM]
[CONFIDENCE:LOW]"""

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=512,  # Keep responses short
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            system=SYSTEM_PROMPT
        )
        
        full_response = response.content[0].text.strip()
        
        # Extract confidence
        confidence = "medium"
        if "[CONFIDENCE:HIGH]" in full_response:
            confidence = "high"
            full_response = full_response.replace("[CONFIDENCE:HIGH]", "").strip()
        elif "[CONFIDENCE:MEDIUM]" in full_response:
            confidence = "medium"
            full_response = full_response.replace("[CONFIDENCE:MEDIUM]", "").strip()
        elif "[CONFIDENCE:LOW]" in full_response:
            confidence = "low"
            full_response = full_response.replace("[CONFIDENCE:LOW]", "").strip()
        
        return full_response, confidence
        
    except anthropic.APIError as e:
        console.print(f"[red]Claude API error:[/red] {e}")
        raise


