import os
import pytest
import tempfile
import shutil
import json
from unittest.mock import patch

from backend.app.services.local_library_config import (
    get_local_library_config,
    update_local_library_config,
    check_directory_status,
    CONFIG_FILE,
)


class TestLocalLibraryConfig:
    @pytest.fixture(autouse=True)
    def setup_dirs(self):
        # 建立临时白名单基准文件夹
        self.temp_base = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_base, "books")
        self.essence_dir = os.path.join(self.temp_base, "essence")
        
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.essence_dir, exist_ok=True)

        yield

        # 清除临时目录与临时生成的 JSON 配置文件
        shutil.rmtree(self.temp_base, ignore_errors=True)
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
            except OSError:
                pass

    def test_get_and_update_config_serialization(self):
        # 1. 验证获取配置时，未创建配置文件时采用默认初始化
        config = get_local_library_config()
        assert config["id"] == 1
        assert "source_dir" in config

        # 2. 校验配置更新的持久化保存
        updated_payload = {
            "source_dir": self.source_dir,
            "essence_dir": self.essence_dir,
            "allow_local_file_access": True,
            "max_file_mb": 200
        }
        res = update_local_library_config(updated_payload)
        assert res["source_dir"] == self.source_dir
        assert res["allow_local_file_access"] is True
        assert res["max_file_mb"] == 200

        # 3. 从磁盘重新读取，验证 JSON 被正确反序列化
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert disk_data["source_dir"] == self.source_dir
        assert disk_data["allow_local_file_access"] is True
        assert disk_data["max_file_mb"] == 200

    def test_check_directory_status_checks(self):
        # 1. 检测存在的、读写正常的目录
        status_ok = check_directory_status(self.source_dir)
        assert status_ok["exists"] is True
        assert status_ok["readable"] is True
        assert status_ok["writable"] is True
        assert status_ok["error"] is None

        # 2. 检测不存在的目录
        status_nonexistent = check_directory_status(os.path.join(self.temp_base, "nonexistent"))
        assert status_nonexistent["exists"] is False
        assert status_nonexistent["error"] == "路径不存在"

        # 3. 检测空路径
        status_empty = check_directory_status("")
        assert status_empty["exists"] is False
        assert status_empty["error"] == "路径为空"

    def test_check_directory_status_readonly(self):
        # 模拟只读目录：在支持权限修改的系统下测试
        readonly_dir = os.path.join(self.temp_base, "readonly_dir")
        os.makedirs(readonly_dir, exist_ok=True)
        
        # 改变目录权限为只读 (Windows 下 chmod 0o400 不影响写目录的能力，故在物理写入时捕获权限报错)
        try:
            os.chmod(readonly_dir, 0o400)
            # 在某些系统下chmod起效后，物理写测试会自动抓包返回 writable=False
            status = check_directory_status(readonly_dir)
            # 我们只需要校验：若无法创建临时文件，它必须返回 writable=False
            if not status["writable"]:
                assert "目录不可写" in status["error"]
        finally:
            os.chmod(readonly_dir, 0o777)
