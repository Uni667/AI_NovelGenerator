import pytest


class TestLocalLibraryContract:
    """测试本地文件夹吸收系统的架构契约与路由占位符是否符合 schema。"""

    def test_get_and_update_config(self, client, auth_headers):
        # 1. GET config
        response = client.get("/api/v1/local-library/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "source_dir" in data
        assert "allow_local_file_access" in data

        # 2. PUT config
        update_payload = {
            "source_dir": "D:/NovelLibrary/books",
            "essence_dir": "D:/NovelLibrary/essence",
            "allow_local_file_access": True,
            "watcher_enabled": True
        }
        response_update = client.put("/api/v1/local-library/config", json=update_payload, headers=auth_headers)
        assert response_update.status_code == 200
        data_update = response_update.json()
        assert data_update["source_dir"] == "D:/NovelLibrary/books"
        assert data_update["allow_local_file_access"] is True
        assert data_update["watcher_enabled"] is True

    def test_config_directory_status_test(self, client, auth_headers):
        payload = {
            "source_dir": "invalid_dir_mock",
            "essence_dir": "invalid_dir_mock"
        }
        response = client.post("/api/v1/local-library/config/test", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "source_dir" in data
        assert "essence_dir" in data
        assert data["success"] is False

    def test_scan_library_guard_blocked_by_default(self, client, auth_headers):
        # 首先重置 config 里的 allow_local_file_access 为 False
        client.put("/api/v1/local-library/config", json={"allow_local_file_access": False}, headers=auth_headers)
        
        # 触发 scan 应该报错 403 (PermissionError)
        response = client.post("/api/v1/local-library/scan", headers=auth_headers)
        assert response.status_code == 403

        # 开启 allow_local_file_access 后应该成功返回 scan 报表
        client.put("/api/v1/local-library/config", json={"allow_local_file_access": True}, headers=auth_headers)
        response_ok = client.post("/api/v1/local-library/scan", headers=auth_headers)
        assert response_ok.status_code == 200
        data = response_ok.json()
        assert "total_files" in data
        assert "new_books" in data

    def test_get_books_and_chapters_index(self, client, auth_headers, tmp_path):
        from backend.app.database import get_db
        import uuid
        import datetime
        
        # Insert a dummy book and file
        book_id = str(uuid.uuid4())
        book_file = tmp_path / "doupo.txt"
        book_file.write_text("第一章 陨落的奇才\n这里是正文\n", encoding="utf-8")
        
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO local_reference_book (
                    id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, "斗破虚空", "doupo.txt", ".txt", "dummyhash", now, str(book_file), "utf-8", 100, "pending", now, now))
            conn.commit()

        # Call parse
        response_parse = client.post(f"/api/v1/local-library/books/{book_id}/parse", headers=auth_headers)
        assert response_parse.status_code == 200

        # 1. List books
        response_books = client.get("/api/v1/local-library/books", headers=auth_headers)
        assert response_books.status_code == 200
        books = [b for b in response_books.json() if b["id"] == book_id]
        assert len(books) == 1
        assert books[0]["title"] == "斗破虚空"

        # 2. Get details
        response_detail = client.get(f"/api/v1/local-library/books/{book_id}", headers=auth_headers)
        assert response_detail.status_code == 200
        assert response_detail.json()["id"] == book_id

        # 3. Get chapters
        response_chapters = client.get(f"/api/v1/local-library/books/{book_id}/chapters", headers=auth_headers)
        assert response_chapters.status_code == 200
        chapters = response_chapters.json()
        assert len(chapters) > 0
        assert "陨落的奇才" in chapters[0]["title"]
        
        # 4. Patch chapter
        response_patch = client.patch(
            f"/api/v1/local-library/books/{book_id}/chapters/{chapters[0]['id']}",
            json={"title": "第一章 奇才崛起"},
            headers=auth_headers
        )
        assert response_patch.status_code == 200
        assert response_patch.json()["title"] == "第一章 奇才崛起"

    def test_absorption_task_control(self, client, auth_headers):
        from backend.app.database import get_db
        import uuid
        import datetime
        
        book_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO local_reference_book (
                    id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, "任务测试", "task.txt", ".txt", "h2", now, "/dummy/task.txt", "utf-8", 100, "pending", now, now))
            conn.commit()

        # 1. Absorb
        res_absorb = client.post(f"/api/v1/local-library/books/{book_id}/absorb", headers=auth_headers)
        if res_absorb.status_code != 200:
            print(res_absorb.json())
        assert res_absorb.status_code == 200
        task_id = res_absorb.json()["task_id"]
        assert task_id.startswith("task_absorb_")

        # 2. Pause
        res_pause = client.post(f"/api/v1/local-library/books/{book_id}/absorb/pause", headers=auth_headers)
        assert res_pause.status_code == 200
        assert res_pause.json()["status"] == "paused"

        # 3. Resume
        res_resume = client.post(f"/api/v1/local-library/books/{book_id}/absorb/resume", headers=auth_headers)
        assert res_resume.status_code == 200
        assert res_resume.json()["status"] == "running"

        # 4. Cancel
        res_cancel = client.post(f"/api/v1/local-library/books/{book_id}/absorb/cancel", headers=auth_headers)
        assert res_cancel.status_code == 200
        assert res_cancel.json()["status"] == "cancelled"

    def test_get_essence_file(self, client, auth_headers, tmp_path):
        from backend.app.database import get_db
        import uuid
        import datetime
        from backend.app.services.local_essence_writer_service import initialize_essence_directory, write_essence_file
        
        book_id = str(uuid.uuid4())
        book_file = tmp_path / "doupo_essence.txt"
        book_file.write_text("第一章 陨落的奇才\n", encoding="utf-8")
        
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO local_reference_book (
                    id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, "斗破虚空", "doupo_essence.txt", ".txt", "dummyhash2", now, str(book_file), "utf-8", 100, "pending", now, now))
            conn.commit()

        # Init essence and write a dummy file
        initialize_essence_directory(book_id)
        write_essence_file(book_id, "style_bible.md", "# 风格圣经\n- 节奏：前紧后舒\n")
        
        response = client.get(f"/api/v1/local-library/books/{book_id}/essence?file_key=style_bible.md", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["file_key"] == "style_bible.md"
        assert "风格圣经" in data["content"]

    def test_project_bindings_flow(self, client, auth_headers, test_project, tmp_path):
        from backend.app.database import get_db
        import uuid
        import datetime
        pid = test_project["id"]
        book_id = str(uuid.uuid4())
        book_file = tmp_path / "binding_dummy.txt"
        book_file.write_text("dummy", encoding="utf-8")
        
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO local_reference_book (
                    id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (book_id, "Dummy", "binding_dummy.txt", ".txt", "dummyhash", now, str(book_file), "utf-8", 10, "pending", now, now))
            conn.commit()
            
        from backend.app.services.local_essence_writer_service import initialize_essence_directory, write_essence_file
        initialize_essence_directory(book_id)
        write_essence_file(book_id, "style_bible.md", "# 风格圣经\n- mock style bible excerpt\n")
        # 1. List bindings
        res_list = client.get(f"/api/v1/projects/{pid}/local-reference-books", headers=auth_headers)
        assert res_list.status_code == 200
        assert isinstance(res_list.json(), list)

        # 2. Bind reference book
        payload = {
            "book_id": book_id,
            "weight": 1.2,
            "use_style_bible": True
        }
        res_bind = client.post(f"/api/v1/projects/{pid}/local-reference-books", json=payload, headers=auth_headers)
        assert res_bind.status_code == 200
        assert res_bind.json()["book_id"] == book_id
        assert res_bind.json()["weight"] == 1.2

        # 3. Preview context
        res_preview = client.post(f"/api/v1/projects/{pid}/reference-context/preview", headers=auth_headers)
        assert res_preview.status_code == 200
        assert "style_bible_excerpt" in res_preview.json()

        # 4. Unbind reference book
        res_unbind = client.delete(f"/api/v1/projects/{pid}/local-reference-books/{book_id}", headers=auth_headers)
        assert res_unbind.status_code == 200
        assert "解绑成功" in res_unbind.json()["message"]
