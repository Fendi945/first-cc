"""飞书 API 客户端 —— 基础认证与 API 调用封装。

用法:
    from engine.feishu_client import FeishuClient
    client = FeishuClient()
    token = client.get_tenant_access_token()
"""

import logging
import time
from typing import Optional

import requests

from engine.config import FEISHU_APP_ID, FEISHU_APP_SECRET

logger = logging.getLogger("feishu_client")

BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """飞书 API 客户端（自动管理 tenant_access_token）。"""

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    # ── Token 管理 ──

    def get_tenant_access_token(self) -> str:
        """获取（或刷新）tenant_access_token。

        返回:
            有效的 token 字符串。

        抛出:
            RuntimeError: 凭证未配置或认证失败
        """
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
            raise RuntimeError(
                "飞书凭证未配置。请先在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
            )

        url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET,
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(
                    f"飞书认证失败: {data.get('msg', '未知错误')} "
                    f"(code={data.get('code')})"
                )

            self._token = data["tenant_access_token"]
            self._token_expires_at = time.time() + data.get("expire", 7200)
            logger.info("飞书 tenant_access_token 已刷新")
            return self._token

        except requests.RequestException as e:
            raise RuntimeError(f"飞书认证请求失败: {e}")

    # ── 通用请求封装 ──

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """带 token 自动刷新的 API 请求。"""
        token = self.get_tenant_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json; charset=utf-8"

        url = f"{BASE_URL}{path}"
        try:
            resp = requests.request(method, url, headers=headers, timeout=kwargs.pop("timeout", 30), **kwargs)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(
                    f"飞书 API 错误 [{path}]: {data.get('msg', '未知错误')} "
                    f"(code={data.get('code')})"
                )

            return data

        except requests.RequestException as e:
            raise RuntimeError(f"飞书 API 请求失败 [{path}]: {e}")

    def _get(self, path: str, **kwargs) -> dict:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs) -> dict:
        return self._request("POST", path, **kwargs)

    # ── 文档 API（docx） ──

    def get_document(self, document_token: str) -> dict:
        """获取飞书文档原始内容。

        参数:
            document_token: 文档 token（从 URL 中获取）

        返回:
            文档数据字典
        """
        path = f"/docx/v1/documents/{document_token}/raw_content"
        return self._get(path)

    # ── 多维表格 API（bitable） ──

    def list_bitable_records(self, app_token: str, table_id: str, page_size: int = 500) -> list:
        """列出多维表格的所有记录。

        参数:
            app_token: 多维表格 app token
            table_id: 数据表 ID
            page_size: 每页数量（最大 500）

        返回:
            记录列表
        """
        records = []
        page_token = None

        while True:
            path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            data = self._get(path, params=params)
            items = data.get("data", {}).get("items", [])
            records.extend(items)

            if not data.get("data", {}).get("has_more"):
                break
            page_token = data.get("data", {}).get("page_token")

        return records

    def create_bitable_record(self, app_token: str, table_id: str, fields: dict) -> dict:
        """在多维表格中创建一条记录。

        参数:
            app_token: 多维表格 app token
            table_id: 数据表 ID
            fields: 字段键值对

        返回:
            创建的记录数据
        """
        path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        payload = {"fields": fields}
        data = self._post(path, json=payload)
        return data.get("data", {}).get("record", {})

    # ── 云空间 API（drive） ──

    def upload_file(self, file_path: str, parent_node: str, parent_type: str = "explorer") -> dict:
        """上传文件到飞书云空间。

        参数:
            file_path: 本地文件路径
            parent_node: 父节点 token（文件夹）
            parent_type: 父节点类型（explorer / docx / bitable）

        返回:
            上传结果
        """
        from pathlib import Path

        path = Path(file_path)
        file_name = path.name
        file_size = path.stat().st_size

        upload_path = "/drive/v1/files/upload_all"
        payload = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": file_size,
        }

        token = self.get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                resp = requests.post(
                    f"{BASE_URL}{upload_path}",
                    headers=headers,
                    data=payload,
                    files=files,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    raise RuntimeError(
                        f"上传失败: {data.get('msg', '未知错误')}"
                    )
                return data
        except requests.RequestException as e:
            raise RuntimeError(f"飞书上传请求失败: {e}")
