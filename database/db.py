import json
import logging
from datetime import datetime

import mysql.connector
from mysql.connector import Error

from config.settings import (
    MYSQL_DB,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)

logger = logging.getLogger(__name__)


def get_connection():
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
        return conn
    except Error as e:
        logger.error(f"MySQL connection error: {e}")
        raise


def init_db():
    """Initialize database and tables."""
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    cursor.close()
    conn.close()

    conn = get_connection()
    cursor = conn.cursor()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            overall_style LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS template_pages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            template_id INT NOT NULL,
            page_number INT NOT NULL,
            markdown_content LONGTEXT,
            layout_json LONGTEXT,
            visual_json LONGTEXT,
            generation_hints LONGTEXT,
            page_type VARCHAR(50) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS generation_jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_requirements LONGTEXT,
            input_files LONGTEXT,
            selected_template_id INT,
            outline_json LONGTEXT,
            content_markdown LONGTEXT,
            layout_json LONGTEXT,
            rendered_pptx_path VARCHAR(500),
            final_pptx_path VARCHAR(500),
            status VARCHAR(50) DEFAULT 'created',
            logs LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (selected_template_id) REFERENCES templates(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    ]

    for sql in tables:
        cursor.execute(sql)

    # Add generation_hints column if not exists (migration for existing DB)
    try:
        cursor.execute("""
            ALTER TABLE template_pages
            ADD COLUMN generation_hints LONGTEXT
        """)
        conn.commit()
        logger.info("Added generation_hints column to template_pages.")
    except Error as e:
        if "Duplicate column name" in str(e):
            logger.debug("generation_hints column already exists.")
        else:
            logger.warning(f"Migration check for generation_hints: {e}")

    # Add page_type column if not exists (PR-Q3a migration; duplicate-tolerant, additive,
    # nullable — existing rows keep NULL and remain valid; no pagetype LONGTEXT).
    try:
        cursor.execute("""
            ALTER TABLE template_pages
            ADD COLUMN page_type VARCHAR(50) DEFAULT NULL
        """)
        conn.commit()
        logger.info("Added page_type column to template_pages.")
    except Error as e:
        if "Duplicate column name" in str(e):
            logger.debug("page_type column already exists.")
        else:
            logger.warning(f"Migration check for page_type: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Database initialized.")


class TemplateDAO:
    @staticmethod
    def create(name: str, file_path: str, overall_style: dict) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO templates (name, file_path, overall_style) VALUES (%s, %s, %s)"
        cursor.execute(sql, (name, file_path, json.dumps(overall_style, ensure_ascii=False)))
        conn.commit()
        tid = cursor.lastrowid
        cursor.close()
        conn.close()
        return tid

    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM templates")
        rows = cursor.fetchall()
        for row in rows:
            if row.get("overall_style"):
                row["overall_style"] = json.loads(row["overall_style"])
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_by_id(tid: int):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM templates WHERE id = %s", (tid,))
        row = cursor.fetchone()
        if row and row.get("overall_style"):
            row["overall_style"] = json.loads(row["overall_style"])
        cursor.close()
        conn.close()
        return row


class TemplatePageDAO:
    @staticmethod
    def create(template_id: int, page_number: int, markdown_content: str, layout_json: dict, visual_json: dict, generation_hints: dict = None, page_type: str = None):
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO template_pages (template_id, page_number, markdown_content, layout_json, visual_json, generation_hints, page_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            template_id, page_number, markdown_content,
            json.dumps(layout_json, ensure_ascii=False),
            json.dumps(visual_json, ensure_ascii=False),
            json.dumps(generation_hints, ensure_ascii=False) if generation_hints else None,
            page_type,
        ))
        conn.commit()
        pid = cursor.lastrowid
        cursor.close()
        conn.close()
        return pid

    @staticmethod
    def get_by_template(template_id: int):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM template_pages WHERE template_id = %s ORDER BY page_number", (template_id,))
        rows = cursor.fetchall()
        for row in rows:
            if row.get("layout_json"):
                row["layout_json"] = json.loads(row["layout_json"])
            if row.get("visual_json"):
                row["visual_json"] = json.loads(row["visual_json"])
            if row.get("generation_hints"):
                row["generation_hints"] = json.loads(row["generation_hints"])
        cursor.close()
        conn.close()
        return rows


class GenerationJobDAO:
    @staticmethod
    def create(user_requirements: str, input_files: list) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO generation_jobs (user_requirements, input_files, logs) VALUES (%s, %s, %s)"
        logs_data = [{"step": "job_created", "time": datetime.now().isoformat(), "input_files": input_files}]
        cursor.execute(sql, (user_requirements, json.dumps(input_files, ensure_ascii=False), json.dumps(logs_data, ensure_ascii=False)))
        conn.commit()
        jid = cursor.lastrowid
        cursor.close()
        conn.close()
        return jid

    @staticmethod
    def update(jid: int, **kwargs):
        conn = get_connection()
        cursor = conn.cursor()
        allowed = ["selected_template_id", "outline_json", "content_markdown", "layout_json",
                   "rendered_pptx_path", "final_pptx_path", "status", "logs"]
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            sets.append(f"{k} = %s")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v, ensure_ascii=False))
            else:
                vals.append(v)
        if not sets:
            return
        sql = f"UPDATE generation_jobs SET {', '.join(sets)} WHERE id = %s"
        vals.append(jid)
        cursor.execute(sql, tuple(vals))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_by_id(jid: int):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM generation_jobs WHERE id = %s", (jid,))
        row = cursor.fetchone()
        if row:
            for k in ["outline_json", "layout_json", "input_files", "logs"]:
                if row.get(k):
                    row[k] = json.loads(row[k])
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def append_log(jid: int, log_entry: dict):
        row = GenerationJobDAO.get_by_id(jid)
        logs = row.get("logs") or []
        logs.append(log_entry)
        GenerationJobDAO.update(jid, logs=logs)
