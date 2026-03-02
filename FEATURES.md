# Storm AI — 功能操作手册

> 最后更新：2026-02-28  
> 文件位置：`storm-ai/FEATURES.md`  
> 系统提示词目录：`backend/app/prompts/system_prompts/`  
> 工具总数：**27 个**

---

## 一、系统架构

### 两阶段生图管线

所有功能共享同一套管线，区别仅在于各自的系统提示词：

```
用户操作: 上传参考图 + 输入提示词 + 选择参数（房间/风格/分辨率等）
    │
    ▼
Stage 1 — 推理模型 (gemini-3-pro)
    输入: 系统提示词 + 用户提示词 + 房间类型
    输出: 200-400词优化英文生图提示词
    │
    ▼
Stage 2 — 生图模型 (nano_banana_pro)
    输入: 优化提示词 + 参考图片(如有)
    输出: 高品质效果图 (S3 URL)
```

### 系统提示词的作用

- **系统提示词**（`.md` 文件）= 功能的"性格"，控制大方向（风格/材质/光照/质量标准）
- **用户提示词** = 每次具体需求（"换成北欧风"、"增强木地板纹理"）
- **参考图片** = 空间约束（保持布局和视角）
- 三者由 Stage 1 推理模型融合，生成最终的生图指令

---

## 二、P0 参数说明

### 布局强约束（layout_strict）

| 项目 | 内容 |
|------|------|
| 参数名 | `layout_strict` |
| 默认值 | `false` |
| 说明 | 启用后严格保持布局、视角、空间比例，不增删物体 |
| 适用 | 仅图生图工具（有参考图时） |
| 前端 | ToolDetail 高级选项 → 勾选「布局强约束」 |

### 跳过翻译（skip_translation）

| 项目 | 内容 |
|------|------|
| 参数名 | `skip_translation` |
| 默认值 | `false` |
| 说明 | 启用后跳过中文→英文风格词翻译，直接使用用户输入的提示词 |
| 注意 | 中文提示词可能影响生图效果 |
| 前端 | ToolDetail 高级选项 → 勾选「跳过翻译」 |

### 区域选择（region）

| 项目 | 内容 |
|------|------|
| 参数名 | `region` |
| 类型 | `rect` / `mask` / `polygon` |
| 说明 | 圈选图片中需要编辑的区域，后端转为自然语言描述注入提示词 |
| 适用工具 | partial-replace、local-material-change、material-replace、local-lighting、universal-edit（场景加模特） |
| 是否强制 | **不强制**。未圈选时后端按无区域处理，对整图生效 |

---

## 三、功能清单（27 个）

| # | 名称 | featureKey | 类型 | 系统提示词 | 实现简述 |
|---|------|------------|------|------------|----------|
| 1 | 草图大师方案渲染 | sketch-render | 图生图 | sketch-render.md | 两阶段管线，保持 SU 草图布局 |
| 2 | Nano Banana 香蕉模型渲染 | banana-pro-edit | 图生图 | banana-pro-edit.md | 专用模板 + 生图模型 |
| 3 | 香蕉Pro文生图 | banana-pro-t2i | 文生图 | — | banana_pro_t2i.j2 模板 |
| 4 | 香蕉Pro双图融合 | banana-pro-dual | 双图 | — | banana_pro_dual.j2 模板 |
| 5 | 室内氛围渲染 | atmosphere-change | 图生图 | atmosphere-change.md | 两阶段管线，6 种氛围预设 |
| 6 | 光影渲染 | lighting-master | 图生图 | lighting-master.md | 两阶段管线，3 种光照类型 |
| 7 | 室内多角度生图 | multi-view | 图生图 | multi-view.md | 两阶段管线，4 种视角 |
| 8 | 软硬装局部替换 | partial-replace | 图生图+区域 | partial-replace.md | 区域描述注入 extra_params |
| 9 | 局部材质修改 | local-material-change | 图生图+区域 | local-material-change.md | 区域描述注入 extra_params |
| 10 | 室内风格迁移 | style-transfer | 图生图 | style-transfer.md | 两阶段管线，9 种风格 + 保留程度 |
| 11 | 白膜生图 | white-model-render | 图生图 | white-model-render.md | 两阶段管线，space_type 注入 |
| 12 | 毛坯房出图 | rough-house-render | 图生图 | rough-house-render.md | 两阶段管线，预算等级 |
| 13 | 室内质感增强 | quality-enhance | 图生图 | quality-enhance.md | 两阶段管线，3 级增强 |
| 14 | 线稿生图 | line-render | 图生图 | sketch-render.md | 复用 sketch_render 模板 |
| 15 | 软装拼贴出图 | collage-render | 图生图/双图 | collage-render.md | 单图拼贴或双图融合 |
| 16 | 锁定材质出图 | locked-material-render | 图生图 | locked-material-render.md | 两阶段管线 |
| 17 | 材质替换 | material-replace | 图生图+区域 | material-replace.md | 区域描述注入 extra_params |
| 18 | 局部开灯 | local-lighting | 图生图+区域 | local-lighting.md | 区域描述 + light_type 注入 |
| 19 | 彩平图 | color-floor-plan | 图生图 | color-floor-plan.md | 两阶段管线，color_scheme |
| 20 | 平面布局方案 | floor-plan-layout | 图生图 | floor-plan-layout.md | 两阶段管线，family_info |
| 21 | 材质通道图 | material-channel | 图生图 | material-channel.md | 两阶段管线 |
| 22 | 软装物料清单 | furniture-list | 图生图→纯文本 | 无 | Gemini generate_text |
| 23 | 图片风格模仿 | style-mimic | 双图 | — | style_mimic.j2 模板 |
| 24 | 工具箱文生图 | toolbox-t2i | 文生图 | — | text_to_image.j2 模板 |
| 25 | 图片去水印 | remove-watermark | 图生图 | remove-watermark.md | remove_watermark.j2 模板 |
| 26 | 图片去背景 | material-extract | 图生图 | material-extract.md | material_extract.j2 模板 |
| 27 | 场景加模特 | universal-edit | 图生图+区域 | universal-edit.md | universal_edit.j2 + 区域描述 |

---

## 四、功能详细说明（精选）

### 草图大师方案渲染（sketch-render）

| 项目 | 内容 |
|------|------|
| Slug | `/tools/sketch-render` |
| Feature Key | `sketch-render` |
| 分类 | 室内 AI |
| 算力 | 2 点/次 |
| API | `POST /api/v1/interior-ai/sketch-render` |

**功能说明**：将 SketchUp 草图/3D 截图一键转为高品质写实渲染效果图。保持原始草图的空间布局、视角和家具位置不变，AI 自动填充真实材质、光影和氛围。

**系统提示词**：`sketch-render.md`

---

### 室内局部替换（partial-replace）

| 项目 | 内容 |
|------|------|
| Slug | `/tools/partial-replace` |
| Feature Key | `partial-replace` |
| 分类 | 室内 AI |
| 算力 | 3 点/次 |
| 区域选择 | 是（圈选需替换区域） |

**功能说明**：替换指定区域的家具或装饰物，其余所有区域像素级不变。新物品自动匹配现有空间的风格、光影和透视。

**系统提示词**：`partial-replace.md`

---

### 软装物料清单（furniture-list）

| 项目 | 内容 |
|------|------|
| Slug | `/tools/furniture-list` |
| Feature Key | `furniture-list` |
| 分类 | 室内 AI |
| 算力 | 1 点/次 |
| 输出 | 纯文本（JSON 格式） |

**功能说明**：AI 识别室内效果图中的物品，生成结构化软装清单。返回 JSON 格式，前端可尝试格式化显示。

---

## 五、提示词设计规范

### 系统提示词结构

```
功能定位（一句话说明用途）

场景：整体控制方向、保持/修改的边界

光照：光源类型、色温、层次、氛围

材质：各元素的材质要求（分条列举）

渲染质量：输出品质标准

风格：整体风格基调和约束
```

### 管理方式

- 文件位置：`backend/app/prompts/system_prompts/{featureKey}.md`
- 热加载：修改文件后重启即生效
- API 管理：`GET/PUT /api/v1/engines/system-prompts/{featureKey}`
- 新增功能：创建 `.md` 文件 + 注册 featureKey 即可

---

## 六、API 速查

### 认证

```
POST /api/v1/auth/register   → 注册（赠送 1000 算力）
POST /api/v1/auth/login      → 登录（返回 JWT）
GET  /api/v1/auth/me         → 当前用户信息
```

### 生成（需 Bearer Token）

```
POST /api/v1/interior-ai/{feature}  → 室内 AI（22 个功能）
POST /api/v1/super-ai/{feature}     → 超级 AI（3 个功能）
POST /api/v1/toolbox/{feature}      → 工具箱（5 个功能）

请求体:
{
  "images": [{"base64_data": "...", "format": "png"}],
  "project_id": "项目ID(可选，不传自动归档默认项目)",
  "prompt_text": "用户提示词",
  "aspect_ratio": "16:9",
  "layout_strict": false,
  "skip_translation": false,
  "region": {"type": "rect", "coordinates": [[0.1,0.1],[0.5,0.5]]},
  "extra_params": {"room_type": "living_room", "quality": "pro"}
}
```

### 积分

```
GET /api/v1/credits/balance   → 查询余额
GET /api/v1/credits/history   → 消费记录
```

### 项目与图库

```
GET   /api/v1/projects                     → 项目列表（含图片数量、最近生成时间）
POST  /api/v1/projects                     → 创建项目
GET   /api/v1/projects/{project_id}        → 项目详情
PATCH /api/v1/projects/{project_id}        → 项目重命名
GET   /api/v1/projects/{project_id}/generations
                                         → 项目内图片历史（分页）
```

### 引擎管理

```
GET  /api/v1/engines/list              → 已注册引擎
GET  /api/v1/engines/models            → 可用模型
POST /api/v1/engines/test              → 快速测试
GET  /api/v1/engines/system-prompts    → 所有系统提示词
PUT  /api/v1/engines/system-prompts/{key} → 更新提示词
```

---

## 七、NewAPI 分发站接入

### 概述

NewAPI 是兼容 OpenAI Chat Completions 协议的 API 分发站，可接入 GPT-4o、Claude 等多种模型。配置后自动注册为可用引擎，支持文本生成和多模态（图文）调用。

### 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `NEWAPI_API_KEY` | 是 | — | NewAPI 分发站 API 密钥 |
| `NEWAPI_BASE_URL` | 否 | `https://zapi.aicc0.com/v1` | API 基础地址 |
| `NEWAPI_DEFAULT_MODEL` | 否 | `gpt-4o` | 默认模型（兼容 fallback） |
| `NEWAPI_REASONING_MODEL` | 否 | `gemini-3-flash` | 推理模型（Stage 1 提示词优化） |
| `NEWAPI_GENERATION_MODEL` | 否 | `grok-imagine-1.0` | 生图模型（Stage 2 图片生成） |

### 支持接口

| 方法 | 对应 API | 说明 |
|------|----------|------|
| `list_models()` | `GET /models` | 列出分发站可用模型 |
| `generate_text()` | `POST /chat/completions` | 纯文本生成（推理） |
| `generate()` 无输入图 | `POST /images/generations` | 文生图，解析 `data[].url` / `data[].b64_json` |
| `generate()` 有输入图 | `POST /chat/completions` | 图生图，多模态 content |
| `generate()` fallback | `POST /chat/completions` | `/images/generations` 失败时自动回退 |

### 默认引擎切换开关（推理/生图模型拆分）

通过 `NEWAPI_AS_DEFAULT` 可将 NewAPI 设为默认引擎。**默认模式下推理和生图使用不同模型**：

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `NEWAPI_AS_DEFAULT` | 否 | `false` | 设为 `true` 时启用默认模式 |

**行为说明**：

- `NEWAPI_AS_DEFAULT=true` 且 `NEWAPI_API_KEY` 已配置时：
  - 创建两个独立的 NewAPIClient 实例：
    - **推理客户端**（`newapi_reasoning`）：使用 `NEWAPI_REASONING_MODEL`，走 `chat/completions`
    - **生图客户端**（`newapi`）：使用 `NEWAPI_GENERATION_MODEL`，走 `/images/generations`
  - 两阶段管线：推理端 → `NEWAPI_REASONING_MODEL`，生图端 → `NEWAPI_GENERATION_MODEL`
  - Swiftask / Gemini 仍会注册但不再是默认引擎
- `NEWAPI_AS_DEFAULT=true` 但未配置 `NEWAPI_API_KEY` 时：
  - 打印 warning 日志，回退到原有默认引擎逻辑
- `NEWAPI_AS_DEFAULT=false`（默认）：
  - 行为与之前完全一致，不影响现有部署

### 调用示例

```bash
# .env 基础配置（非默认模式）
NEWAPI_API_KEY=sk-your-key-here
NEWAPI_BASE_URL=https://zapi.aicc0.com/v1
NEWAPI_DEFAULT_MODEL=gpt-4o
```

```bash
# .env 推荐配置（默认模式，推理/生图拆分）
NEWAPI_API_KEY=sk-your-key-here
NEWAPI_BASE_URL=https://api.loveyy.qzz.io/v1
NEWAPI_DEFAULT_MODEL=gemini-3-flash
NEWAPI_REASONING_MODEL=gemini-3-flash
NEWAPI_GENERATION_MODEL=grok-imagine-1.0
NEWAPI_AS_DEFAULT=true
```

启动后在引擎列表中可见：

```
GET /api/v1/engines/list
→ [
    ...,
    {"key": "newapi", "type": "newapi", "label": "NewAPI 生图引擎", "is_default": true},
    {"key": "newapi_reasoning", "type": "newapi", "label": "NewAPI 推理引擎", "is_default": false}
  ]
```

---

## 八、Venice AI 渠道接入

### 概述

Venice AI 同时支持 **原生生图端点**（`/image/generate`）和 **OpenAI 兼容协议**（`/chat/completions`、`/images/generations`）。可通过环境变量灵活控制：

- `VENICE_AS_GENERATION=true`：Venice 作为默认生图引擎，文生图走原生端点
- `VENICE_AS_REASONING=true`：Venice 接管推理客户端

### 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `VENICE_API_KEY` | 是 | — | Venice AI API 密钥 |
| `VENICE_BASE_URL` | 否 | `https://api.venice.ai/api/v1` | Venice API 基础地址 |
| `VENICE_DEFAULT_MODEL` | 否 | `venice-uncensored` | 默认模型（推理/通用） |
| `VENICE_GENERATION_MODEL` | 否 | `nano-banana-2` | 生图模型（走原生 `/image/generate`） |
| `VENICE_AS_REASONING` | 否 | `false` | 设为 `true` 时将推理客户端切换到 Venice |
| `VENICE_AS_GENERATION` | 否 | `false` | 设为 `true` 时 Venice 作为默认生图引擎（与 `NEWAPI_AS_DEFAULT` 互斥） |

### Venice 原生生图端点

当 `VENICE_AS_GENERATION=true` 时，文生图请求优先调用 Venice 原生端点：

```
POST https://api.venice.ai/api/v1/image/generate
Content-Type: application/json
Authorization: Bearer <VENICE_API_KEY>

{
  "model": "nano-banana-2",       ← 必填，生图模型名
  "prompt": "a modern living room with warm lighting",  ← 必填，生图描述
  "aspect_ratio": "16:9",         ← 可选，宽高比（"1:1"、"16:9"、"9:16" 等）
  "negative_prompt": "...",       ← 可选，负面提示词
  "seed": 123456789,              ← 可选，随机种子
  "steps": 8,                     ← 可选，推理步数
  "cfg_scale": 7.5,               ← 可选，CFG 缩放
  "style_preset": "3D Model",     ← 可选，风格预设
  "resolution": "2K"              ← 可选，分辨率（"1K"/"2K"/"4K"）
}
```

**响应格式**：

```json
{
  "id": "generate-image-...",
  "images": ["<base64-encoded-image>", ...],
  "timing": { "total": 3200, "inferenceDuration": 2800, ... }
}
```

**Fallback 机制**：原生端点失败时自动回退到 OpenAI 兼容的 `/images/generations`，再失败则回退到 `/chat/completions`。

### 默认行为

- `VENICE_AS_GENERATION=true` + `VENICE_API_KEY` 已配置：
  - Venice 注册为默认生图引擎（`is_default=true`）
  - 使用 `VENICE_GENERATION_MODEL`（默认 `nano-banana-2`）
  - `NEWAPI_AS_DEFAULT` 自动降级为非默认
- `VENICE_AS_GENERATION=false`（默认）：
  - Venice 仅注册为可选引擎，不影响现有生图链路
- `VENICE_AS_REASONING=true`：两阶段管线的推理端切换到 Venice，生图端不变

### 推荐配置

```bash
# Venice 作为默认生图引擎（推荐）
VENICE_API_KEY=your-venice-key
VENICE_GENERATION_MODEL=nano-banana-2
VENICE_AS_GENERATION=true
VENICE_AS_REASONING=false
NEWAPI_AS_DEFAULT=false          # 避免双默认冲突
```

---

## 九、项目化图片保存与多图对比（MVP）

### 能力概览

| 能力 | 状态 | 说明 |
|------|------|------|
| 图片持久化保存 | ✅ 已实现 | 生成成功后写入 `generation_history`，刷新不丢图 |
| 项目管理 | ✅ 已实现 | 支持创建项目、重命名项目、查看项目详情 |
| 默认项目归档 | ✅ 已实现 | 生成请求不传 `project_id` 时自动归档“未命名项目” |
| 项目图库分页 | ✅ 已实现 | `GET /projects/{id}/generations?limit&offset` |
| 多图对比（最多4张） | ✅ 已实现 | 项目详情页勾选图片后并排对比 |

### 后端实现要点

- 数据模型：
  - `projects`：`id/user_id/name/cover_image_url/is_default/created_at/updated_at`
  - `generation_history.project_id`：关联项目ID
- 归档流程：
  1. 生成接口（super/interior/toolbox）在成功后触发 `record_generation`
  2. 若传入 `project_id`，先校验项目归属
  3. 未传 `project_id` 自动分配默认项目
  4. 写入记录后可通过项目接口分页查询
- 鉴权：
  - 项目相关 API 与生成 API 均要求 `Authorization: Bearer <token>`

### 前端实现要点

- 项目页：
  - `/projects`：项目列表、创建项目、进入项目
  - `/projects/:id`：项目图库、分页加载、项目重命名
- 生成页：
  - `ToolDetail` 增加“所属项目”选择器
  - 请求体新增 `project_id`
- 对比页（MVP）：
  - 项目详情中可勾选最多 4 张图
  - “开始对比”后进入全屏网格对比，支持逐张下载

### 典型用户流程

```
登录 → 进入工具详情页 → 选择项目(或默认项目) → 生成图片
→ 后端自动归档到项目 → 打开 /projects/{id} 查看历史
→ 勾选多张图片 → 开始对比
```
