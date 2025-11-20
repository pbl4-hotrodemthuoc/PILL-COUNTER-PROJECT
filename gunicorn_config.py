# File: gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:5001"
workers = 1  # SocketIO yêu cầu chỉ 1 worker
worker_class = "eventlet"  # Quan trọng: Sử dụng eventlet worker
timeout = 120
keepalive = 5
loglevel = "info"