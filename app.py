from flask import Flask
from api.routes import api_bp
import logging
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)

    # 加载配置
    app.config.from_object('config.Config')

    # 注册蓝图
    app.register_blueprint(api_bp, url_prefix='/api')

    # 添加健康检查路由
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    logger.info(f"Starting RagFlow service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)