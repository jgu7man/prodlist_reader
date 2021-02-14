from flask import Flask, jsonify, request, Response
from flask import render_template
from flask_cors import CORS

from src.file import File

def index():
    """
    Can upload file in firebase storage temp folder to read and change columns
    """
    app = Flask(__name__)
    CORS(app)
    cors = CORS(app, resources={
        r"/":{
            "origins":"*"
        }
    })
    
    @app.route('/', methods=['GET'])
    def test(): return 'Product list Reader works!'
    
    @app.route('/file', methods=['GET', 'POST'])
    def fileuploader(): return File.upload(request)
    
    @app.route('/set-columns', methods=['POST'])
    def set_columns(): return File.define_columns(request)
    
    
    if __name__ == '__main__':
        app.run(debug=True, port=5000)
    return app


app = index()