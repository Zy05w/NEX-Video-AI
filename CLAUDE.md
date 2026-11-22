# NEX 视频增强 — 项目工作指引

Windows 11 桌面端 **AI 视频超分 + 补帧**软件（商用产品，类似 SVFI / Topaz Video AI）。
技术栈：Python 3.11 + PySide6（原生控件 + 自定义 QSS）；引擎为 FFmpeg + realesrgan-ncnn-vulkan + rife-ncnn-vulkan（Vulkan / NVIDIA GPU）。

当前阶段：**S7 打磨与终测（已完成，待用户终验）**

## 标准文件索引

| 路径 | 用途 |
|---|---|
| `docs/01-产品需求说明.md` | 需求、功能清单、非目标、已确认决策 |
| `docs/02-技术方案.md` | 架构、处理管线、引擎参数、实测核验记录 |
| `docs/03-界面设计规范.md` | 色板、字体、间距、组件与页面规范 |
| `docs/04-代码工程规范.md` | 目录结构、命名、错误处理、日志、git 提交规范 |
| `docs/05-开发执行步骤.md` | S0-S7 分阶段步骤、每阶段验证与停点 |
| `docs/06-测试与验收标准.md` | 冒烟测试、手工测试清单、验收标准 |
| `docs/07-打包发布与授权合规.md` | 打包流程、许可证清单、发布检查清单 |
| `devlog/` | 开发日志，每天一个文件 `YYYY-MM-DD.md` |
| `devlog/_模板.md` | 日志模板（四节：完成/问题/待办/待确认） |
| `engines/` | 第三方引擎与模型（ffmpeg、realesrgan、rife），不入 git |

## 工作规则（必须遵守）

1. **一次只推进一个阶段**（S0-S7），不提前做后续阶段的事。
2. 阶段结束顺序：**先验证 → 更新受影响 docs → 更新当日 devlog → 向用户汇报 → 等用户确认后再进入下一阶段**。
3. 宣称"完成 / 修好 / 通过"之前，必须实际运行验证命令并看到输出；失败要如实汇报输出。
4. 任何技术决策变化必须同步写入 `docs/02-技术方案.md`。
5. 每次工作会话结束前必须更新 `devlog/当日日期.md`（没有就按模板新建）。
6. 用户是不懂编程的小白：汇报用通俗中文，避免术语堆砌；重大取舍先问用户。
7. 不擅自扩大范围；发现新需求先记入 devlog 待办并询问用户。
8. 代码遵循 `docs/04-代码工程规范.md`；界面遵循 `docs/03-界面设计规范.md`。
9. 界面文案必须通过 `nex/i18n.py` 的 `t()` 输出，新增文案同步补充英文；状态、阶段、日志与错误同样走翻译。

## 常用命令

| 用途 | 命令 | 可用阶段 |
|---|---|---|
| 启动界面 | `.venv\Scripts\python.exe -m nex` 或双击 `启动NEX.bat` | S2 起 |
| 命令行处理 | `.venv\Scripts\python.exe -m nex.cli 输入.mp4 --sr realesr-animevideov3 --sr-scale 2` | S3 起 |
| 命令行补帧 | `.venv\Scripts\python.exe -m nex.cli 输入.mp4 --fi rife-v4.6 --fi-mult 2` | S3 起 |
| 拖入视频试用 | 把视频拖到 `拖入视频测试.bat` 上，按菜单选择 | S3 起 |
| 本地备份 | 双击 `备份项目.bat`（输出到 `项目上级目录/NEX-backups`，含 Git 历史，排除引擎/虚拟环境） | S5 起 |
| 运行测试 | `.venv\Scripts\python.exe -m pytest -q` | S3 起 |
| 4.25 补帧测试 | `.venv-rife\Scripts\python.exe -m nex.cli 输入.mp4 --fi practical-rife-4.25 --fi-mult 2` | S5 起 |
| 打包程序 | `pyinstaller build/nex.spec` → `dist\NEX` | S6 起 |
| 编译安装包 | `ISCC.exe build\installer.iss` → `dist\installer\NEX_Setup_0.1.0.exe` | S6 起 |
| 安装后自检 | `NEX.exe --self-test`（报告 `%TEMP%\NEX_selftest.txt`） | S6 起 |

> 显卡温度保护默认开启（88°C 上限）；CLI 可加 `--temp-limit 90` 调整，`--temp-limit 0` 关闭。
> Practical-RIFE 4.25 使用独立 `.venv-rife`（torch 2.11.0+cu128）；主程序仅通过子进程调用，v1 默认不随安装包分发。
