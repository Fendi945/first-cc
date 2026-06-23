# API 接入记录

## 飞书开放平台

- 应用地址：https://open.feishu.cn
- 已创建应用：Claude 文档助手

## 凭证信息

- App ID：`cli_aa942cbadf3b1bee`
- App Secret：已配置到 `.env`
- 认证方式：tenant_access_token（internal app）

## 接口调试记录

| 日期 | 接口 | 结果 | 备注 |
|------|------|------|------|
| 2026-06-23 | `auth/v3/tenant_access_token/internal` | ✅ 成功 | token=t-g1046n9BIXPX674RGI... |

## 可用 API（已封装）

| API | 方法 | 用途 |
|-----|------|------|
| `docx/v1/documents/{token}/raw_content` | GET | 获取飞书文档原始内容 |
| `bitable/v1/apps/{token}/tables/{id}/records` | GET | 列出多维表格记录 |
| `bitable/v1/apps/{token}/tables/{id}/records` | POST | 创建多维表格记录 |
| `drive/v1/files/upload_all` | POST | 上传文件到云空间 |
