from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Path where masked/demo data will be saved. ONLY masked values are stored.
data_file = "card_data.txt"


def is_valid_masked_card(masked: str) -> bool:
    if not masked or not isinstance(masked, str):
        return False
    # remove spaces for easier checks
    compact = masked.replace(' ', '')
    # must end with exactly 4 digits
    if not re.search(r'\d{4}$', compact):
        return False
    # digits part before last4 should be only non-digits (stars, x, etc.)
    prefix = compact[:-4]
    # ensure prefix contains only masking characters (stars, x, #)
    if re.search(r'[^\*xX#]', prefix):
        return False
    # ensure there are at least 6 masking characters in total (heuristic)
    if prefix.count('*') + prefix.lower().count('x') + prefix.count('#') < 6:
        return False
    return True


def is_valid_expiry(expiry: str) -> bool:
    if not expiry or not isinstance(expiry, str):
        return False
    m = re.match(r'^(0[1-9]|1[0-2])/(\d{2})$', expiry)
    if not m:
        return False
    mm = int(m.group(1))
    yy = int(m.group(2))
    year = 2000 + yy
    now = datetime.utcnow()
    if year < now.year:
        return False
    if year == now.year and mm < (now.month):
        return False
    return True


def is_masked_cvv(cvv_mask: str) -> bool:
    if not cvv_mask or not isinstance(cvv_mask, str):
        return False
    if re.search(r'\d', cvv_mask):
        return False
    return 1 <= len(cvv_mask) <= 4


@app.route('/submit_card', methods=['POST'])
def submit_card():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    masked_card = data.get('masked_card')
    expiry = data.get('expiry')
    cvv_mask = data.get('cvv_mask')
    consent = data.get('consent')

    if consent is not True:
        return jsonify({"message": "Consent required for demo collection"}), 400


    if not is_valid_expiry(expiry):
        return jsonify({"message": "expiry invalid or in the past"}), 400


    ts = datetime.utcnow().isoformat() + 'Z'
    line = f"{ts} | masked_card: {masked_card} | expiry: {expiry} | cvv_mask: {cvv_mask}\n"
    with open(data_file, 'a', encoding='utf-8') as f:
        f.write(line)

    return jsonify({"message": "Demo data saved"}), 200


@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Card server."}), 200


if __name__ == '__main__':
    # Ensure the file exists or create it if necessary
    if not os.path.exists(data_file):
        with open(data_file, 'w', encoding='utf-8') as f:
            pass
    app.run(debug=True, port=8000)
