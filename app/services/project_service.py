from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, db: Session, user_id: int):
        self.project_repo = ProjectRepository(db, user_id)
        self.user_id = user_id

    def get_all_projects(self) -> List[Project]:
        return self.project_repo.get_all()

    def get_project_by_id(self, project_id: int) -> Optional[Project]:
        return self.project_repo.get_by_id(project_id)

    def get_projects_by_status(self, status: str) -> List[Project]:
        return self.project_repo.get_by_status(status)

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        technologies: Optional[str] = None,
        status: str = "not_started",
        github_link: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            technologies=technologies,
            status=status,
            github_link=github_link,
            notes=notes,
            user_id=self.user_id,
        )
        return self.project_repo.create(project)

    def update_project(self, project_id: int, data: dict) -> Optional[Project]:
        project = self.project_repo.get_by_id(project_id)
        if project:
            if data.get("status") == "completed" and not project.completed_at:
                data["completed_at"] = datetime.now()
            return self.project_repo.update(project, data)
        return None

    def delete_project(self, project_id: int) -> bool:
        return self.project_repo.delete(project_id)

    def get_completed_count(self) -> int:
        return len(self.project_repo.get_by_status("completed"))
