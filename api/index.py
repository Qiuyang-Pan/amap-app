# backend/app.py
import os
import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from flask_cors import CORS

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__)

# --- 配置 ---
NOTION_API_TOKEN = os.environ.get('NOTION_API_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
# 确保你的 Notion 数据库中包含城市名称的列（属性）的名称
# 修改为你实际的属性名称，例如 "城市", "Name", "City Name" 等
NOTION_CITY_PROPERTY_NAME = 'City Name'
NOTION_API_VERSION = '2022-06-28' # 使用稳定的 Notion API 版本

# --- CORS 配置 ---
# 允许来自特定源的跨域请求
# 在开发环境中，可以允许来自前端开发服务器的源 (例如 http://localhost:5173)
# 在生产环境中，应将其替换为你的前端部署的域名
vercel_url = os.environ.get('VERCEL_URL')
allowed_origins = []
if vercel_url:
    allowed_origins.append(f"https://{vercel_url}")
# 如果你有自定义域名，也添加进去
# allowed_origins.append("https://your-custom-domain.com")
# 为了本地调试方便，也可以加上 localhost (部署到生产时可移除)
allowed_origins.append("http://localhost:5173") # Vite 默认端口
# 精确控制 API 路径的 CORS
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS"], # 根据需要调整
        "supports_credentials": True # 如果需要 Cookie 或认证头
    }
})

# --- 错误检查 ---
if not NOTION_API_TOKEN:
    print("错误：未在 .env 文件中设置 NOTION_API_TOKEN")
    exit(1) # 启动时退出，避免运行时错误
if not NOTION_DATABASE_ID:
    print("错误：未在 .env 文件中设置 NOTION_DATABASE_ID")
    exit(1)

# --- API 端点 ---
@app.route('/api/get-cities', methods=['GET'])
def get_cities():
    """
    从 Notion 数据库查询城市列表并返回。
    """
    notion_api_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        'Authorization': f"Bearer {NOTION_API_TOKEN}",
        'Notion-Version': NOTION_API_VERSION,
        'Content-Type': 'application/json',
    }
    # Notion 查询数据库通常需要 POST，即使是读取。
    # 空的 body {} 表示获取所有页面（受分页限制）。
    # 如果需要过滤或排序，可以在这里添加 body 数据。
    body = {}

    print("正在向 Notion API 发送请求...")

    try:
        response = requests.post(notion_api_url, headers=headers, json=body, timeout=15) # 增加超时
        response.raise_for_status()  # 如果 HTTP 状态码是 4xx 或 5xx，则抛出异常

        data = response.json()
        results = data.get('results', [])

        cities = []
        for page in results:
            properties = page.get('properties', {})
            city_property = properties.get(NOTION_CITY_PROPERTY_NAME)

            city_name = None
            # --- 解析城市名称 (需要根据你的 Notion 属性类型调整) ---
            if city_property:
                if city_property['type'] == 'title' and city_property['title']:
                    city_name = city_property['title'][0]['plain_text']
                elif city_property['type'] == 'rich_text' and city_property['rich_text']:
                     city_name = city_property['rich_text'][0]['plain_text']
                # elif city_property['type'] == 'text': # 如果是旧的 Text 类型
                #     # 处理旧 Text 类型的逻辑（可能需要调整）
                #     pass
                # 添加对其他可能类型的处理...

            if city_name and city_name.strip(): # 确保名称存在且不为空白
                cities.append(city_name.strip())
            else:
                 page_id = page.get('id', '未知ID')
                 print(f"警告：页面 {page_id} 无法提取有效的 '{NOTION_CITY_PROPERTY_NAME}' 或名称为空。属性数据: {city_property}")
        # --- 解析结束 ---

        print(f"成功从 Notion 获取到 {len(cities)} 个城市: {cities}")
        return jsonify(cities) # 直接返回城市名称的列表

    except requests.exceptions.Timeout:
        print("错误：请求 Notion API 超时")
        return jsonify({"error": "请求 Notion API 超时"}), 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        print(f"错误：请求 Notion API 失败: {e}")
        # 尝试获取更详细的 Notion 错误信息
        error_message = f"请求 Notion API 失败: {e}"
        if e.response is not None:
            try:
                notion_error = e.response.json()
                error_message = notion_error.get('message', error_message)
            except ValueError: # 如果响应不是 JSON
                error_message = f"{error_message} (状态码: {e.response.status_code})"
        return jsonify({"error": error_message}), getattr(e.response, 'status_code', 500) # 返回 Notion 的状态码或通用 500
    except Exception as e:
         print(f"错误：处理 Notion 数据时发生未知错误: {e}")
         return jsonify({"error": f"服务器内部错误: {e}"}), 500


# --- 运行 Flask 开发服务器 ---
if __name__ == '__main__':
    # debug=True 会在代码变动时自动重启服务器，方便开发
    # host='0.0.0.0' 使服务器可以从局域网内其他设备访问
    app.run(host='0.0.0.0', port=5000, debug=True)
