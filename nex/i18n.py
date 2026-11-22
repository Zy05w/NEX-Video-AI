"""极简界面翻译层：中文原文作为键，英文为译文。

用法：t("添加任务")、t("已添加 {count} 个任务", count=3)。
中文模式下原样返回；英文模式查表，缺失时回退中文。
"""

from __future__ import annotations

LANGUAGE_LABELS = {"zh": "简体中文", "en": "English"}

_current = "zh"


def set_language(language: str) -> None:
    global _current
    _current = "en" if language == "en" else "zh"


def get_language() -> str:
    return _current


def t(text: str, **kwargs) -> str:
    if _current == "en":
        text = EN.get(text, text)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


EN = {
    # 应用与主窗口
    "NEX 视频增强": "NEX Video Enhancer",
    "AI 视频超分 · 补帧": "AI Video Upscaling & Frame Interpolation",
    "添加任务": "Add Task",
    "开始全部": "Start All",
    "设置": "Settings",
    "使用教程": "User Guide",
    "清空视图": "Clear View",
    "保存": "Save",
    "取消": "Cancel",
    "确定": "OK",
    "退出": "Exit",
    "是": "Yes",
    "否": "No",
    "启用": "Enable",
    "删除": "Delete",
    "重试": "Retry",
    "浏览...": "Browse...",
    "选择视频...": "Choose Video...",
    "添加": "Add",
    "知道了": "Got it",
    "文件名": "File Name",
    "状态": "Status",
    "进度": "Progress",
    "目标参数": "Target",
    "操作": "Actions",
    "等待中": "Pending",
    "处理中": "Processing",
    "已完成": "Completed",
    "失败": "Failed",
    "已取消": "Cancelled",
    "日志 · 未选择任务": "Log · No task selected",
    "日志 · {name}": "Log · {name}",
    "就绪": "Ready",
    "就绪 · 共 {count} 个任务": "Ready · {count} task(s)",
    "已恢复 {count} 个未完成任务为等待中": "Recovered {count} unfinished task(s) to Pending",
    "已添加 {count} 个任务": "Added {count} task(s)",
    "已开始 {count} 个任务": "Started {count} task(s)",
    "没有等待中的任务": "No pending tasks",
    "正在取消任务...": "Cancelling...",
    "已取消：{name}": "Cancelled: {name}",
    "已重新加入队列：{name}": "Requeued: {name}",
    "无法删除": "Cannot Delete",
    "任务正在处理中，请先取消后再删除。": "The task is running. Please cancel it before deleting.",
    "删除任务记录": "Delete Task Record",
    "确定删除「{name}」的记录吗？\n仅删除记录，不会删除视频文件。": "Delete the record for “{name}”?\nOnly the record will be removed; the video file is kept.",
    "已删除任务记录": "Task record deleted",
    "正在处理：{name}": "Processing: {name}",
    "处理中：{stage} · {percent}%": "Processing: {stage} · {percent}%",
    "已完成：{name}": "Completed: {name}",
    "失败：{name} — {message}": "Failed: {name} — {message}",
    "退出软件": "Exit",
    "有任务正在处理，退出将停止当前任务。确定退出吗？": "A task is running. Exiting will stop it. Continue?",
    "（暂无日志）目标参数：{summary}": "(No log yet) Target: {summary}",
    # 添加任务
    "视频文件": "Video File",
    "输出位置": "Output Location",
    "AI 超分": "AI Upscaling",
    "AI 补帧": "AI Frame Interpolation",
    "尚未选择视频文件": "No video selected",
    "默认：源视频同目录": "Default: same folder as source",
    "添加后立即开始": "Start immediately after adding",
    "请先选择要处理的视频文件": "Please select a video file first",
    "请至少开启“超分”或“补帧”中的一项": "Enable at least one of Upscaling or Frame Interpolation",
    "已选择 {count} 个文件": "{count} files selected",
    "选择视频文件": "Choose Video Files",
    "选择输出文件夹": "Choose Output Folder",
    "选择默认输出文件夹": "Choose Default Output Folder",
    "视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v);;所有文件 (*.*)": (
        "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v);;All files (*.*)"
    ),
    "动漫视频（推荐）": "Anime Video (Recommended)",
    "写实通用": "Realistic / General",
    "动漫插画": "Anime Illustration",
    "rife-v4.6（推荐）": "rife-v4.6 (Recommended)",
    "rife-anime（动漫）": "rife-anime (Anime)",
    "RIFE 4.25（PyTorch，需额外环境）": "RIFE 4.25 (PyTorch, extra environment required)",
    "Practical-RIFE 4.25 环境不完整：\n{files}": (
        "Practical-RIFE 4.25 environment is incomplete:\n{files}"
    ),
    "Practical-RIFE 输出帧数不符：{count}/{expected}": (
        "Practical-RIFE frame count mismatch: {count}/{expected}"
    ),
    # 设置
    "默认输出目录": "Default Output Folder",
    "视频编码器": "Video Encoder",
    "自动（推荐）": "Auto (Recommended)",
    "软件编码 x264（兼容）": "Software x264 (Compatible)",
    "硬件编码 NVENC（需驱动 610+）": "Hardware NVENC (Driver 610+)",
    "显卡选择": "GPU",
    "GPU {id}（自动）": "GPU {id} (Auto)",
    "日志保留天数": "Log Retention (days)",
    "温度保护上限 (°C)": "Temperature Limit (°C)",
    "界面语言": "Language",
    "版本 {version} · 开源组件：Real-ESRGAN（BSD-3）、RIFE（MIT）、FFmpeg（GPL v3）、PySide6（LGPLv3）\n许可证文本见安装目录 licenses/。温度保护上限设为 0 表示关闭。": (
        "Version {version} · Open-source: Real-ESRGAN (BSD-3), RIFE (MIT), "
        "FFmpeg (GPL v3), PySide6 (LGPLv3)\n"
        "License texts are in the licenses/ folder. "
        "Set the temperature limit to 0 to disable it."
    ),
    "语言已更改": "Language Changed",
    "语言设置将在重启软件后生效。是否立即重启？": "The language change takes effect after restarting. Restart now?",
    "有任务正在处理，请在任务结束后手动重启软件使语言生效。": "A task is running. Please restart the app manually after it finishes to apply the language.",
    # 任务摘要
    "不超分": "No Upscaling",
    "超分": "Upscaling",
    "不补帧": "No Interpolation",
    "补帧": "Interpolation",
    # 阶段
    "探测": "Probe",
    "规划": "Plan",
    "温度": "Temperature",
    "抽帧": "Extract",
    "合成": "Encode",
    "完成": "Done",
    "错误": "Error",
    "无": "none",
    "引擎": "Engine",
    # 日志与错误
    "{name} · {width}x{height} · {fps}fps · {duration}s · 音轨 {audio}": (
        "{name} · {width}x{height} · {fps}fps · {duration}s · Audio {audio}"
    ),
    "显卡 {name} · 初始 {temp}°C · 保护上限 {limit}°C": (
        "GPU {name} · Initial {temp}°C · Limit {limit}°C"
    ),
    "未检测到 nvidia-smi，跳过温度监控": "nvidia-smi not found; temperature monitoring disabled",
    "GPU {temp}°C · 占用 {util}% · 功耗 {power}W · 显存 {mem}MiB": (
        "GPU {temp}°C · Util {util}% · Power {power}W · VRAM {mem}MiB"
    ),
    "温度达到 {temp}°C（保护上限 {limit}°C），正在安全停止任务": (
        "Temperature reached {temp}°C (limit {limit}°C); stopping the task safely"
    ),
    "超分：{model}，运行倍数 {scale}x（跳过 AI，直接缩放），输出 {width}x{height}": (
        "Upscaling: {model}, scale {scale}x (AI skipped, resize only), output {width}x{height}"
    ),
    "超分：{model}，运行倍数 {scale}x，输出 {width}x{height}": (
        "Upscaling: {model}, scale {scale}x, output {width}x{height}"
    ),
    "补帧：{model}，{note}，插值 {passes} 遍，输出 {fps}fps": (
        "Interpolation: {model}, {note}, {passes} pass(es), output {fps}fps"
    ),
    "未启用": "disabled",
    "补帧：未启用": "Interpolation: disabled",
    "开始": "started",
    "完成：{count} 帧，耗时 {seconds}s": "done: {count} frames in {seconds}s",
    "开始：{model} {scale}x，共 {count} 帧": "started: {model} {scale}x, {count} frames",
    "第 {index}/{total} 遍开始：{count} 帧": "pass {index}/{total} started: {count} frames",
    "第 {index} 遍完成：{count} 帧，耗时 {seconds}s": "pass {index} done: {count} frames in {seconds}s",
    "编码器 auto → x264（NVENC 需驱动 ≥610.00，暂用软件编码）": (
        "Encoder auto → x264 (NVENC requires driver ≥610.00; using software encoding)"
    ),
    "开始：{width}x{height} @ {fps}fps，编码器 {encoder}": (
        "started: {width}x{height} @ {fps}fps, encoder {encoder}"
    ),
    "NVENC 失败，自动回退 x264：{message}": "NVENC failed; falling back to x264: {message}",
    "完成：{path}，耗时 {seconds}s": "done: {path} in {seconds}s",
    "总耗时 {seconds}s · 输出 {width}x{height} @ {fps}fps · {frames} 帧": (
        "Total {seconds}s · Output {width}x{height} @ {fps}fps · {frames} frames"
    ),
    "任务已取消": "Task cancelled",
    "显卡温度过高（{temp}°C，保护上限 {limit}°C），已安全停止任务。请检查散热后重试。": (
        "GPU temperature too high ({temp}°C, limit {limit}°C). "
        "The task was stopped safely. Check cooling and retry."
    ),
    "内部错误：{error}": "Internal error: {error}",
    "任务数据损坏：{id}": "Corrupted task data: {id}",
    "未知的超分模型：{model}": "Unknown upscaling model: {model}",
    "超分倍数与目标高度只能二选一": "Specify either a scale or a target height, not both",
    "未知的补帧模型：{model}": "Unknown interpolation model: {model}",
    "补帧倍数与目标帧率只能二选一": "Specify either a multiplier or a target frame rate, not both",
    "补帧倍数仅支持 2x 或 4x": "Interpolation multiplier supports only 2x or 4x",
    "目标 {target}fps": "target {target}fps",
    "目标 {target}fps 不高于源帧率，跳过": "Target {target}fps is not above source fps; skipped",
    "目标 {target}fps 超过 8x，已限制为 {fps}fps": "Target {target}fps exceeds 8x; limited to {fps}fps",
    "缺少引擎文件：\n{files}": "Missing engine files:\n{files}",
    "请至少开启超分或补帧中的一项": "Enable at least one of upscaling or interpolation",
    "没有可执行的增强步骤（超分被跳过且补帧未生效）": (
        "No enhancement step to run (upscaling skipped and interpolation inactive)"
    ),
    "抽帧失败：没有生成任何帧": "Frame extraction failed: no frames generated",
    "超分失败：没有生成任何帧": "Upscaling failed: no frames generated",
    "补帧失败：没有生成任何帧": "Interpolation failed: no frames generated",
    "合成失败：输出文件不存在或为空": "Encoding failed: output file missing or empty",
    "无法创建输出目录：{error}": "Cannot create output folder: {error}",
    "文件不存在：{path}": "File not found: {path}",
    "无法读取视频信息": "Cannot read video information",
    "视频信息解析失败": "Failed to parse video information",
    "文件中没有视频流": "No video stream found",
    "无法识别视频帧率": "Cannot detect frame rate",
    "无法启动引擎：{error}": "Cannot start engine: {error}",
    "引擎执行失败（退出码 {code}）": "Engine failed (exit code {code})",
    "{stage}失败：{message}": "{stage} failed: {message}",
    "{stage}失败（退出码 {code}）：{message}": "{stage} failed (exit code {code}): {message}",
}
