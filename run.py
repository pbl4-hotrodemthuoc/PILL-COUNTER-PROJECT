# File: run.py
from server_app import create_app

app = create_app()

if __name__ == '__main__':
    # Chạy ứng dụng với debug mode được BẬT
    app.run(host='0.0.0.0', port=5001, debug=True)