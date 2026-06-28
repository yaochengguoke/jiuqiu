# -*- coding: utf-8 -*-
"""
项目持久化存储 — SQLite 替代 JSON 文件

提供项目元数据的增删查, 支持历史回溯。
不影响现有 JSON 数据池 (data_pool/) 的运行时读写。
"""
import sqlite3, json, os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


DB_PATH = Path(__file__).parent / "outputs" / "projects.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表 (幂等)"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            competition TEXT NOT NULL,
            status      TEXT DEFAULT 'draft',
            word_count  INTEGER DEFAULT 0,
            output_dir  TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_data (
            project_id  INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
            raw_submission TEXT,       -- JSON: 原始提交数据
            data_pool     TEXT,         -- JSON: 中央数据池快照
            quality_report TEXT         -- JSON: 质量检查结果
        );
        CREATE TABLE IF NOT EXISTS project_files (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            file_type   TEXT NOT NULL,  -- 'docx','pdf','html','md','pptx','chart','other'
            file_path   TEXT NOT NULL,
            file_size   INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_files_project ON project_files(project_id);
    """)
    conn.commit()
    conn.close()


class ProjectStore:
    """项目持久化存储"""

    def __init__(self):
        init_db()

    def create_project(
        self,
        name: str,
        competition: str,
        raw_submission: dict = None,
        output_dir: str = None,
    ) -> int:
        """创建新项目, 返回项目ID"""
        now = datetime.now().isoformat()
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO projects (name, competition, status, output_dir, created_at, updated_at) "
            "VALUES (?, ?, 'draft', ?, ?, ?)",
            (name, competition, output_dir, now, now),
        )
        pid = cur.lastrowid
        if raw_submission:
            conn.execute(
                "INSERT INTO project_data (project_id, raw_submission) VALUES (?, ?)",
                (pid, json.dumps(raw_submission, ensure_ascii=False)),
            )
        conn.commit()
        conn.close()
        return pid

    def update_status(
        self,
        project_id: int,
        status: str,
        word_count: int = None,
        data_pool: dict = None,
        quality_report: dict = None,
    ):
        """更新项目状态和元数据"""
        now = datetime.now().isoformat()
        conn = _get_conn()
        parts = ["status = ?", "updated_at = ?"]
        params = [status, now]
        if word_count is not None:
            parts.append("word_count = ?")
            params.append(word_count)
        params.append(project_id)
        conn.execute(
            f"UPDATE projects SET {', '.join(parts)} WHERE id = ?",
            params,
        )
        # Upsert project_data
        existing = conn.execute(
            "SELECT project_id FROM project_data WHERE project_id = ?", (project_id,)
        ).fetchone()
        data_update = {}
        if data_pool:
            data_update["data_pool"] = json.dumps(data_pool, ensure_ascii=False)
        if quality_report:
            data_update["quality_report"] = json.dumps(quality_report, ensure_ascii=False)
        if data_update:
            if existing:
                set_clause = ", ".join(f"{k}=?" for k in data_update)
                conn.execute(
                    f"UPDATE project_data SET {set_clause} WHERE project_id=?",
                    (*data_update.values(), project_id),
                )
            else:
                conn.execute(
                    "INSERT INTO project_data (project_id, data_pool, quality_report) "
                    "VALUES (?, ?, ?)",
                    (project_id,
                     data_update.get("data_pool", "{}"),
                     data_update.get("quality_report", "{}")),
                )
        conn.commit()
        conn.close()

    def add_file(self, project_id: int, file_type: str, file_path: str):
        """记录项目输出文件"""
        size = 0
        try: size = os.path.getsize(file_path)
        except OSError: pass
        conn = _get_conn()
        conn.execute(
            "INSERT INTO project_files (project_id, file_type, file_path, file_size) "
            "VALUES (?, ?, ?, ?)",
            (project_id, file_type, file_path, size),
        )
        conn.commit()
        conn.close()

    def get_project(self, project_id: int) -> Optional[dict]:
        """获取项目详情"""
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            conn.close(); return None
        data_row = conn.execute(
            "SELECT * FROM project_data WHERE project_id = ?", (project_id,)
        ).fetchone()
        files = conn.execute(
            "SELECT * FROM project_files WHERE project_id = ? ORDER BY file_type",
            (project_id,),
        ).fetchall()
        conn.close()
        return {
            **dict(row),
            "raw_submission": json.loads(data_row["raw_submission"]) if data_row and data_row["raw_submission"] else None,
            "data_pool": json.loads(data_row["data_pool"]) if data_row and data_row["data_pool"] else None,
            "files": [dict(f) for f in files],
        }

    def list_projects(self, limit: int = 20, offset: int = 0) -> List[dict]:
        """列出最近项目"""
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, name, competition, status, word_count, created_at "
            "FROM projects ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_project(self, project_id: int):
        """删除项目及其关联数据"""
        conn = _get_conn()
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()

    def total_count(self) -> int:
        conn = _get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()
        conn.close()
        return row["cnt"] if row else 0


# 快捷方法: 从Agent完成后保存
def save_project_from_agent(agent, raw_submission: dict = None):
    """Agent完成生成后调用, 一键持久化"""
    store = ProjectStore()
    project_name = agent.current_document.project_name if agent.current_document else "未命名"
    competition = agent.current_template.competition_name if agent.current_template else "未知"
    word_count = agent.current_document.total_word_count if agent.current_document else 0
    output_dir = str(agent.current_export.output_dir) if agent.current_export else None

    pid = store.create_project(
        name=project_name,
        competition=competition,
        raw_submission=raw_submission,
        output_dir=output_dir,
    )

    # 记录输出文件
    if agent.current_export:
        out = agent.current_export.output_dir
        if out.exists():
            for f in out.iterdir():
                if f.is_file():
                    ext = f.suffix.lstrip('.')
                    store.add_file(pid, ext, str(f))

    store.update_status(pid, "completed", word_count=word_count)
    return pid
