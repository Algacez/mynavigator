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


def normalize_categories(config):
    """确保分类有顺序并按顺序排序"""
    categories = config.get('categories', [])
    changed = False

    for i, category in enumerate(categories):
        if 'order' not in category:
            category['order'] = i + 1
            changed = True

    categories.sort(key=lambda x: x.get('order', 0))

    for i, category in enumerate(categories, start=1):
        if category.get('order') != i:
            category['order'] = i
            changed = True

    if changed:
        save_config(config)

    return categories


def normalize_links(config):
    """确保链接在各自分类内有顺序并排序"""
    links = config.get('links', [])
    changed = False

    links_by_category = {}
    for link in links:
        links_by_category.setdefault(link.get('category_id', 1), []).append(link)

    for category_id, category_links in links_by_category.items():
        category_links.sort(key=lambda x: x.get('order', 0))
        for i, link in enumerate(category_links, start=1):
            if link.get('order') != i:
                link['order'] = i
                changed = True

    if changed:
        save_config(config)

    return links


def group_links_by_category(links):
    links_by_category = {}
    for link in links:
        links_by_category.setdefault(link.get('category_id', 1), []).append(link)

    for category_id, category_links in links_by_category.items():
        category_links.sort(key=lambda x: x.get('order', 0))

    return links_by_category


@app.route('/')
def index():
    """主导航页面"""
    config = load_config()
    categories = normalize_categories(config)
    links = normalize_links(config)
    links_by_category = group_links_by_category(links)

    return render_template('index.html', links_by_category=links_by_category, categories=categories)


@app.route('/admin')
def admin():
    """管理页面"""
    config = load_config()
    categories = normalize_categories(config)
    links = normalize_links(config)
    links_by_category = group_links_by_category(links)

    return render_template('admin.html', links_by_category=links_by_category, categories=categories)


@app.route('/api/links', methods=['GET'])
def get_links():
    """获取所有链接，按排序字段排序"""
    config = load_config()
    categories = normalize_categories(config)
    links = normalize_links(config)

    category_order_map = {cat['id']: cat.get('order', 0) for cat in categories}
    links = sorted(
        links,
        key=lambda x: (category_order_map.get(x.get('category_id', 1), 0), x.get('order', 0))
    )

    return jsonify({'links': links, 'categories': categories})


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
    normalize_categories(config)
    existing_ids = [link['id'] for link in config.get('links', [])]
    new_id = max(existing_ids) + 1 if existing_ids else 1

    # 获取当前分类下最大的order值
    links = config.get('links', [])
    category_links = [link for link in links if link.get('category_id') == category_id]
    max_order = max([link.get('order', 0) for link in category_links]) if category_links else 0

    new_link = {
        'id': new_id,
        'name': name,
        'url': url,
        'category_id': category_id,
        'order': max_order + 1
    }
    config.setdefault('links', []).append(new_link)
    save_config(config)

    return jsonify(new_link)


@app.route('/api/links/<int:link_id>', methods=['PUT'])
def update_link(link_id):
    """更新链接"""
    data = request.json
    config = load_config()
    normalize_categories(config)
    links = config.get('links', [])

    for link in links:
        if link['id'] == link_id:
            old_category_id = link.get('category_id')
            link['name'] = data.get('name', link['name']).strip()
            link['url'] = data.get('url', link['url']).strip()
            if 'category_id' in data:
                link['category_id'] = data['category_id']

            if 'category_id' in data and data['category_id'] != old_category_id:
                new_category_id = data['category_id']
                category_links = [l for l in links if l.get('category_id') == new_category_id]
                max_order = max([l.get('order', 0) for l in category_links]) if category_links else 0
                link['order'] = max_order + 1

            normalize_links(config)
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


@app.route('/api/links/<int:link_id>/move', methods=['POST'])
def move_link(link_id):
    """移动链接顺序"""
    data = request.json
    direction = data.get('direction')  # 'up' or 'down'

    if direction not in ['up', 'down']:
        return jsonify({'error': '方向只能是up或down'}), 400

    config = load_config()
    normalize_categories(config)
    links = normalize_links(config)

    # 找到当前链接的索引
    current_link = next((link for link in links if link['id'] == link_id), None)
    if current_link is None:
        return jsonify({'error': '链接不存在'}), 404

    category_id = current_link.get('category_id', 1)
    category_links = [link for link in links if link.get('category_id') == category_id]
    category_links.sort(key=lambda x: x.get('order', 0))

    current_index = None
    for i, link in enumerate(category_links):
        if link['id'] == link_id:
            current_index = i
            break

    if current_index is None:
        return jsonify({'error': '链接不存在'}), 404

    # 计算目标索引
    if direction == 'up':
        if current_index == 0:
            return jsonify({'error': '已经在最前面了'}), 400
        target_index = current_index - 1
    else:  # down
        if current_index == len(links) - 1:
            return jsonify({'error': '已经在最后面了'}), 400
        target_index = current_index + 1

    # 交换order值
    current_order = category_links[current_index]['order']
    target_order = category_links[target_index]['order']

    category_links[current_index]['order'] = target_order
    category_links[target_index]['order'] = current_order

    save_config(config)
    return jsonify({'success': True})


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有分类"""
    config = load_config()
    categories = normalize_categories(config)
    return jsonify(categories)


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
    max_order = max([cat.get('order', 0) for cat in config.get('categories', [])]) if config.get('categories') else 0

    new_category = {
        'id': new_id,
        'name': name,
        'order': max_order + 1
    }
    config.setdefault('categories', []).append(new_category)
    save_config(config)

    return jsonify(new_category)


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新分类"""
    data = request.json
    config = load_config()
    normalize_categories(config)
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
            normalize_categories(config)
            normalize_links(config)
            save_config(config)
            return jsonify({'success': True})

    return jsonify({'error': '分类不存在'}), 404


@app.route('/api/categories/<int:category_id>/move', methods=['POST'])
def move_category(category_id):
    """移动分类顺序"""
    data = request.json
    direction = data.get('direction')  # 'up' or 'down'

    if direction not in ['up', 'down']:
        return jsonify({'error': '方向只能是up或down'}), 400

    config = load_config()
    categories = normalize_categories(config)

    current_index = None
    for i, category in enumerate(categories):
        if category['id'] == category_id:
            current_index = i
            break

    if current_index is None:
        return jsonify({'error': '分类不存在'}), 404

    if direction == 'up':
        if current_index == 0:
            return jsonify({'error': '已经在最前面了'}), 400
        target_index = current_index - 1
    else:  # down
        if current_index == len(categories) - 1:
            return jsonify({'error': '已经在最后面了'}), 400
        target_index = current_index + 1

    current_order = categories[current_index]['order']
    target_order = categories[target_index]['order']

    categories[current_index]['order'] = target_order
    categories[target_index]['order'] = current_order

    save_config(config)
    return jsonify({'success': True})


@app.route('/api/categories/<int:category_id>/batch-update-ip', methods=['POST'])
def batch_update_ip(category_id):
    """批量更新分类下所有链接的 IP 地址"""
    data = request.json
    new_ip = data.get('ip', '').strip()

    if not new_ip:
        return jsonify({'error': 'IP 地址不能为空'}), 400

    config = load_config()
    normalize_categories(config)
    links = config.get('links', [])
    updated_count = 0

    import re
    ip_pattern = re.compile(r'^(https?://)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?(/.*)?$')

    for link in links:
        if link.get('category_id') == category_id:
            url = link.get('url', '')
            match = ip_pattern.match(url)
            if match:
                protocol = match.group(1) or 'http://'
                port_and_path = match.group(4) or ''
                port_match = re.search(r':(\d+)', url)
                port_str = ''
                path_str = ''
                if port_match:
                    port_str = ':' + port_match.group(1)
                path_match = re.search(r':\d+(/.*)$', url)
                if path_match:
                    path_str = path_match.group(1)
                elif not port_match and '/' in url.split('://')[-1]:
                    path_str = '/' + url.split('://')[-1].split('/', 1)[1] if '://' in url else '/' + url.split('/', 1)[1]
                
                new_url = f"{protocol}{new_ip}{port_str}{path_str}"
                link['url'] = new_url
                updated_count += 1

    save_config(config)
    return jsonify({'success': True, 'updated_count': updated_count})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
