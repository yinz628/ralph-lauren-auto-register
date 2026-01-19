# Ralph Lauren 自动注册系统

Ralph Lauren 自动注册系统是一个自动化工具，用于批量注册 Ralph Lauren 账户并更新用户资料。系统支持代理轮换、人工验证处理和完整的日志记录。

## 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [安装](#安装)
- [配置](#配置)
- [使用方法](#使用方法)
- [人工验证功能](#人工验证功能)
- [故障排除](#故障排除)
- [日志和监控](#日志和监控)

## 功能特性

- ✅ 自动填写注册表单
- ✅ 自动更新用户资料
- ✅ 代理服务器支持和轮换
- ✅ **人工验证处理** - 检测 PerimeterX 挑战并等待用户手动完成
- ✅ 自动流程恢复 - 验证完成后自动继续
- ✅ 完整的日志记录和事件追踪
- ✅ 可配置的超时和重试机制
- ✅ 多次验证支持

## 系统要求

- Python 3.8+
- Playwright (自动安装浏览器)
- 稳定的网络连接
- （可选）代理服务器

## 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd ralph-lauren-auto-register
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装 Playwright 浏览器：
```bash
playwright install chromium
```

## 配置

系统通过 `src/config.py` 文件进行配置。主要配置项包括：

### 基础配置

```python
# 浏览器配置
HEADLESS: bool = False  # 人工验证需要设置为 False
BROWSER_TIMEOUT: int = 30000  # 毫秒

# 注册配置
REGISTRATION_URL: str = "https://www.ralphlauren.com/..."
MAX_ITERATIONS: int = 10
ITERATION_DELAY: int = 5  # 秒
```

### 人工验证配置

```python
# 人工验证超时时间（秒）
MANUAL_VERIFICATION_TIMEOUT: int = 120

# 是否显示验证通知
ENABLE_VERIFICATION_NOTIFICATIONS: bool = True

# 单次迭代最大验证次数
MAX_VERIFICATION_ATTEMPTS: int = 3
```

### 代理配置

```python
# 代理服务器列表
PROXIES: List[str] = [
    "http://username:password@proxy1.example.com:8080",
    "http://username:password@proxy2.example.com:8080"
]

# 是否启用代理轮换
ENABLE_PROXY_ROTATION: bool = True
```

## 使用方法

### 基本使用

运行主程序：

```bash
python main.py
```

系统将自动执行以下流程：
1. 加载配置
2. 初始化浏览器（使用代理）
3. 填写注册表单
4. 提交表单
5. **检测 PerimeterX 验证挑战**
6. **等待用户手动完成验证**
7. 验证成功后自动继续
8. 更新用户资料
9. 保存账户信息

### 命令行参数

```bash
# 指定迭代次数
python main.py --iterations 5

# 使用特定配置文件
python main.py --config custom_config.py

# 启用详细日志
python main.py --verbose
```

## 人工验证功能

### 工作原理

当系统检测到 PerimeterX 验证挑战时，会自动进入人工验证模式：

1. **检测挑战**：系统监控页面，检测 PerimeterX 验证元素
2. **暂停自动化**：立即停止所有自动化操作
3. **显示通知**：在控制台显示清晰的通知消息
4. **等待用户**：保持浏览器窗口可见，等待用户手动完成验证
5. **监控完成**：持续监控页面 URL 变化和挑战元素消失
6. **自动恢复**：验证成功后自动继续后续流程

### 验证流程示例

```
╔════════════════════════════════════════════════════════════╗
║  PerimeterX 验证挑战检测                                    ║
║                                                            ║
║  请在浏览器中手动完成验证                                    ║
║  验证成功后页面将自动跳转                                    ║
║                                                            ║
║  超时时间: 120 秒                                           ║
║  剩余时间: 115 秒                                           ║
╚════════════════════════════════════════════════════════════╝
```

### 用户操作步骤

当看到上述通知时：

1. **切换到浏览器窗口**：系统会保持浏览器窗口可见
2. **完成验证挑战**：
   - 按住不放验证：按住按钮直到进度条完成
   - 复选框验证：勾选"我不是机器人"
   - 滑块验证：拖动滑块到正确位置
3. **等待自动跳转**：验证成功后页面会自动跳转
4. **系统自动恢复**：无需任何操作，系统会自动继续

### 配置选项详解

#### MANUAL_VERIFICATION_TIMEOUT

等待用户完成验证的最大时间（秒）。

```python
MANUAL_VERIFICATION_TIMEOUT: int = 120  # 默认 2 分钟
```

- **推荐值**：120-180 秒
- **最小值**：60 秒（给用户足够时间）
- **最大值**：300 秒（避免无限等待）

**何时调整**：
- 如果经常超时，增加此值
- 如果希望快速失败，减少此值

#### ENABLE_VERIFICATION_NOTIFICATIONS

是否在控制台显示验证通知。

```python
ENABLE_VERIFICATION_NOTIFICATIONS: bool = True  # 默认启用
```

- `True`：显示详细的通知框和倒计时
- `False`：仅记录日志，不显示通知

**何时禁用**：
- 在无人值守模式下运行
- 通过日志文件监控而非控制台

#### MAX_VERIFICATION_ATTEMPTS

单次迭代中允许的最大验证次数。

```python
MAX_VERIFICATION_ATTEMPTS: int = 3  # 默认 3 次
```

- 超过此次数后，当前迭代标记为失败
- 系统会继续下一次迭代

**何时调整**：
- 如果网站频繁出现多次验证，增加此值
- 如果希望快速失败，减少此值

### 支持的验证类型

系统可以检测以下 PerimeterX 验证类型：

1. **Press and Hold**（按住不放）
   - 选择器：`#px-captcha`, `.px-captcha`
   - 用户操作：按住按钮直到进度条完成

2. **Checkbox**（复选框）
   - 选择器：`.g-recaptcha`, `#recaptcha`
   - 用户操作：勾选"我不是机器人"

3. **Slider**（滑块）
   - 选择器：`.slider-captcha`, `#slider`
   - 用户操作：拖动滑块到正确位置

4. **Modal Challenge**（模态框挑战）
   - 选择器：`[id*="challenge"]`, `[class*="challenge"]`
   - 用户操作：根据提示完成验证

### 验证完成检测

系统通过以下方式检测验证完成：

1. **URL 变化**：页面跳转到预期的成功 URL
2. **元素消失**：所有 PerimeterX 挑战元素从页面消失
3. **页面状态**：页面加载完成且处于稳定状态

### 多次验证处理

在某些情况下，一次注册流程可能遇到多次验证挑战：

- **注册提交后**：第一次验证
- **资料更新后**：第二次验证
- **其他操作后**：可能的额外验证

系统会独立处理每次验证，使用相同的流程：

```
迭代 1:
  ├─ 填写表单
  ├─ 提交 → 验证 1 (成功)
  ├─ 更新资料 → 验证 2 (成功)
  └─ 完成

迭代 2:
  ├─ 填写表单
  ├─ 提交 → 验证 1 (成功)
  ├─ 更新资料 → 验证 2 (超时)
  └─ 失败 (继续下一次迭代)
```

## 故障排除

### 常见问题

#### 1. 验证超时

**症状**：
```
[MANUAL_VERIFICATION] Verification timed out after 120s
```

**原因**：
- 用户未在规定时间内完成验证
- 网络延迟导致页面跳转缓慢
- 验证挑战过于复杂

**解决方案**：
```python
# 增加超时时间
MANUAL_VERIFICATION_TIMEOUT: int = 180  # 3 分钟
```

#### 2. 检测不到验证挑战

**症状**：
- 页面显示验证挑战，但系统没有暂停
- 系统继续执行导致失败

**原因**：
- PerimeterX 使用了新的选择器
- 挑战元素加载延迟

**解决方案**：
1. 检查日志中的选择器信息
2. 在 `src/manual_verification.py` 中添加新选择器：
```python
PERIMETERX_SELECTORS = [
    "#px-captcha",
    ".px-captcha",
    # 添加新发现的选择器
    ".new-challenge-selector"
]
```

#### 3. 验证完成但系统未恢复

**症状**：
- 手动完成验证后页面已跳转
- 系统仍在等待状态

**原因**：
- URL 模式不匹配
- 页面跳转到意外的 URL

**解决方案**：
1. 检查日志中的当前 URL
2. 更新预期 URL 模式：
```python
# 在 submit_and_verify() 中
expected_url = "https://www.ralphlauren.com/profile"  # 更新为实际 URL
```

#### 4. 浏览器窗口不可见

**症状**：
- 无法看到浏览器窗口进行验证

**原因**：
- `HEADLESS` 模式启用

**解决方案**：
```python
# 在 config.py 中
HEADLESS: bool = False  # 必须设置为 False
```

#### 5. 多次验证失败

**症状**：
```
[ERROR] Maximum verification attempts (3) exceeded
```

**原因**：
- 网站对该 IP/代理进行了限制
- 账户注册频率过高

**解决方案**：
1. 增加迭代延迟：
```python
ITERATION_DELAY: int = 10  # 增加到 10 秒
```

2. 轮换代理：
```python
ENABLE_PROXY_ROTATION: bool = True
```

3. 减少每日注册次数

#### 6. 代理连接失败

**症状**：
```
[ERROR] Failed to connect through proxy
```

**原因**：
- 代理服务器不可用
- 代理认证失败
- 网络连接问题

**解决方案**：
1. 验证代理配置：
```python
PROXIES: List[str] = [
    "http://username:password@proxy.example.com:8080"
]
```

2. 测试代理连接：
```bash
curl -x http://username:password@proxy.example.com:8080 https://www.google.com
```

3. 禁用代理测试：
```python
ENABLE_PROXY_ROTATION: bool = False
```

### 调试技巧

#### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 查看浏览器控制台

在验证期间，可以打开浏览器开发者工具（F12）查看：
- 网络请求
- JavaScript 错误
- 控制台日志

#### 截图调试

在关键步骤添加截图：
```python
page.screenshot(path=f"debug_{timestamp}.png")
```

#### 检查元素选择器

使用浏览器开发者工具验证选择器：
1. 右键点击验证元素
2. 选择"检查"
3. 复制选择器
4. 更新代码中的选择器列表

## 日志和监控

### 日志文件

系统生成以下日志文件：

- `main.log`：主程序日志
- `src/main.log`：详细执行日志

### 日志格式

```
[2024-01-19 10:30:45] [INFO] Starting registration iteration 1
[2024-01-19 10:30:50] [MANUAL_VERIFICATION] Challenge detected: press-and-hold
[2024-01-19 10:30:50] [MANUAL_VERIFICATION] Waiting for user (timeout: 120s)
[2024-01-19 10:31:15] [MANUAL_VERIFICATION] Verification completed in 25s
[2024-01-19 10:31:20] [INFO] Registration successful
```

### 验证事件追踪

每次验证都会记录详细信息：

```python
{
    "challenge_type": "press-and-hold",
    "start_time": "2024-01-19T10:30:50",
    "end_time": "2024-01-19T10:31:15",
    "success": true,
    "timeout": false,
    "duration_seconds": 25.0
}
```

### 监控指标

关键指标：
- **验证成功率**：成功验证次数 / 总验证次数
- **平均验证时间**：所有成功验证的平均耗时
- **超时率**：超时次数 / 总验证次数
- **迭代成功率**：成功迭代 / 总迭代次数

## 最佳实践

### 1. 合理设置超时时间

```python
# 根据验证复杂度调整
MANUAL_VERIFICATION_TIMEOUT: int = 120  # 简单验证
MANUAL_VERIFICATION_TIMEOUT: int = 180  # 复杂验证
```

### 2. 使用代理轮换

```python
# 避免 IP 限制
ENABLE_PROXY_ROTATION: bool = True
PROXIES: List[str] = [
    # 至少 3-5 个代理
]
```

### 3. 控制注册频率

```python
# 避免触发反爬虫机制
ITERATION_DELAY: int = 10  # 每次迭代间隔 10 秒
MAX_ITERATIONS: int = 5     # 每次运行最多 5 次
```

### 4. 监控日志

定期检查日志文件，关注：
- 验证失败模式
- 超时频率
- 错误信息

### 5. 保持浏览器可见

```python
# 人工验证必须
HEADLESS: bool = False
```

### 6. 备份账户数据

定期备份生成的账户信息文件。

## 安全注意事项

1. **不要提交敏感信息**：
   - 代理凭证
   - 账户密码
   - 个人信息

2. **使用环境变量**：
```python
import os
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
```

3. **日志脱敏**：
   - 系统自动脱敏邮箱和密码
   - 仅显示部分信息

## 技术支持

如遇到问题：

1. 查看[故障排除](#故障排除)部分
2. 检查日志文件获取详细错误信息
3. 确保配置正确
4. 验证网络连接和代理设置

## 许可证

[添加许可证信息]

## 更新日志

### v2.0.0 - 2024-01-19
- ✨ 新增人工验证功能
- ✨ 自动流程恢复
- ✨ 多次验证支持
- 🗑️ 移除自动化验证代码
- 📝 完善文档和故障排除指南

### v1.0.0 - 2024-01-01
- 🎉 初始版本
- ✨ 基础注册功能
- ✨ 代理支持
