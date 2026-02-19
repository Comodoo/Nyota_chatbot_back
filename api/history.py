from flask import Blueprint, jsonify, request
from flask_cors import CORS
from models import Conversation, Message, db
from datetime import datetime

history_bp = Blueprint("history", __name__, url_prefix="/api")
CORS(history_bp, origins=["http://localhost:3000"])  # ✅ allow your frontend

# ===============================
# 1️⃣ GET ALL CONVERSATIONS (Sidebar)
# ===============================
@history_bp.route("/history", methods=["GET"])
def history():
    user_id = request.headers.get("user-id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user ID"}), 400

    conversations = Conversation.query.filter_by(user_id=user_id).all()
    data = []

    for conv in conversations:
        messages = Message.query.filter_by(
            conversation_id=conv.conversation_id
        ).order_by(Message.created_at).all()

        data.append({
            "conversation_id": conv.conversation_id,
            "messages": [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ]
        })

    return jsonify({"success": True, "conversations": data})


# ===============================
# 2️⃣ CREATE NEW CONVERSATION
# ===============================
@history_bp.route("/conversation", methods=["POST"])
def create_conversation():
    user_id = request.headers.get("user-id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user ID"}), 400

    # Create new conversation
    new_conv = Conversation(user_id=user_id, created_at=datetime.utcnow())
    db.session.add(new_conv)
    db.session.commit()

    return jsonify({
        "success": True,
        "conversation": {
            "conversation_id": new_conv.conversation_id,
            "messages": []  # empty initially
        }
    })


# ===============================
# 3️⃣ GET SINGLE CONVERSATION
# ===============================
@history_bp.route("/conversation/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    user_id = request.headers.get("user-id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = int(user_id)

    conversation = Conversation.query.filter_by(
        conversation_id=conversation_id,
        user_id=user_id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify({
        "success": True,
        "conversation": {
            "conversation_id": conversation.conversation_id,
            "messages": [
                {
                    "id": m.message_id,
                    "sender": m.sender,
                    "content": m.content,
                    "versions": [v.content for v in m.versions],
                    "created_at": m.created_at.isoformat()
                }
                for m in conversation.messages
            ]
        }
    })

# ===============================
# 4️⃣ DELETE CONVERSATION
# ===============================
@history_bp.route("/conversation/<int:conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    user_id = request.headers.get("user-id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user ID"}), 400

    # Find conversation owned by user
    conversation = Conversation.query.filter_by(
        conversation_id=conversation_id,
        user_id=user_id
    ).first()

    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    # Delete messages first (important!)
    Message.query.filter_by(conversation_id=conversation_id).delete()

    # Delete conversation
    db.session.delete(conversation)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Conversation deleted successfully"
    })
