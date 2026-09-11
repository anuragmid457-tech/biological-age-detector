import os
import tempfile

from flask import Flask, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from chatbot_final import chat
from detector_manual import detect_manual
from detector_pdf import detect


app = Flask(__name__)

# Needed for session cookies. Set a real value in .env for anything beyond local use.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    """Check whether the uploaded file is a PDF."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def detect():
    return render_template("detector.html")


@app.route("/api/manual", methods=["POST"])
def manual_analysis():
    """
    Receives manually entered health/lifestyle/biomarker data
    and passes it to detect_manual().
    """

    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "error": "No data was provided."
            }), 400

        # Remove empty values
        measures = {
            key: value
            for key, value in data.items()
            if value is not None and str(value).strip() != ""
        }

        if not measures:
            return jsonify({
                "success": False,
                "error": "Please enter at least one health measurement."
            }), 400

        result = detect_manual(measures)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:
        app.logger.exception("Manual analysis failed")

        return jsonify({
            "success": False,
            "error": "Unable to analyze the submitted information.",
            "details": str(e)
        }), 500


@app.route("/api/pdf", methods=["POST"])
def pdf_analysis():
    """
    Receives a PDF, temporarily saves it, and sends its path
    to the detect() AI pipeline.
    """

    temp_path = None

    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "error": "No PDF file was uploaded."
            }), 400

        file = request.files["file"]

        if not file or file.filename == "":
            return jsonify({
                "success": False,
                "error": "Please select a PDF file."
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": "Only PDF files are supported."
            }), 400

        filename = secure_filename(file.filename)

        # Create a temporary PDF file.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_path = temp_file.name
            file.save(temp_path)

        # Pass temporary PDF path to your existing AI function.
        age = request.form.get("age")
        result = detect(temp_path, age)

        return jsonify({
            "success": True,
            "filename": filename,
            "result": result
        })

    except Exception as e:
        app.logger.exception("PDF analysis failed")

        return jsonify({
            "success": False,
            "error": "Unable to analyze the PDF.",
            "details": str(e)
        }), 500

    finally:
        # Always remove temporary uploaded file.
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.route("/api/chat", methods=["POST"])
def chat_reply():
    """
    Health-only chat. Conversation history is kept per browser session,
    so two people using the site do not share a thread.
    """

    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get("message", "")).strip()

        if not message:
            return jsonify({
                "success": False,
                "error": "Please type a question."
            }), 400

        history = session.get("chat_history", [])
        reply = chat(message, history)
        session["chat_history"] = history[-24:]

        return jsonify({
            "success": True,
            "reply": reply
        })

    except Exception as e:
        app.logger.exception("Chat failed")

        return jsonify({
            "success": False,
            "error": "Unable to answer right now.",
            "details": str(e)
        }), 500


@app.route("/api/chat/reset", methods=["POST"])
def chat_reset():
    session.pop("chat_history", None)
    return jsonify({"success": True})


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "success": False,
        "error": "The uploaded file is too large. Maximum size is 10 MB."
    }), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "The requested endpoint was not found."
    }), 404


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )