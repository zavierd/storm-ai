# Storm AI — 服务器与部署说明

> 运维速查文档，记录服务器配置、部署流程及常用命令，便于后续操作。

---

## 一、服务器信息

| 项目 | 值 |
|------|-----|
| **IP** | 118.31.63.113 |
| **端口** | 22 |
| **用户** | root |
| **登录方式** | 证书（推荐）或密码 |
| **证书路径** | `~/.ssh/id_ed25519` |

**证书登录：**
```bash
ssh -i ~/.ssh/id_ed25519 root@118.31.63.113
```

---

## 二、服务器环境

| 组件 | 说明 |
|------|------|
| 系统 | Ubuntu 22.04 LTS |
| Swap | 1.5GB，swappiness=10，`/swapfile` |
| fail2ban | sshd jail，白名单见 `ignoreip` |
| UFW | 放行 22/80/443/8000/5173 |
| Docker | 29.2.1 + Compose v5.1.0 |
| PostgreSQL | v14，数据库 `stormaidb` |

**fail2ban 白名单**：`/etc/fail2ban/jail.local` 中 `ignoreip`，新增 IP 后需 `systemctl restart fail2ban`。

---

## 三、项目部署

| 项目 | 路径/说明 |
|------|-----------|
| 代码目录 | `/opt/storm-ai` |
| 后端服务 | `storm-ai-backend` (systemd) |
| 前端 | nginx 托管 `dist/` |
| 反向代理 | nginx 80 → 后端 8000 |
| 访问地址 | http://118.31.63.113/ |
| API 基址 | http://118.31.63.113/api/v1/ |

**GitHub：** https://github.com/zavierd/storm-ai

---

## 四、常用命令

### 部署更新
```bash
cd /opt/storm-ai && git pull origin main
cd frontend && npm install && npm run build
# 复制 dist 到 nginx 目录（按实际配置）
sudo cp -r dist/* /usr/share/nginx/html/
sudo systemctl restart storm-ai-backend
sudo systemctl restart nginx
```

### 服务管理
```bash
sudo systemctl status storm-ai-backend   # 后端状态
sudo systemctl restart storm-ai-backend # 重启后端
sudo journalctl -u storm-ai-backend -f  # 实时日志
sudo systemctl restart nginx             # 重启 nginx
```

### 数据库
```bash
sudo -u postgres psql -d stormaidb
```

---

## 五、后端配置

**环境变量**：`/opt/storm-ai/backend/.env`（不纳入 Git）

必填项：
- `DATABASE_URL` — PostgreSQL 连接串
- `JWT_SECRET` — JWT 签名密钥
- `SWIFTASK_API_KEY` 或其它 AI 引擎密钥
- `BACKEND_PUBLIC_URL` — 后端对外地址，用于生成图 URL

参考：`backend/.env.example`

---

## 六、故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| SSH 超时 | fail2ban 封禁 | 控制台登录 → `fail2ban-client unban --all` |
| 502 | 后端未启动 | `systemctl restart storm-ai-backend` |
| 前端空白 | dist 未更新 | 重新 `npm run build` 并复制到 nginx |
| 积分不足 | 余额或费率配置 | 查 `users.credits_balance`、`CREDITS_*` 环境变量 |

---

## 七、项目结构速览

```
storm-ai/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── api/      # 路由：auth, credits, interior_ai, super_ai, toolbox
│   │   ├── services/ # 业务逻辑
│   │   └── models/
│   └── run.py
├── frontend/         # Vite + React
│   └── src/
├── docs/             # 文档
└── FEATURES.md       # 功能说明
```

---

*最后更新：2026-03*
