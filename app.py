from flask import Flask, request, jsonify, send_from_directory
from agents.react_agent import agent


app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path=""
)


@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")


@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "reply": "Please enter a message."
        })


    try:

        result = agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        })


        messages = result["messages"]


        for message in reversed(messages):

            if not hasattr(message, "content") or not message.content:
                continue

            content = message.content

            # Gemini có thể trả content dưới dạng list các block
            if isinstance(content, list):

                text_parts = []

                for block in content:

                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))

                    elif isinstance(block, str):
                        text_parts.append(block)

                content = "\n".join(text_parts)

            else:
                content = str(content)

            return jsonify({
                "reply": content
            })


        return jsonify({
            "reply": "I could not generate a response."
        })


    except Exception as e:

        return jsonify({
            "reply": "Error: " + str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)