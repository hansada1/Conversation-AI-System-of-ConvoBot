from flask import Flask
from app import db

app = Flask(__name__)

@app.route('/drop-chat-history')
def drop_chat_history():
    db.engine.execute("DROP TABLE IF EXISTS chat_history")
    return "chat_history table dropped"

if __name__ == '__main__':
    app.run(debug=True)

