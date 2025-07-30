from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')

    if not name or not email or not message:
        return jsonify({'status': 'error', 'message': 'All fields required'}), 400

    return jsonify({'status': 'success', 'message': 'Thanks for contacting us!'})

if __name__ == '__main__':
    app.run(debug=True)
