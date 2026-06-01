# 基于 Agent 的图书进销存系统

这是一个适合课堂展示的最低可行版本，包含传统图书进销存功能和一个 Agent 自然语言入口。

## 技术栈

- 前端：HTML + CSS + JavaScript
- 后端：Python Flask
- 数据库：SQLite
- AI：DeepSeek API，可选；未配置 API Key 时自动使用本地规则解析

## 运行方式

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

打开浏览器访问：

```text
http://127.0.0.1:5000
```

如果要启用 DeepSeek API：

```powershell
$env:DEEPSEEK_API_KEY="你的 API Key"
python app.py
```

不配置 API Key 也能完成课堂演示，系统会使用 `agent.py` 里的本地规则识别常用管理指令。

## 已完成功能

### 传统图书管理系统

- 图书管理：添加、删除、修改、查询图书
- 库存管理：查看库存、库存预警
- 进货管理：记录进货数量，自动增加库存
- 销售管理：记录卖出图书，自动减少库存
- 数据统计：总库存、总销量、销售额、销量排行、低库存列表

### Agent 对话入口

支持示例：

```text
查询库存少于 10 本的书
添加一本《算法导论》，价格 88，库存 15
统计销量最高的 5 本书
把《C++ Primer》的库存增加 20 本
卖出《数据结构》2 本
查询《数据结构》
把《数据结构》的价格改为 50
把《活着》的作者改为 余华
把《高等数学》的分类改为 教材
把《算法导论》的书名改为《算法导论第三版》
删除《算法导论》
```

## 核心设计

Agent 不直接操作数据库，而是先识别用户意图，再调用系统已经封装好的工具函数：

```text
用户输入
  ↓
agent.py 识别意图和参数
  ↓
tools.py 调用工具函数
  ↓
SQLite 数据库
  ↓
返回执行结果
```

主要工具函数：

```text
add_book()        添加图书
list_books()      查询图书
update_stock()    修改库存
update_book_info() 修改图书信息
delete_book()     删除图书
record_purchase() 记录进货
record_sale()     记录销售
low_stock_alert() 库存预警
top_sales()       销量统计
```

## 课堂展示建议

1. 先展示传统方式：在左侧表单添加一本书，再用查询框查库存。
2. 展示库存和销售：选择一本书，记录销售，说明库存会自动减少。
3. 展示 Agent 方式：输入“查询库存少于 10 本的书”，系统直接返回低库存结果。
4. 展示 Agent 自动调用工具：输入“把《C++ Primer》的库存增加 20 本”，页面库存同步变化。
5. 总结对比：传统系统是“人按系统流程操作”，Agent 系统是“人提出目标，Agent 自动选择功能完成任务”。

## 文件结构

```text
app.py              Flask 路由和 API
database.py         SQLite 初始化和连接
tools.py            系统工具函数
agent.py            Agent 意图识别和工具调度
templates/index.html
static/styles.css
static/app.js
requirements.txt
```
