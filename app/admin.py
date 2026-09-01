from sqladmin import ModelView
from app.models.learning_path import LearningPathModel


class LearningPathAdmin(ModelView, model=LearningPathModel):
    column_list = [LearningPathModel.id, LearningPathModel.title, LearningPathModel.topic, LearningPathModel.difficulty, LearningPathModel.created_at]
    column_searchable_list = [LearningPathModel.title, LearningPathModel.topic]
    column_sortable_list = [LearningPathModel.id, LearningPathModel.created_at]
