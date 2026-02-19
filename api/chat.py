from flask import Blueprint, request, jsonify
from extensions import db
from models import User, Conversation, Message, MessageVersion
from model_loader import llm

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


# ---------------------------
# Load prompts once at startup
# ---------------------------
def load_prompt_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


SYSTEM_PROMPT = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\full_prompts_system.txt")
DEFINITION_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\definition_prompts.txt")
RIGHTS_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\rights_prompts..txt")
REGISTRATION_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\registration_pr.txt")
COLLECTIVE_BARGAINING_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\collective_barg.txt")
STRIKE_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\strike_prompts..txt")
COMPLIANCE_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\compliance_prom.txt")
DISPUTE_RESOLUTION_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\dispute_resolut.txt")
HISTORICAL_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\historical_cont.txt")
PRACTICAL_PROMPTS = load_prompt_file(r"C:\Users\Thani\Documents\AI\prompts\practical_scena.txt")




# ---------------------------
# Helper functions
# ---------------------------
def get_or_create_user(user_id):
    user = User.query.get(user_id)
    if not user:
        user = User(user_id=user_id)
        db.session.add(user)
        db.session.commit()
    return user

def select_category_prompt(message: str) -> str:
    msg_lower = message.lower()
    if any(k in msg_lower for k in ["define", "meaning", "what is", "explain term"]):
        return DEFINITION_PROMPTS
    elif any(k in msg_lower for k in ["right", "protection", "employee", "employer"]):
        return RIGHTS_PROMPTS
    elif any(k in msg_lower for k in ["register", "registration", "certificate"]):
        return REGISTRATION_PROMPTS
    elif any(k in msg_lower for k in ["collective", "bargaining", "agreement"]):
        return COLLECTIVE_BARGAINING_PROMPTS
    elif any(k in msg_lower for k in ["strike", "lock-out", "industrial action"]):
        return STRIKE_PROMPTS
    elif any(k in msg_lower for k in ["dispute", "mediation", "arbitration"]):
        return DISPUTE_RESOLUTION_PROMPTS
    elif any(k in msg_lower for k in ["compliance", "penalty", "law", "enforce"]):
        return COMPLIANCE_PROMPTS
    elif any(k in msg_lower for k in ["history", "historical", "background"]):
        return HISTORICAL_PROMPTS
    elif any(k in msg_lower for k in ["example", "scenario", "case", "practical"]):
        return PRACTICAL_PROMPTS
    else:
        return ""  # fallback to system prompt only


def build_prompt(user_message: str) -> str:
    category_prompt = select_category_prompt(user_message)
    return f"""
{SYSTEM_PROMPT}

{category_prompt}

User Question: {user_message}

Answer in clear, professional language. Cite specific sections of the Zanzibar Labour Relations Act 2005 where relevant.
"""


# ---------------------------
# Chat Endpoint
# ---------------------------
@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = data.get("user_id")
    message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    user = get_or_create_user(user_id)

    # Use existing conversation or create new
    if conversation_id:
        conversation = Conversation.query.filter_by(
            conversation_id=conversation_id, user_id=user.user_id
        ).first()
    else:
        conversation = Conversation(user_id=user.user_id)
        db.session.add(conversation)
        db.session.commit()

    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    # Save user message
    user_msg = Message(
        conversation_id=conversation.conversation_id,
        sender="user",
        content=message
    )
    db.session.add(user_msg)
    db.session.commit()

    # Build prompt
    prompt = build_prompt(message)

    # Call LLM
    result = llm(prompt, max_tokens=500, temperature=0.3)
    reply = result["choices"][0]["text"].strip()

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.conversation_id,
        sender="assistant",
        content=reply
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        "success": True,
        "reply": reply,
        "conversation_id": conversation.conversation_id
    })


# ---------------------------
# Regenerate Endpoint
# ---------------------------
@chat_bp.route("/message/<int:message_id>/regenerate", methods=["POST"])
def regenerate_message(message_id):
    # Find assistant message
    assistant_msg = Message.query.get(message_id)
    if not assistant_msg or assistant_msg.sender != "assistant":
        return jsonify({"error": "Assistant message not found"}), 404

    # Find preceding user message
    user_msg = Message.query.filter_by(
        conversation_id=assistant_msg.conversation_id, sender="user"
    ).filter(
        Message.created_at < assistant_msg.created_at
    ).order_by(Message.created_at.desc()).first()

    if not user_msg:
        return jsonify({"error": "User question not found"}), 404

    # Save current assistant response as version
    version = MessageVersion(
        message_id=assistant_msg.message_id,
        content=assistant_msg.content
    )
    db.session.add(version)

    # Build prompt again
    prompt = build_prompt(user_msg.content)

    # Generate new response
    result = llm(prompt, max_tokens=500, temperature=0.3)
    new_reply = result["choices"][0]["text"].strip()

    # Update assistant message
    assistant_msg.content = new_reply
    db.session.commit()

    # Get all versions
    versions = MessageVersion.query.filter_by(
        message_id=assistant_msg.message_id
    ).order_by(MessageVersion.created_at.desc()).all()

    return jsonify({
        "success": True,
        "message": {
            "id": assistant_msg.message_id,
            "sender": assistant_msg.sender,
            "content": assistant_msg.content,
            "versions": [v.content for v in versions],
            "created_at": assistant_msg.created_at.isoformat()
        }
    })
