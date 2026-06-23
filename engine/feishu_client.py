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
        """带 token 自动刷新和指数退避重试的 API 请求。

        自动处理：
        - 401 → 清理 token，刷新后重试
        - 429 → 限流退避重试
        - 5xx → 服务端错误退避重试
        """
        max_retries = kwargs.pop("max_retries", 3)
        timeout = kwargs.pop("timeout", 30)
        given_headers = kwargs.pop("headers", {})

        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            token = self.get_tenant_access_token()

            headers = dict(given_headers)
            headers["Authorization"] = f"Bearer {token}"
            headers["Content-Type"] = "application/json; charset=utf-8"

            url = f"{BASE_URL}{path}"
            try:
                resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)

                # 401 — token 过期，清理缓存并刷新重试（仅一次）
                if resp.status_code == 401:
                    old_token = self._token
                    self._token = None  # 清理过期 token
                    if attempt == 0:
                        logger.warning("飞书 token 过期 [%s]，刷新后重试", path)
                        # 强制刷新 token（get_tenant_access_token 会重新请求）
                        continue
                    # 二次尝试仍 401，说明凭证本身有问题
                    self._token = old_token  # 保留现场以便排查
                    raise RuntimeError(
                        f"飞书认证失败 [{path}]: 401 Unauthorized（刷新 token 后仍失败）"
                    )

                resp.raise_for_status()
                data = resp.json()

                # 业务错误码 — token invalid / expired
                if data.get("code") in (99991663, 99991668):
                    self._token = None
                    if attempt == 0:
                        logger.warning("飞书 token 无效 [%s]，刷新后重试", path)
                        continue
                    raise RuntimeError(
                        f"飞书 token 无效 [{path}]: {data.get('msg', '')} "
                        f"(code={data.get('code')})"
                    )

                if data.get("code") != 0:
                    raise RuntimeError(
                        f"飞书 API 错误 [{path}]: {data.get('msg', '未知错误')} "
                        f"(code={data.get('code')})"
                    )

                return data

            except requests.HTTPError as e:
                status = e.response.status_code if e.response else 0

                # 429 — API 限流，指数退避
                if status == 429:
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt + attempt * 0.5
                        logger.warning(
                            "飞书 API 限流 [%s]，%.1fs 后重试 (%d/%d)",
                            path, wait, attempt + 1, max_retries,
                        )
                        time.sleep(wait)
                        last_error = e
                        continue
                    raise RuntimeError(
                        f"飞书 API 限流 [{path}]: 重试 {max_retries} 次后仍被限流"
                    )

                # 5xx — 服务端临时错误，可重试
                if status >= 500:
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt + attempt * 0.5
                        logger.warning(
                            "飞书服务端错误 [%s] HTTP %d，%.1fs 后重试 (%d/%d)",
                            path, status, wait, attempt + 1, max_retries,
                        )
                        time.sleep(wait)
                        last_error = e
                        continue
                    raise RuntimeError(
                        f"飞书 API 服务端错误 [{path}]: HTTP {status}"
                    )

                raise RuntimeError(f"飞书 API 请求失败 [{path}]: {e}")

            except requests.RequestException as e:
                # 网络层错误（超时、连接重置等），可重试
                if attempt < max_retries - 1:
                    wait = 2 ** attempt + attempt * 0.5
                    logger.warning(
                        "飞书网络错误 [%s]，%.1fs 后重试 (%d/%d)",
                        path, wait, attempt + 1, max_retries,
                    )
                    time.sleep(wait)
                    last_error = e
                    continue
                raise RuntimeError(
                    f"飞书 API 请求失败 [{path}]: 重试 {max_retries} 次后仍失败: {last_error}"
                )

        raise RuntimeError(f"飞书 API 请求失败 [{path}]: 意外错误")

    def _get(self, path: str, **kwargs) -> dict:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs) -> dict:
        return self._request("POST", path, **kwargs)

    # ── 多维表格字段 API ──

    def list_fields(self, app_token: str, table_id: str) -> list:
        """列出指定多维表格的所有字段定义。

        参数:
            app_token: 多维表格 app token
            table_id: 数据表 ID

        返回:
            字段定义列表 [{field_id, field_name, type, ...}]
        """
        path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        data = self._get(path)
        return data.get("data", {}).get("items", [])

    def create_field(self, app_token: str, table_id: str,
                     field_name: str, field_type: int,
                     property: Optional[dict] = None) -> dict:
        """在多维表格中创建一个新字段。

        参数:
            app_token: 多维表格 app token
            table_id: 数据表 ID
            field_name: 字段名称
            field_type: 字段类型
            property: 字段属性（如选项列表）

        返回:
            创建结果
        """
        path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        payload = {"field_name": field_name, "type": field_type}
        if property:
            payload["property"] = property
        data = self._post(path, json=payload)
        return data.get("data", {})

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

    def create_bitable(self, name: str) -> dict:
        """创建一个新的多维表格。

        参数:
            name: 多维表格名称

        返回:
            创建结果，包含 app_token
        """
        path = "/bitable/v1/apps"
        payload = {"name": name}
        data = self._post(path, json=payload)
        app_data = data.get("data", {}).get("app", {})
        return {
            "app_token": app_data.get("app_token", ""),
            "url": app_data.get("url", ""),
            "default_table_id": app_data.get("default_table_id", ""),
        }

    def list_tables(self, app_token: str) -> list:
        """列出多维表格中的所有数据表。

        参数:
            app_token: 多维表格 app token

        返回:
            数据表列表
        """
        path = f"/bitable/v1/apps/{app_token}/tables"
        data = self._get(path)
        return data.get("data", {}).get("items", [])

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

    def create_folder(self, name: str, folder_token: str = "") -> dict:
        """在飞书云空间创建文件夹。

        参数:
            name: 文件夹名称
            folder_token: 父文件夹 token，空字符串表示根目录

        返回:
            {token, url, name, ...}
        """
        path = "/drive/v1/files/create_folder"
        payload = {"name": name, "folder_token": folder_token}
        data = self._post(path, json=payload)
        return data.get("data", {})

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
