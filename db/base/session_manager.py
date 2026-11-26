from contextlib import contextmanager
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from ..models import Base


def _ensure_sqlite_dir(db_path: str) -> None:
    """SQLite 文件所在目录不存在时自动创建，避免首次启动报 unable to open database file"""
    if not db_path.startswith("sqlite:///") or db_path.startswith("sqlite:///:memory:"):
        return
    db_file = db_path[len("sqlite:///") :]
    parent = os.path.dirname(db_file)
    if parent:
        os.makedirs(parent, exist_ok=True)


class SessionManager:
    """
    数据库会话管理器
    
    职责：
    1. 管理数据库连接和会话
    2. 提供统一的会话上下文管理
    3. 处理事务和异常回滚
    """
    
    def __init__(self, db_path='sqlite:///data/smart_appointment.db'):
        """
        初始化会话管理器
        
        Args:
            db_path: 数据库连接路径
        """
        self.engine = create_engine(db_path)
        _ensure_sqlite_dir(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    @contextmanager
    def session_scope(self):
        """
        提供会话上下文管理
        
        自动处理：
        - 会话创建和关闭
        - 事务提交和回滚
        - 异常处理
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """关闭会话管理器"""
        self.Session.remove()
        self.engine.dispose()
