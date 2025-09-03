from operator import truediv
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import datetime
import requests

app = Flask(__name__)
app.config.from_object('config.Config')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Flask-Login设置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'


# 模型定义
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, default=25565)
    version = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_online = db.Column(db.Boolean, default=True)
    max_players = db.Column(db.Integer, default=20)
    current_players = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ResourcePack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    version = db.Column(db.String(50), nullable=False)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_server_status(server):
    # 模拟服务器状态检查
    # 在实际应用中，你可能需要使用真正的Minecraft服务器查询
    # APIhttps://api.mcstatus.io/v2/status/java/{server.ip}:{server.port}
    response = requests.get(f'https://api.mcstatus.io/v2/status/java/{server.ip}:{server.port}')
    try:
        if response.status_code == 200:
            data = response.json()
            if data['online']:
                return {
                    'is_online': data['online'],
                    'current_players': data['players']['online'],
                    'max_players': data['players']['max']
                }
            else:
                return {
                    'is_online': data['online'],
                    'current_players': '-',
                    'max_players': '-'
                }
    except:
        return {
            'is_online': False,
            'current_players': 0,
            'max_players': server.max_players
        }

def get_website_uptime():
    # 简单的网站运行时间计算（假设从2023年1月1日开始）
    start_date = datetime.datetime(2025, 9, 1)
    now = datetime.datetime.utcnow()
    uptime = now - start_date
    return uptime.days


# 路由定义
@app.route('/')
def index():
    servers = Server.query.all()
    packs = ResourcePack.query.all()

    # 为每个服务器获取状态
    server_data = []
    for server in servers:
        status = get_server_status(server)
        server_data.append({
            'id': server.id,
            'name': server.name,
            'ip': server.ip,
            'port': server.port,
            'version': server.version,
            'description': server.description,
            'is_online': status['is_online'],
            'current_players': status['current_players'],
            'max_players': status['max_players']
        })

    uptime_days = get_website_uptime()

    return render_template('index.html', servers=server_data, packs=packs, uptime_days=uptime_days)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 管理员路由
@app.route('/admin')
@login_required
def admin_dashboard():
    servers = Server.query.all()
    packs = ResourcePack.query.all()
    return render_template('admin/dashboard.html', servers=servers, packs=packs)

@app.route('/admin/add_server', methods=['GET', 'POST'])
@login_required
def add_server():
    if request.method == 'POST':
        name = request.form['name']
        ip = request.form['ip']
        port = int(request.form['port'])
        version = request.form['version']
        description = request.form['description']
        max_players = int(request.form['max_players'])

        server = Server(
            name=name,
            ip=ip,
            port=port,
            version=version,
            description=description,
            max_players=max_players
        )

        db.session.add(server)
        db.session.commit()

        flash('服务器添加成功')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_server.html')


@app.route('/admin/edit_server/<int:server_id>', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):
    server = Server.query.get_or_404(server_id)

    if request.method == 'POST':
        server.name = request.form['name']
        server.ip = request.form['ip']
        server.port = int(request.form['port'])
        server.version = request.form['version']
        server.description = request.form['description']
        server.max_players = int(request.form['max_players'])

        db.session.commit()
        flash('服务器更新成功')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_server.html', server=server)


@app.route('/admin/delete_server/<int:server_id>')
@login_required
def delete_server(server_id):
    server = Server.query.get_or_404(server_id)
    db.session.delete(server)
    db.session.commit()
    flash('服务器删除成功')
    return redirect(url_for('admin_dashboard'))

CHUNK_SIZE = 10 * 1024 * 1024   # 2 MB
# ------------------------------------------------------------------
import time          # 用于可选时间戳，亦可不用
# ====================================
# -------------------------------------------------
# 统一上传路由
@app.route('/admin/upload_pack', methods=['GET', 'POST'])
@login_required
def upload_pack():
    if request.method == 'GET':
        return render_template('admin/upload_pack.html')

    # ① 分片阶段
    if request.form.get('chunk') is not None:
        return _handle_chunk()

    # ② 合并阶段
    return _merge_chunks()
# -------------------------------------------------

def _handle_chunk():
    """保存单个分片"""
    upload_folder = app.config['UPLOAD_FOLDER']
    chunk_index   = int(request.form['chunk'])
    total_chunks  = int(request.form['chunks'])
    file_uuid     = request.form['uuid']
    filename      = secure_filename(request.form['filename'])

    chunk_dir = os.path.join(upload_folder, 'temp', file_uuid)
    os.makedirs(chunk_dir, exist_ok=True)

    chunk_path = os.path.join(chunk_dir, f'{chunk_index:05d}')
    request.files['file'].save(chunk_path)

    return jsonify({'status': 'ok', 'chunk': chunk_index})

# -------------------------------------------------
def _merge_chunks():
    """合并分片 + 入库 + 清理"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        file_uuid   = request.form['uuid']
        name        = request.form['name']
        version     = request.form['version']
        description = request.form['description']
        total       = int(request.form['total_chunks'])

        # 1. 使用前端原始文件名（已 secure_filename）
        filename = secure_filename(request.form['filename'])

        # 2. 重名处理：原名_序号.扩展名
        base, ext = os.path.splitext(filename)
        counter = 1
        final_path = os.path.join(upload_folder, filename)
        while os.path.exists(final_path):
            filename = f"{base}_{counter}{ext}"
            final_path = os.path.join(upload_folder, filename)
            counter += 1

        # 3. 合并所有分片
        chunk_dir = os.path.join(upload_folder, 'temp', file_uuid)
        with open(final_path, 'wb') as out_f:
            for i in range(total):
                chunk_path = os.path.join(chunk_dir, f'{i:05d}')
                with open(chunk_path, 'rb') as in_f:
                    shutil.copyfileobj(in_f, out_f)

        # 4. 入库（filename 就是最终磁盘文件名）
        pack = ResourcePack(
            name=name,
            filename=filename,
            version=version,
            description=description
        )
        db.session.add(pack)
        db.session.commit()

        # 5. 清理临时目录
        shutil.rmtree(chunk_dir, ignore_errors=True)

        return jsonify({'status': 'done', 'redirect': url_for('admin_dashboard')})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/admin/delete_pack/<int:pack_id>')
@login_required
def delete_pack(pack_id):
    pack = ResourcePack.query.get_or_404(pack_id)

    # 删除文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], pack.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(pack)
    db.session.commit()
    flash('整合包删除成功')
    return redirect(url_for('admin_dashboard'))


@app.route('/download/<int:pack_id>')
def download_pack(pack_id):
    pack = ResourcePack.query.get_or_404(pack_id)
    pack.download_count += 1
    db.session.commit()

    return send_from_directory(app.config['UPLOAD_FOLDER'], pack.filename, as_attachment=True)


# 这是一个路由处理函数，用于获取指定服务器的状态信息
@app.route('/api/server_status/<int:server_id>')
def api_server_status(server_id):
    # 根据传入的服务器ID查询服务器信息，如果不存在则返回404错误
    server = Server.query.get_or_404(server_id)
    # 调用get_server_status函数获取服务器的当前状态
    status = get_server_status(server)
    # 将状态信息转换为JSON格式并返回
    return jsonify(status)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # 创建默认管理员账户（如果不存在）
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账户已创建: admin / admin123")

    app.run(debug=True)
