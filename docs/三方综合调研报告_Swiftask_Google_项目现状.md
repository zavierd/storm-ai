# Swiftask + Google 模型 + storm-ai 三方综合调研报告

> 调研日期：2026-02-27 | 用途：为后续功能实现提供依据

---

## 一、精简结论（<600字）

### Swiftask 官方能力边界

- **API**：`POST /api/ai/{slug}`，认证 `Authorization: Bearer <token>`
- **files 格式**：`[{url, type, name?, size?}]`，`url` 必填，支持 S3 上传后的 URL 或 `data:image/png;base64,...`
- **S3 上传**：`GET /widget/get-signed-url?fileName=xxx&clientToken=xxx`，返回含 `url`（PUT 上传）和 `fileUrl`（下载）的 JSON；项目已正确使用 `url` 做 PUT 上传
- **生图相关 bot slug**：`nano_banana_pro`、`gemini---nano-banana`（图生图）、`imagen_4`/`imagen_4_fast`/`imagen_4_ultra`（纯文生图）
- **关键限制**：Imagen 系列**不支持** image input，仅 Nano Banana 系列支持图生图；`documentAnalysisMode: ADVANCED` 用于有文件时的深度分析

### Google 模型最佳实践

- **文生图**：叙事化描述 > 关键词堆砌；结构建议：主体→环境→材质→光照→风格→品质；摄影术语（镜头、角度、光线）可提升写实感
- **图生图**：无显式参考图权重参数，需通过提示词控制；布局保持用 "Keep the same layout, proportions and viewing angle"；局部编辑用 "change only [X] to [Y], keep everything else exactly the same"
- **多图输入**：支持合成、风格迁移；编辑时多图会采用最后一张的宽高比
- **已知限制**：复杂排版/角色一致性需多轮迭代；宽高比需在提示词中显式约束

### 项目现状与符合度

- **pipeline**：图生图走翻译→简短编辑→生图；文生图走推理扩展→生图，符合文档建议
- **swiftask_client**：files 格式、S3 流程、slug 映射与文档一致；S3 响应用 `url` 字段（文档示例为 `signedUrl`，实际接口可能兼容）
- **unified.py**：各 feature 已有布局保持、风格约束等提示词，与 Google 建议基本一致
- **已知问题**：① 翻译层可能过度压缩用户意图；② 布局保持完全依赖提示词，无 API 级权重；③ Imagen 被映射到 quality 档位但实际不支持图生图，需在前端/配置中区分

### 功能实现优先级建议

1. **高**：图生图布局保持强化（提示词模板优化 + 可选「强约束」模式）
2. **高**：翻译层可配置化（支持跳过/简化/保留原文）
3. **中**：Imagen 与 Nano Banana 的 quality 路由区分（Imagen 仅文生图）
4. **中**：多图输入与 style-mimic 的 files 顺序与提示词规范
5. **低**：局部编辑（inpainting）的 region 描述标准化

---

## 二、文档能力 vs 项目实现 对照表

| 能力/约束 | 文档说明 | 项目实现 | 符合度 | 备注 |
|-----------|----------|----------|--------|------|
| files 传参 | `{url, type, name?, size?}` | `{url, name, type, size}` | ✅ | 一致 |
| S3 上传流程 | get-signed-url → PUT → 用 URL 填 files | 同流程，用 `url` 字段 | ✅ | 文档示例为 signedUrl，实际可能返回 url |
| documentAnalysisMode | SIMPLE / ADVANCED | 有 files 时设 ADVANCED | ✅ | 符合 |
| 图生图模型 | Nano Banana 系列支持 image input | nano_banana_pro、gemini---nano-banana | ✅ | 正确 |
| Imagen 图生图 | 不支持 | quality 映射含 imagen_4 等 | ⚠️ | 需区分：Imagen 仅文生图 |
| 布局保持 | 无 API 参数，靠提示词 | "Keep layout, proportions, viewing angle" | ✅ | 符合文档建议 |
| 参考图权重 | 无显式参数 | 无 | — | 文档也无，只能靠提示词 |
| 文生图提示词 | 叙事化、主体→环境→光照 | 推理模型生成 100–200 词英文 | ✅ | 符合 |
| 多图输入 | 支持合成、风格迁移 | style-mimic 等有模板 | ✅ | 已覆盖 |
| 局部编辑 | 提示词描述区域 | partial-replace、local-material-change | ✅ | 靠提示词实现 |
| 错误处理 | 400/401/404/500 | GeminiAPIError、isBotError | ✅ | 已覆盖 |

---

## 三、功能实现优先级与实现要点

### P0：布局保持强化

| 要点 | 实现建议 |
|------|----------|
| 提示词 | 在 `_build_image_edit_prompt` 中增加可选强约束："Strictly preserve layout, camera angle, and spatial proportions. Do not add or remove objects." |
| 触发条件 | `extra_params.layout_strict = true` 时启用 |
| 风险 | 过度约束可能削弱风格/材质变化，建议默认关闭 |

### P0：翻译层可配置化

| 要点 | 实现建议 |
|------|----------|
| 配置项 | `extra_params.skip_translation` 或 `translation_mode: "none"|"minimal"|"full"` |
| 实现 | pipeline 中 `skip_translation` 时跳过 `_translate_style_keywords`，直接使用 user_prompt |
| 风险 | 中文直接输入可能影响 Nano Banana 效果，需在 UI 提示用户 |

### P1：Imagen 与 Nano Banana 路由区分

| 要点 | 实现建议 |
|------|----------|
| 逻辑 | 有 `images` 时，quality 若为 imagen 系列则自动降级到 nano_banana_pro 或返回明确错误 |
| 配置 | QUALITY_MODELS 中为 imagen 增加 `supports_image_input: False`，前端据此禁用图生图选项 |
| 风险 | 用户可能不理解「该档位不支持参考图」，需文案说明 |

### P1：多图与 style-mimic 规范

| 要点 | 实现建议 |
|------|----------|
| files 顺序 | 目标图在前、风格参考图在后（与 unified 中 "Image 1 is target, Image 2 is style" 一致） |
| 提示词 | 明确 "Preserve target composition. Apply style from reference image 2." |
| 宽高比 | 提示词中加 "Use aspect ratio of the first/reference image." |

### P2：局部编辑 region 标准化

| 要点 | 实现建议 |
|------|----------|
| 参数 | `region_description` 标准化为 "the [object/area] in [position]" 格式 |
| 提示词 | "Change only [region_description] to [new_description]. Keep everything else unchanged." |
| 限制 | 无 mask API，完全依赖文本描述，效果受模型理解能力影响 |

---

## 四、风险与规避

| 风险 | 规避方式 |
|------|----------|
| S3 响应字段变更 | 同时兼容 `url` 与 `signedUrl`，优先 `url` |
| 布局被过度修改 | 默认加布局约束；复杂场景提供「强约束」开关 |
| 翻译丢失用户意图 | 提供跳过/简化选项；翻译失败时回退原文 |
| Imagen 收到图生图请求 | 后端校验 `supports_image_input`，前端按能力禁用 |
| 多图宽高比混乱 | 提示词显式指定 "preserve first image aspect ratio" |
| 角色/排版一致性差 | 文档已说明需多轮迭代；UI 可提供「继续优化」入口 |

---

## 五、附录：生图相关 Bot Slug 一览

| Slug | 名称 | 图生图 | 来源 |
|------|------|--------|------|
| nano_banana_pro | Nano Banana Pro | ✅ | 项目默认 |
| google-gemini-nano-banana-pro | 同上（别名） | ✅ | 官方 bots |
| gemini---nano-banana | Nano Banana | ✅ | 项目 basic |
| imagen_4 | Imagen-4 | ❌ | 项目 standard |
| imagen_4_fast | Imagen-4 Fast | ❌ | 项目 fast |
| imagen_4_ultra | Imagen-4 Ultra | ❌ | 项目 hd |
| gpt-image | GPT Image 1.5 | ✅ | 可选 |
| fluxpro11 / flux_kontext_pro_tool | Flux Pro | ✅ | 可选 |
