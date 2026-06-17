from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy.orm import Session

class NotificationChannel(ABC):
    @abstractmethod
    def send(self, db: Session, user_id: int, notification_type: str, title: str, message: str, project_id: Optional[int] = None, task_id: Optional[int] = None, reminder_rule: Optional[str] = None):
        pass

class InAppChannel(NotificationChannel):
    def send(self, db: Session, user_id: int, notification_type: str, title: str, message: str, project_id: Optional[int] = None, task_id: Optional[int] = None, reminder_rule: Optional[str] = None):
        # Local import to prevent circular import between crud.notification and services.dispatcher
        from app.crud.notification import create_notification
        return create_notification(
            db=db,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            project_id=project_id,
            task_id=task_id,
            reminder_rule=reminder_rule
        )

class EmailChannel(NotificationChannel):
    def send(self, db: Session, user_id: int, notification_type: str, title: str, message: str, project_id: Optional[int] = None, task_id: Optional[int] = None, reminder_rule: Optional[str] = None):
        # FUTURE: Fetch user email from db using user_id, format message, and send email.
        # print(f"[Email Channel] Sent to user {user_id}: {title} - {message}")
        pass

class WhatsAppChannel(NotificationChannel):
    def send(self, db: Session, user_id: int, notification_type: str, title: str, message: str, project_id: Optional[int] = None, task_id: Optional[int] = None, reminder_rule: Optional[str] = None):
        # FUTURE: Format and send WhatsApp alert using Twilio or local gateway.
        # print(f"[WhatsApp Channel] Sent to user {user_id}: {title} - {message}")
        pass

class PushChannel(NotificationChannel):
    def send(self, db: Session, user_id: int, notification_type: str, title: str, message: str, project_id: Optional[int] = None, task_id: Optional[int] = None, reminder_rule: Optional[str] = None):
        # FUTURE: Send Firebase Cloud Messaging or Web Push notification.
        # print(f"[Push Channel] Sent to user {user_id}: {title} - {message}")
        pass

class NotificationDispatcher:
    def __init__(self, channels: Optional[List[NotificationChannel]] = None):
        if channels is None:
            self.channels = [InAppChannel(), EmailChannel(), WhatsAppChannel(), PushChannel()]
        else:
            self.channels = channels

    def dispatch(self, db: Session, user_id: int, notification_type: str, title: str, message: str, project_id: Optional[int] = None, task_id: Optional[int] = None, reminder_rule: Optional[str] = None):
        for channel in self.channels:
            try:
                channel.send(
                    db=db,
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    project_id=project_id,
                    task_id=task_id,
                    reminder_rule=reminder_rule
                )
            except Exception as e:
                # Log dispatch error but do not break execution of subsequent channels
                # print(f"Failed to dispatch channel: {e}")
                pass

dispatcher = NotificationDispatcher()
