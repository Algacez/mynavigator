from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os

app = Flask(__name__)
CONFIG_FILE = 'config.json'


def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'links': []}


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    """主导航页面"""
    config = load_config()
    return render_template('index.html', links=config.get('links', []), categories=config.get('categories', []))


@app.route('/admin')
def admin():
    """管理页面"""
    config = load_config()
    return render_template('admin.html', links=config.get('links', []), categories=config.get('categories', []))


@app.route('/api/links', methods=['GET'])
def get_links():
    """获取所有链接"""
    config = load_config()
    return jsonify({'links': config.get('links', []), 'categories': config.get('categories', [])})


@app.route('/api/links', methods=['POST'])
def add_link():
    """添加新链接"""
    data = request.json
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()
    category_id = data.get('category_id', 1)

    if not name or not url:
        return jsonify({'error': '名称和URL不能为空'}), 400

    config = load_config()
    existing_ids = [link['id'] for link in config.get('links', [])]
    new_id = max(existing_ids) + 1 if existing_ids else 1

    new_link = {
        'id': new_id,
        'name': name,
        'url': url,
        'category_id': category_id
    }
    config.setdefault('links', []).append(new_link)
    save_config(config)

    return jsonify(new_link)


@app.route('/api/links/<int:link_id>', methods=['PUT'])
def update_link(link_id):
    """更新链接"""
    data = request.json
    config = load_config()
    links = config.get('links', [])

    for link in links:
        if link['id'] == link_id:
            link['name'] = data.get('name', link['name']).strip()
            link['url'] = data.get('url', link['url']).strip()
            if 'category_id' in data:
                link['category_id'] = data['category_id']
            save_config(config)
            return jsonify(link)

    return jsonify({'error': '链接不存在'}), 404


@app.route('/api/links/<int:link_id>', methods=['DELETE'])
def delete_link(link_id):
    """删除链接"""
    config = load_config()
    links = config.get('links', [])

    for i, link in enumerate(links):
        if link['id'] == link_id:
            links.pop(i)
            save_config(config)
            return jsonify({'success': True})

    return jsonify({'error': '链接不存在'}), 404


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有分类"""
    config = load_config()
    return jsonify(config.get('categories', []))


@app.route('/api/categories', methods=['POST'])
def add_category():
    """添加新分类"""
    data = request.json
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400

    config = load_config()
    existing_ids = [cat['id'] for cat in config.get('categories', [])]
    new_id = max(existing_ids) + 1 if existing_ids else 1

    new_category = {
        'id': new_id,
        'name': name
    }
    config.setdefault('categories', []).append(new_category)
    save_config(config)

    return jsonify(new_category)


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新分类"""
    data = request.json
    config = load_config()
    categories = config.get('categories', [])

    for category in categories:
        if category['id'] == category_id:
            category['name'] = data.get('name', category['name']).strip()
            save_config(config)
            return jsonify(category)

    return jsonify({'error': '分类不存在'}), 404


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """删除分类"""
    config = load_config()
    categories = config.get('categories', [])

    for i, category in enumerate(categories):
        if category['id'] == category_id:
            categories.pop(i)
            # 将该分类下的链接移到默认分类或第一个分类
            for link in config.get('links', []):
                if link.get('category_id') == category_id:
                    link['category_id'] = categories[0]['id'] if categories else 1
            save_config(config)
            return jsonify({'success': True})

    return jsonify({'error': '分类不存在'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
