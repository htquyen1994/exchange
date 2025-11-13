# Exchange Flask App Deployment Guide

Hướng dẫn này giúp deploy ứng dụng Flask `exchange` trên server Ubuntu bằng `systemd`.  

---

## 1. Chuẩn bị server

1. Cập nhật package:
```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y python3.9 python3.9-venv python3.9-distutils python3-pip

sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx

cd /home/ubuntu
git clone <REPO_URL> exchange
cd exchange

# Tạo virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Cài các package cần thiết
pip install --upgrade pip
pip install -r requirements.txt

sudo vim /etc/systemd/system/flaskexchange.service

[Unit]
Description=Flask Exchange WebApp
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/exchange
ExecStart=/home/ubuntu/exchange/venv/bin/python /home/ubuntu/exchange/webapp.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target

Lưu và reload systemd:

sudo systemctl daemon-reload
sudo systemctl enable flaskexchange
sudo systemctl start flaskexchange