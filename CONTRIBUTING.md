# Contributing to 7Z GUI

欢迎贡献代码！以下是贡献指南。

## 如何贡献

### 报告问题
1. 检查是否已有相同的 Issue
2. 提供清晰的问题描述和复现步骤
3. 附上截图或错误日志（如果适用）

### 提交代码
1. Fork 仓库
2. 创建新分支：`git checkout -b feature/your-feature-name`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature-name`
5. 提交 Pull Request

## 开发环境

### 依赖
- Python 3.8+
- PyQt5
- PyInstaller

### 运行测试
```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py

# 打包应用
pyinstaller --name "7Z GUI" --windowed --add-data "src/resources:resources" src/main.py
```

## 代码规范

- 遵循 PEP 8 代码规范
- 保持代码简洁清晰
- 添加必要的注释
- 确保所有功能都经过测试

## 许可证

提交的代码将遵循 MIT 许可证。

## 致谢

感谢所有贡献者！