import os
import pytest
import tempfile
import shutil
from unittest.mock import patch

from backend.app.services.local_file_guard import (
    resolve_safe_path,
    assert_read_allowed,
    assert_write_allowed,
    is_safe_extension,
)
from backend.app.services.local_library_config import update_local_library_config


class TestLocalFileGuard:
    @pytest.fixture(autouse=True)
    def setup_dirs(self):
        # 建立临时白名单基准文件夹
        self.temp_base = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_base, "books")
        self.essence_dir = os.path.join(self.temp_base, "essence")
        self.cache_dir = os.path.join(self.temp_base, "cache")
        self.log_dir = os.path.join(self.temp_base, "logs")

        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.essence_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

        # 动态更新临时配置以指向我们隔离的临时文件夹
        update_local_library_config({
            "source_dir": self.source_dir,
            "essence_dir": self.essence_dir,
            "cache_dir": self.cache_dir,
            "log_dir": self.log_dir,
            "allow_local_file_access": True
        })

        yield

        # 清除临时目录
        shutil.rmtree(self.temp_base, ignore_errors=True)

    def test_safe_path_resolution(self):
        # 1. 允许解析子目录文件
        target = os.path.join(self.source_dir, "novel.txt")
        resolved = resolve_safe_path(self.source_dir, "novel.txt")
        assert os.path.realpath(target) == resolved

    def test_traversal_prevention(self):
        # 1. 拦截相对目录穿越 ..
        with pytest.raises(PermissionError):
            resolve_safe_path(self.source_dir, "../.env")

        # 2. 拦截绝对目录越界
        external_dir = tempfile.gettempdir()
        with pytest.raises(PermissionError):
            resolve_safe_path(self.source_dir, os.path.join(external_dir, "malicious.txt"))

    def test_symlink_hijacking_prevention(self):
        # 仅在非 Windows 或支持 symlink 的环境下测试
        target_outside = os.path.join(self.temp_base, "secret.env")
        with open(target_outside, "w") as f:
            f.write("sensitive_keys")

        link_inside = os.path.join(self.source_dir, "malicious_link.txt")
        try:
            os.symlink(target_outside, link_inside)
        except (OSError, NotImplementedError):
            pytest.skip("当前系统不支持创建软链接，跳过软链接安全校验测试。")

        # 尝试通过 resolve 软链接指向外部文件，应当拦截
        with pytest.raises(PermissionError):
            resolve_safe_path(self.source_dir, "malicious_link.txt")

    def test_extension_filtering(self):
        # 1. 安全类型后缀判断
        assert is_safe_extension("book.txt", [".txt", ".md"]) is True
        assert is_safe_extension("script.py", [".txt", ".md"]) is False

        # 2. 拦截黑名单文件读取
        env_file = os.path.join(self.source_dir, ".env")
        with open(env_file, "w") as f:
            f.write("SECRET=1")

        with pytest.raises(PermissionError) as exc:
            assert_read_allowed(env_file)
        assert "restricted extension" in str(exc.value)

        # 3. 允许白名单文件读取
        safe_file = os.path.join(self.source_dir, "novel.txt")
        with open(safe_file, "w") as f:
            f.write("正文")
        assert_read_allowed(safe_file)  # 应通过无报错

    def test_feature_flag_disable_blocking(self):
        # 禁用本地访问功能
        update_local_library_config({"allow_local_file_access": False})
        
        safe_file = os.path.join(self.source_dir, "novel.txt")
        with pytest.raises(PermissionError) as exc:
            assert_read_allowed(safe_file)
        assert "ALLOW_LOCAL_FILE_ACCESS" in str(exc.value)

    def test_write_guard_checks(self):
        # 1. 允许在 essence_dir 目录下写入 md
        safe_essence_file = os.path.join(self.essence_dir, "style_bible.md")
        assert_write_allowed(safe_essence_file)

        # 2. 禁止在 source_dir 目录下写入
        outside_essence = os.path.join(self.source_dir, "should_fail.md")
        with pytest.raises(PermissionError):
            assert_write_allowed(outside_essence)

        # 3. 拦截黑名单文件写入
        malicious_write = os.path.join(self.essence_dir, "hack.db")
        with pytest.raises(PermissionError):
            assert_write_allowed(malicious_write)
