"""一键部署到腾讯云"""
import paramiko
import os
import time

HOST = "124.223.214.193"
USER = "ubuntu"
PASS = "U8n7yE6$BzZ)"

print("🔄 连接服务器...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=15)
print("✅ 连接成功")

def run(cmd, timeout=60):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        for line in out.strip().split('\n')[:5]:
            print(f"    {line}")
    if err.strip() and exit_code != 0:
        for line in err.strip().split('\n')[:3]:
            print(f"    ! {line}")
    return exit_code == 0

# 1. 更新系统
print("\n📦 更新系统包...")
run("sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv nginx git 2>&1 | tail -3", timeout=120)

# 2. 从 GitHub 拉代码
print("\n📥 拉取代码...")
run("cd /home/ubuntu && sudo -u ubuntu git clone https://github.com/snowwolf007/书店.git bookstore 2>&1 || (cd bookstore && git pull)", timeout=30)

# 3. 安装 Python 依赖
print("\n🐍 安装 Python 依赖...")
run("cd /home/ubuntu/bookstore/backend && python3 -m venv venv && source venv/bin/activate && pip install -q -r requirements.txt 2>&1 | tail -3", timeout=120)

# 4. 创建 systemd 服务
print("\n⚙️ 配置开机自启...")
SERVICE = """[Unit]
Description=Bookstore API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bookstore/backend
ExecStart=/home/ubuntu/bookstore/backend/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8899
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
ssh.exec_command(f"echo '{SERVICE}' | sudo tee /etc/systemd/system/bookstore.service")
run("sudo systemctl daemon-reload && sudo systemctl enable bookstore && sudo systemctl start bookstore", timeout=10)
time.sleep(3)

# 5. 检查服务
print("\n🔍 检查服务状态...")
run("sudo systemctl status bookstore --no-pager 2>&1 | head -10", timeout=5)

# 6. 配置防火墙
print("\n🔓 开放端口...")
run("sudo ufw allow 8899/tcp 2>/dev/null; sudo ufw --force enable 2>/dev/null", timeout=10)

# 7. 测试
print("\n🌐 测试 API...")
run("curl -s http://localhost:8899/api/health", timeout=5)

print("\n✅✅✅ 部署完成！")
print(f"   管理后台: http://{HOST}:8899/admin/admin.html")
print(f"   健康检查: http://{HOST}:8899/api/health")

ssh.close()
