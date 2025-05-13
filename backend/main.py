from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route('/api')
def api():
    return jsonify({"message": "Hello, World!"})
if __name__ == '__main__':
    app.run(debug=True)