# tg-auto

轻量级 Telegram 自动化工具箱（Python + Telethon），当前功能：通过 **两级内联按钮**领取每日 Token。代码统一托管在 GitHub；Debian 13 负责运行。与已有的 `tdl-bot` **相互独立**。

> 已在 Debian 上实测：`login.py` 首次授权、`inspect_buttons.py` 只读按钮探测、`checkin.py --navigate-only` 一级导航、`checkin.py --execute` 二级领取成功。安装/卸载脚本已进行静态检查；尚需在你的实际 Debian 环境中验收。

## 1. 文件布局与配置来源

| 位置 | 用途 | 删除后影响 |
| --- | --- | --- |
| `~/apps/tg-auto/` | GitHub 拉取的代码、`.venv`、脚本 | 需重新克隆并安装依赖 |
| `~/.config/tg-auto/api_id` | Telegram app ID；单行整数 | 无法连接 Telegram |
| `~/.config/tg-auto/api_hash` | Telegram app hash；单行密钥 | 无法连接 Telegram |
| `~/.config/tg-auto/settings.env` | 本机普通配置（环境变量形式） | 无法从服务文件加载配置 |
| `~/.local/state/tg-auto/tg_auto.session` | 个人账号已授权的 Telethon 会话 | 需要重新登录 |
| `~/.config/systemd/user/tg-auto.service` | 用户级一次性签到服务 | 无法通过 systemd 运行 |
| `~/.config/systemd/user/tg-auto.timer` | 用户级每日调度器 | 不会再定时签到 |
| systemd journal | 历史日志（`journalctl --user`） | 系统统一管理，不随项目卸载清除 |

沿用 `tdl-bot` 的约定：代码放 `~/apps/`，敏感配置放 `~/.config/`，运行状态放 `~/.local/state/`。Telegram API 凭据与 Session **绝不能提交 GitHub**。`api_id`/`api_hash` 是 Telegram 开发者应用凭据，而不是 BotFather 的 bot token。两者不可混用。

`settings.env`（参考 `config/settings.env.example`）：

```dotenv
TG_AUTO_BOT_USERNAME=your_real_bot_username
TG_AUTO_PROXY=socks5://127.0.0.1:2080
```

- `TG_AUTO_BOT_USERNAME`：目标 Bot 的用户名，不带 `@` 也可以；不能留在 `example_bot`。
- `TG_AUTO_PROXY`：可选；示例使用 **Debian 宿主机**上的 Throne SOCKS5 代理。设为空值表示直连。需确保代理正在运行。
- 签到时刻不在 `settings.env` 设置，而由 `systemd/tg-auto.timer` 的 `OnCalendar` 控制。
- `TG_AUTO_LOG_LEVEL` 目前**未接入** Python 日志系统，不用配置。运行结果通过 `journalctl --user -u tg-auto.service` 查阅。
- `settings.env` 可被 systemd 的 `EnvironmentFile` 加载；程序也会自行读取本机配置。脚本只更新缺失文件，不覆盖你已存在的配置。
- 建议：配置目录 `700`，API 文件、`settings.env` 和 Session `600`。

## 2. 首次安装（Debian 13）

使用普通 Linux 用户（例如 `xiaomo`），**不要以 root 或 `sudo bash` 运行脚本**。脚本固定使用该用户的 `$HOME`。安装 `tg-auto` 不需要运行青龙。

系统准备：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
# Debian 13 如果 venv 仍提示缺少 ensurepip：
sudo apt install -y python3.13-venv
```

系统级 `python3-pip` **不是必需的**：`venv` 可以在虚拟环境内提供 pip。不要对 Debian 系统 Python 强制使用 `pip install --break-system-packages`。

仓库 Public 时可以直接 HTTPS 克隆（不要求 GitHub SSH 密钥）；若你将仓库改回 Private，请使用已授权的 SSH/HTTPS 方式：

```bash
mkdir -p ~/apps
git clone https://github.com/Jankinsu/tg-auto.git ~/apps/tg-auto
cd ~/apps/tg-auto
bash scripts/install.sh
```

**一键安装脚本会：**

1. 检查依赖命令、建立独立配置和状态目录；如果缺少 `api_id`/`api_hash`，在交互式终端安全询问并写入本机文件。
2. 仅在 `settings.env` 不存在时，从模板创建它（需填写真实 `TG_AUTO_BOT_USERNAME`）。
3. 创建/复用 `.venv`，安装 `requirements.txt` 依赖；首次没有 Session 时交互运行 `login.py`。
4. 安装 **用户级** `tg-auto.service` 和 `tg-auto.timer`；如原有 unit 内容不同，会先备份到同目录 `*.backup.*`。
5. **默认不启用定时任务**，避免尚未核对时区/领取状态就自动执行。

如果此前已经完成 Telegram 登录，脚本会保留原 Session，不会要求再次输入验证码；如果缺少 Python venv 组件，则先按报错安装相应 Debian 包并重新运行脚本。

首次安装后编辑：

```bash
nano ~/.config/tg-auto/settings.env
```

然后测试（`--navigate-only` 只进入二级菜单，`--execute` 才真正领取）：

```bash
cd ~/apps/tg-auto
.venv/bin/python inspect_buttons.py
.venv/bin/python checkin.py --navigate-only
.venv/bin/python checkin.py --execute
```

## 3. 开启每日自动签到

默认定时配置在 `systemd/tg-auto.timer`：每天 **09:10（Debian 的本地时区）**，并随机延迟最多五分钟。先确认 Bot 的额度重置时间，并根据需要修改仓库中的 timer 模板后重新执行安装脚本同步到 systemd（个人修改的原 unit 会先备份）。

```bash
timedatectl
systemctl --user start tg-auto.service
systemctl --user status tg-auto.service
journalctl --user -u tg-auto.service -n 50 --no-pager
```

首次确认服务正常后，启用 timer：

```bash
systemctl --user enable --now tg-auto.timer
systemctl --user list-timers --all tg-auto.timer
```

也可以在安装时**明确选择**自动启用（前提是已配置好真实 Bot 名称、时区并核验服务）：

```bash
bash scripts/install.sh --enable-timer
```

`Persistent=true`：错过的日历时间可能在定时器重新激活后补执行一次。签到程序本身会检查二级菜单的“已领取”状态，不会主动重复领取，也不针对不明确的结果无限重试。系统时钟和 Telegram Bot 的重置时区不一定相同。

为了让用户级 timer 在 SSH 退出或重启后运行，可查看：

```bash
loginctl show-user "$USER" -p Linger
# 如为 Linger=no，且需要无登录会话时定时运行：
sudo loginctl enable-linger "$USER"
```

**注意：** `linger` 是该 Linux 用户的全局设置，可能同时影响 `tdl-bot` 等服务。卸载本项目不自动关闭它。

## 4. 运行与排障

```bash
# 查看下次执行
systemctl --user list-timers --all tg-auto.timer
# 查看签到日志
journalctl --user -u tg-auto.service -n 50 --no-pager
# 手动执行 systemd 一次性任务
systemctl --user start tg-auto.service
# 暂停每日自动任务
systemctl --user disable --now tg-auto.timer
# 查看授权文件权限（不输出其内容）
ls -l ~/.local/state/tg-auto/tg_auto.session
```

常见问题：

- **`ensurepip is not available` / `No module named pip`**：缺少 `python3.13-venv`；系统级 pip 是否存在与虚拟环境是否有 pip 是两回事。
- **`Permission denied (publickey)`**：SSH 密钥未被 GitHub 接受；Public 仓库可用 HTTPS 克隆。
- **代理超时**：检查宿主机 `127.0.0.1:2080` 的 Throne SOCKS5 服务是否可用，且不要混用 Docker 容器内的回环地址。
- **Telegram 授权丢失**：检查 `~/.local/state/tg-auto/tg_auto.session`，必要时在交互终端重新执行 `.venv/bin/python login.py`。
- **系统服务找不到配置**：确保 service 与普通 SSH 登录属于**同一 Linux 用户**，且 `~/.config/tg-auto/settings.env` 存在。
- **领取失败**：先运行只读探测，再核对一级/二级按钮；二级按钮必须是明确的 `点击领取每日…token` 才会尝试领取。领取结果无法验证时以失败退出，不反复点击。

## 5. 更新代码与服务配置

```bash
cd ~/apps/tg-auto
git pull
bash scripts/install.sh
```

安装脚本可重复运行：保留 `api_id`、`api_hash`、`settings.env`、`tg_auto.session`，更新 Python 依赖和本地 systemd unit，并重新加载 systemd。**注意**：如果你手工改动过安装后的 timer/unit，重新运行安装脚本会将它们备份并替换为仓库模板；因此建议在 GitHub 的模板中维护长期变更。

## 6. 一键卸载：两种模式

### A. 普通卸载：保留配置与登录状态，方便以后恢复

```bash
cd ~/apps/tg-auto
bash scripts/uninstall.sh
```

会停止并禁用 `tg-auto.timer`，停止 `tg-auto.service`，删除 `~/.config/systemd/user/` 下对应的两个 unit 文件并执行 `daemon-reload`。**保留**代码、虚拟环境、配置、API 凭据、Session 和可能存在的 unit 备份。

### B. 彻底卸载：本机文件全部清理

```bash
cd ~/apps/tg-auto
bash scripts/uninstall.sh --purge
```

要求手动输入 `DELETE tg-auto` 才会删除：

```text
~/apps/tg-auto/                      # 源码及 .venv
~/.config/tg-auto/                   # api_id、api_hash、settings.env
~/.local/state/tg-auto/              # tg_auto.session 等运行状态
~/.config/systemd/user/tg-auto.service
~/.config/systemd/user/tg-auto.timer
~/.config/systemd/user/tg-auto.*.backup.*   # 安装器创建的 unit 备份
```

非交互式彻底卸载需要明确指定 `bash scripts/uninstall.sh --purge --yes`，**无法撤销**。脚本只删除本项目的固定路径，不删除同目录中的其他服务。

**不会清理**：`tdl-bot`、Throne、青龙、系统 Python/apt/pip、用户 `linger` 设置、GitHub 远程仓库以及 systemd journal 历史日志。

**账号安全提示：** 删除本地 `.session` 文件 **不等于** 向 Telegram 服务端注销该授权会话。如果要撤销这次登录，还需在 Telegram 客户端的 **Settings → Devices（设置 → 设备）** 中找到相应会话并终止。即使删除本机 `api_id`/`api_hash` 文件，也不会让 Telegram 开发者凭据本身失效。

## 7. 核心实现与安全边界

```text
/start → 一级菜单「点击领取余额」→ 二级菜单
       →「点击领取每日…token」→ 验证「已领取」
```

Bot 可能在同一条 Message ID 上编辑内联按钮，程序会重新获取消息内容。仅发送正常的 `/start` 并点击明确识别的回调，不访问充值/邀请链接。每天通过 systemd 触发一次，运行完退出；不常驻进程。

`inspect_buttons.py` 为只读工具，不发送消息、不点击按钮，不打印 Callback Data 或目标 URL。项目使用的是个人 Telegram 账号（MTProto），不是 BotFather 机器人 token。请遵守目标服务的使用条款，不以高频调用绕过限制。
