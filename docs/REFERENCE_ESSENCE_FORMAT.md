# 参考书精华文件格式说明

## 1. 简介
系统为了保证速度、安全性和脱离数据库强依赖，将解析提炼出的产物（精华，Essence）全部序列化存放在用户指定的 `REFERENCE_ESSENCE_DIR` 目录下的纯文本格式（JSON）中。
这样即使系统重置，精华文件也可以被直接挂载复用，甚至可以通过 Git 进行版本控制或团队分享。

## 2. 目录结构
假设一本书的 ID 为 `zhuxian_book`，其精华目录结构如下：

```
[REFERENCE_ESSENCE_DIR]/
  └── zhuxian_book/
       ├── manifest.json                  # 全局索引表
       ├── summary_full_book.json         # 全书总结（含主线、世界观）
       ├── style_bible.json               # 风格圣经
       ├── volume_summaries.json          # 各卷总结与人物弧光
       ├── scene_patterns.json            # 提取出的经典场景套路模板
       ├── chapter_summaries/             # 章节级别拆解
       │    ├── chapter_1_summary.json
       │    ├── chapter_2_summary.json
       │    └── ...
       └── chapter_analysis/              # 更深层次的节拍拆解（预留）
```

## 3. manifest.json 结构
`manifest.json` 是单本书的总控台，记录了文件的来源校验以及生成的元数据：

```json
{
  "book_id": "zhuxian_book",
  "source_path": "D:/books/zhuxian.txt",
  "source_hash": "a1b2c3d4...",
  "generated_at": "2026-06-25T12:00:00Z",
  "schema_version": "1.0",
  "absorb_status": "completed",
  "files": {
    "style_bible": "style_bible.json",
    "summary_full_book": "summary_full_book.json",
    ...
  }
}
```

## 4. 为什么不存进数据库？
- **版权安全**：纯粹依靠文件系统隔离，不在主库留下任何涉嫌侵权的痕迹。
- **可移植性**：用户可以直接把提取后的精华打包发给协作者，无需做任何 DB 导入导出。
- **防止超长记录**：几十万字的摘要和分析如果在数据库单条记录里会造成极差的性能。文件系统对于大 JSON 有天然的支持。
