import hmac
import os
import tempfile

from flask import Flask, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

import db
import learning
from chatbot_final import chat
from detector_manual import detect_manual, needs_care
from detector_pdf import detect as detect_pdf
from questions import QUESTIONNAIRE, clean_answers
from utils import SECTIONS, parse_reading


app = Flask(__name__)

# Needed for session cookies. Set a real value in .env for anything beyond local use.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf"}

db.init_db()
learning.rebuild_if_empty()


def allowed_file(filename):
    """Check whether the uploaded file is a PDF."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _store(source, result, reading, **extra):
    """Save an assessment. A storage failure is logged but never costs the user their reading."""
    try:
        return db.save_assessment(
            source=source,
            input_text=result["input_text"],
            raw_output=result["output"],
            reading=reading,
            examples_used=result["examples_used"],
            **extra,
        )
    except Exception:
        app.logger.exception("Could not store assessment")
        return None


# ---------------------------------------------------------------- pages

# Renamed from detect(): that name shadowed the imported PDF detector, so /api/pdf
# was calling this view function instead of the AI pipeline.
@app.route("/")
def index():
    return render_template("detector.html")


@app.route("/expert")
def expert_page():
    return render_template("expert.html")


# ---------------------------------------------------------------- readings

@app.route("/api/questions")
def questions():
    return jsonify({"success": True, "sections": QUESTIONNAIRE})


@app.route("/api/manual", methods=["POST"])
def manual_analysis():
    """Receives the questionnaire answers (all optional) and runs detect_manual()."""

    try:
        data = request.get_json(silent=True)

        if not data or not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "No data was provided."
            }), 400

        measures = clean_answers(data)

        if not measures:
            return jsonify({
                "success": False,
                "error": "Please answer at least one question."
            }), 400

        result = detect_manual(measures)
        reading = parse_reading(result["output"])

        assessment_id = _store(
            "manual", result, reading,
            chronological_age=_to_float(measures.get("age")),
            answers=measures,
        )

        return jsonify({
            "success": True,
            "assessment_id": assessment_id,
            "result": result["output"],
            "reading": reading,
            "chronological_age": _to_float(measures.get("age")),
            "care_flag": needs_care(measures),
            "expert_cases_used": len(result["examples_used"]),
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
    """Receives a PDF, temporarily saves it, and sends its path to the PDF pipeline."""

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

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            file.save(temp_path)

        # An empty age box arrives as "", which should mean "not given".
        age = (request.form.get("age") or "").strip() or None

        result = detect_pdf(temp_path, age)
        reading = parse_reading(result["output"])

        assessment_id = _store(
            "pdf", result, reading,
            chronological_age=_to_float(age),
            filename=filename,
        )

        return jsonify({
            "success": True,
            "assessment_id": assessment_id,
            "filename": filename,
            "result": result["output"],
            "reading": reading,
            "chronological_age": _to_float(age),
            "expert_cases_used": len(result["examples_used"]),
        })

    except Exception as e:
        app.logger.exception("PDF analysis failed")

        return jsonify({
            "success": False,
            "error": "Unable to analyze the PDF.",
            "details": str(e)
        }), 500

    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ---------------------------------------------------------------- expert review

def _expert_denied():
    """Return an error response unless the request carries the expert access code."""
    expected = os.environ.get("EXPERT_ACCESS_CODE", "")
    if not expected:
        return jsonify({
            "success": False,
            "error": "Expert review is switched off. Set EXPERT_ACCESS_CODE in .env to turn it on."
        }), 503

    supplied = request.headers.get("X-Expert-Code", "")
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        return jsonify({
            "success": False,
            "error": "That expert access code is not correct."
        }), 403

    return None


@app.route("/api/expert/check", methods=["POST"])
def expert_check():
    return _expert_denied() or jsonify({"success": True})


@app.route("/api/assessments")
def assessments_list():
    denied = _expert_denied()
    if denied:
        return denied

    limit = min(max(request.args.get("limit", 50, type=int), 1), 200)
    offset = max(request.args.get("offset", 0, type=int), 0)
    return jsonify({"success": True, "assessments": db.list_assessments(limit, offset)})


@app.route("/api/assessments/<int:assessment_id>")
def assessment_detail(assessment_id):
    denied = _expert_denied()
    if denied:
        return denied

    assessment = db.get_assessment(assessment_id)
    if assessment is None:
        return jsonify({"success": False, "error": "No reading with that number."}), 404
    return jsonify({"success": True, "assessment": assessment})


# Plausible bounds for each corrected value.
LIMITS = {
    "biological_age": (0, 150),
    "life_expectancy": (0, 150),
    "health_score": (0, 100),
}
SCORE_LIMIT = (-60, 60)


def _bounded(value, low, high, label, errors):
    if value is None or str(value).strip() == "":
        return None
    number = _to_float(value)
    if number is None or not (low <= number <= high):
        errors.append(f"{label} must be a number between {low} and {high}.")
        return None
    return number


@app.route("/api/assessments/<int:assessment_id>/corrections", methods=["POST"])
def add_correction(assessment_id):
    denied = _expert_denied()
    if denied:
        return denied

    assessment = db.get_assessment(assessment_id)
    if assessment is None:
        return jsonify({"success": False, "error": "No reading with that number."}), 404

    data = request.get_json(silent=True) or {}
    errors = []

    expert_name = str(data.get("expert_name", "")).strip()
    reason = str(data.get("reason", "")).strip()

    if not expert_name:
        errors.append("Enter the expert's name.")
    elif len(expert_name) > 120:
        errors.append("Keep the name under 120 characters.")

    if len(reason) < 15:
        errors.append("Explain why the reading was wrong, in at least a sentence.")
    elif len(reason) > 4000:
        errors.append("Keep the reason under 4000 characters.")

    reading = {
        key: _bounded(data.get(key), low, high, key.replace("_", " ").capitalize(), errors)
        for key, (low, high) in LIMITS.items()
    }

    scores = {}
    raw_scores = data.get("scores") or {}
    if isinstance(raw_scores, dict):
        for section in SECTIONS:
            value = _bounded(raw_scores.get(section), *SCORE_LIMIT, f"{section.capitalize()} score", errors)
            if value is not None:
                scores[section] = value
    reading["scores"] = scores

    if not errors and all(reading[k] is None for k in LIMITS) and not scores:
        errors.append("Change at least one value before saving.")

    if errors:
        return jsonify({"success": False, "error": " ".join(errors)}), 400

    correction_id = db.add_correction(
        assessment_id, expert_name=expert_name, reason=reason, reading=reading
    )

    # Saved either way; only the "learn from it" step can fail separately.
    try:
        learning.index_correction(assessment)
        indexed = True
    except Exception:
        app.logger.exception("Correction saved but could not be indexed")
        indexed = False

    return jsonify({
        "success": True,
        "correction_id": correction_id,
        "indexed": indexed,
    })


# ---------------------------------------------------------------- chat

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
        # The Werkzeug debugger lets anyone who can reach the port run code on your
        # machine, so it is only on when you ask for it.
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )