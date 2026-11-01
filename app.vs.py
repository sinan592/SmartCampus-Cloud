
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>SmartCampus Cloud</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                background: #f0f4f8;
                padding: 80px 20px;
            }
            h1 {
                color: #1455a0;
            }
        </style>
    </head>
    <body>
        <h1>SmartCampus Cloud</h1>
        <h2>Welcome to Student Services Platform</h2>
        <p>Our cloud project is running!</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(debug=True)
