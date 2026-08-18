from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.project import Project


class ProjectRepository:
    def __init__(self, db: Session, user_id: int, study_mode: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.study_mode = study_mode

    def _base_query(self):
        q = self.db.query(Project).filter(Project.user_id == self.user_id)
        if self.study_mode is not None:
            q = q.filter(Project.study_mode == self.study_mode)
        return q

    def get_all(self) -> List[Project]:
        return self._base_query().order_by(Project.created_at.desc()).all()

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self._base_query().filter(Project.id == project_id).first()

    def get_by_status(self, status: str) -> List[Project]:
        return self._base_query().filter(Project.status == status).all()

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, project: Project, data: dict) -> Project:
        allowed_fields = {"name", "description", "technologies", "status", "github_link", "notes", "completed_at"}
        for key, value in data.items():
            if value is not None and key in allowed_fields:
                setattr(project, key, value)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project_id: int) -> bool:
        project = self.get_by_id(project_id)
        if project:
            self.db.delete(project)
            self.db.commit()
            return True
        return False
