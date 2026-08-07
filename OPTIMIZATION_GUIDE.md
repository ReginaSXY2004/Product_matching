# 竞品库优化指南

## 📋 修改总结

### 1. 修改的文件

#### ✅ `src/config.py`
- **变更**: 添加 `OUTPUT_DIR` 路径配置
- **用途**: 输出文件（results.xlsx, search_log.json）保存到 `data/output/`
- **自动创建**: 输出目录在程序启动时自动创建

#### ✅ `src/search/taobao_search.py`
- **新增函数**: `_detect_captcha(page, body_text)` 
  - 检测滑块验证、安全验证等反爬机制
  - 关键词识别: "滑块验证", "验证码", "suspected robot" 等
  - 返回: `bool` 类型

- **改造函数**: `_search_single_page(page, keyword, topk)`
  - 旧返回格式: `List[dict]` (候选商品列表)
  - 新返回格式: 
    ```python
    {
        "candidates": [...],      # 候选商品列表
        "raw_text": "...",        # 搜索结果页面完整文本
        "captcha_detected": False, # 是否检测到反爬
        "url": "..."              # 最后访问的 URL
    }
    ```

#### ✅ `src/batch/batch_search.py`
- **导入更新**: 
  - 新增: `from src.config import OUTPUT_DIR`
  - 新增: `_detect_captcha` 导入（自动通过返回值获得）

- **输出路径变更**:
  - `OUTPUT_FILE` 从 `DATA_DIR / "search_results.xlsx"` → `OUTPUT_DIR / "search_results.xlsx"`
  - `LOG_FILE` 从 `DATA_DIR / "search_log.json"` → `OUTPUT_DIR / "search_log.json"`

- **输出字段优化**:
  - 新增字段: `raw_text` - 搜索结果页面完整文本
  - 日志新增: `captcha_detected` 字段记录反爬检测

- **统计功能增强**:
  - 添加总耗时统计
  - 添加平均单个耗时
  - 添加失败统计
  - 添加反爬检测统计

---

## 🚀 运行方式

### 方式 1: 小规模测试（推荐）
```bash
cd Product_matching

# 默认测试 10 个商品，Top5 候选
python -m src.batch.batch_search
```

### 方式 2: 自定义参数
```bash
# 修改 src/batch/batch_search.py 的最后一行
if __name__ == "__main__":
    batch_search(
        topk=5,           # 每个商品返回前 5 个候选
        max_products=100  # 搜索前 100 个商品
    )

python -m src.batch.batch_search
```

### 方式 3: Python 脚本调用
```python
from src.batch.batch_search import batch_search

# 搜索 50 个商品，每个取前 3 个候选
batch_search(topk=3, max_products=50)
```

---

## 📊 输出文件结构

### 1. `data/output/search_results.xlsx`
每行代表一个候选商品，可用于后续商品匹配。

| 字段 | 类型 | 说明 |
|------|------|------|
| `goodsId` | int | 本品 ID |
| `source_title` | str | 本品标题 |
| `rank` | int | 淘宝搜索排名 (1-5) |
| `candidate_title` | str | 候选商品标题 |
| `url` | str | 候选商品链接 |
| `raw_text` | str | 搜索结果页面完整文本（用于提取品牌、规格、价格） |

**示例行数**: 100 商品 × Top5 候选 = 500 行

### 2. `data/output/search_log.json`
记录每个商品的搜索过程统计。

```json
{
  "100001": {
    "title": "iPhone 15 Pro Max",
    "status": "success",
    "candidate_num": 5,
    "cost_time": 12.34,
    "captcha_detected": false
  },
  "100002": {
    "title": "MacBook Pro 16",
    "status": "failed",
    "error": "网络超时",
    "cost_time": 30.0,
    "captcha_detected": false
  }
}
```

---

## ⏱️ 性能预估

### 100 商品 × Top5 候选的预期耗时

| 阶段 | 耗时 |
|------|------|
| 浏览器启动 (1 次) | ~3-5s |
| 登录 (第一次或失效时) | ~30-180s（取决于是否需要扫码） |
| 单个搜索 (网页加载 + 提取) | ~8-15s |
| **单个搜索间隔**(防爬) | ~3-8s (随机) |
| 100 个商品总耗时 | **约 30-40 分钟** |

### 详细计算
```
总耗时 = 启动(4s) + 登录(60s) + (搜索(12s) + 间隔(5.5s)) × 100 - 最后一个间隔
       = 4 + 60 + (12 + 5.5) × 100 - 5.5
       ≈ 1760s ≈ 29 分钟
```

**实际可能范围**: 25-50 分钟（取决于网络速度和反爬触发率）

---

## 🔍 反爬检测说明

### 检测机制

#### URL 检测
- `check.taobao.com` - 反爬验证域名
- `passport` - 淘宝登录/验证
- `seccodelogin` - 安全验证登录

#### 页面文本检测
- "滑块验证"、"拖动滑块"
- "安全验证"、"验证码"
- "我是人类"、"suspected robot"
- "请输入验证码"、"perform suspicious"

### 检测到反爬时的行为

1. **不尝试绕过**: 直接记录 `captcha_detected=true`
2. **继续搜索**: 仍然返回已获取的候选结果（可能为空）
3. **记录在日志**: 方便后续分析哪些商品触发了反爬
4. **等待重试**: 间隔 3-8 秒后继续搜索下一个商品

### 触发反爬的原因
- 短时间内大量请求（已通过间隔随机化缓解）
- 浏览器特征识别（Chrome 通常较难被识别）
- IP 地址被标记为爬虫

---

## 📈 扩展到 20000 SKU 的瓶颈分析

### 1. **时间成本** (最主要瓶颈)
- 当前: 100 SKU ≈ 30 分钟 → 20000 SKU ≈ **100 小时**
- **解决方案**:
  - 多进程/多线程 (3-5 个并发浏览器) → 3-5 倍加速
  - 分布式爬虫 (多台服务器) → N 倍加速
  - 预估: 3-5 进程 → 20-30 小时

### 2. **反爬压力增大**
- 当前: 防爬间隔 3-8s
- **扩展到 20000**: 可能触发 IP 限制、账号封禁
- **解决方案**:
  - 使用多个账号（需要登录态轮换）
  - 使用代理 IP 池（成本: ~¥1-5k/月）
  - 增加请求间隔
  - 机器学习识别最优间隔

### 3. **存储成本**
- 当前: 100 × Top5 × raw_text ≈ 50-100MB
- **扩展到 20000**: ≈ 1-2GB（单个 Excel 文件可能有大小限制）
- **解决方案**:
  - 分批输出到多个 Excel 文件
  - 改用 CSV 或 Parquet 格式
  - 数据库存储 (SQLite / PostgreSQL)

### 4. **浏览器资源**
- 当前: 1 个浏览器实例 × 30 分钟
- **扩展到 20000**: 需要并发多个浏览器
- **成本**:
  - 内存: 每个浏览器 ~100-200MB → 1GB for 5 instances
  - CPU: 轻度压力
  - 磁盘: 缓存文件 (可清理)

### 5. **网络和账号管理**
- 淘宝可能检测异常登录行为
- **需要**:
  - 账号池 (5-10 个不同账号)
  - 代理轮换
  - User-Agent 随机化
  - 请求模式分析调整

---

## 💡 优化建议顺序

### 短期（当前）
1. ✅ 完成 100 商品的竞品库构建
2. ✅ 验证 `raw_text` 中的数据是否符合需求
3. ✅ 测试商品匹配算法的效果

### 中期（5000-10000 SKU）
1. 实现多进程并发爬虫 (3-5 进程)
2. 添加异常恢复机制 (断点续爬)
3. 改进反爬间隔策略
4. 预估耗时: 5-10 小时

### 长期（20000+ SKU）
1. 迁移到分布式爬虫框架 (Scrapy / Colly)
2. 使用代理 IP 池
3. 实现多账号轮换
4. 改用数据库存储
5. 预估耗时: 2-5 小时（5-10 台机器）

---

## 🛠️ 故障排查

### 问题 1: 搜索超时
```
错误: 页面加载超时
解决: 增加 wait_for_timeout 时间，或检查网络连接
```

### 问题 2: 反复触发反爬
```
错误: captcha_detected = true
原因: IP 被标记，账号登录异常
解决: 
  1. 增加间隔时间
  2. 更换 IP 或账号
  3. 检查浏览器特征识别
```

### 问题 3: 登录失败
```
错误: 登录超时或扫码失败
解决:
  1. 删除 data/taobao_storage_state.json，重新登录
  2. 确保有人工扫码或输入验证码
  3. 检查网络连接
```

---

## 📝 数据质量说明

### `raw_text` 字段的用途
- **品牌提取**: 通常在商品标题首位
- **规格提取**: 在商品属性栏 (高度、重量、颜色等)
- **价格提取**: 在 `¥XXX.XX` 格式中
- **包装信息**: 在商品描述中

### 后续商品匹配使用
```python
# 示例：从 raw_text 提取品牌
import re
raw_text = row['raw_text']
brand = re.search(r'(Apple|Samsung|小米|华为).*', raw_text)
```

---

## 📞 联系与反馈

如有问题，请查看以下文件:
- `src/config.py` - 路径配置
- `src/search/taobao_search.py` - 搜索逻辑
- `src/batch/batch_search.py` - 批量处理
- `data/output/search_log.json` - 错误日志

