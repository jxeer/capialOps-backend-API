"""
Notification utilities for creating Notification records.

This module provides the DB-write layer for the notification system.
Other parts of the app call create_notification() to queue notifications
for users. Real-time push (WebSockets, push notifications, etc.) is
not yet implemented — this is purely the persistence layer.

Usage:
    from app.notifications import create_notification

    create_notification(
        user_id=123,
        notification_type="entitlement_update",
        title="Entitlement Status Changed",
        body="The variance application for The Meridian has been approved.",
        related_entity_type="entitlement_record",
        related_entity_id=456
    )
"""

from app import db
from app.models import Notification


def create_notification(
    user_id,
    notification_type,
    title,
    body,
    related_entity_type=None,
    related_entity_id=None
):
    """
    Create and persist a notification for a user.

    Args:
        user_id: The ID of the user to notify
        notification_type: Type string (e.g., "entitlement_update", "permit_event",
                          "work_order_assigned")
        title: Short title for the notification
        body: Full notification text
        related_entity_type: Optional entity type (e.g., "entitlement_record",
                             "work_order") for linking
        related_entity_id: Optional ID of the related entity

    Returns:
        Notification: The created notification record
    """
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        is_read=False,
    )
    db.session.add(notification)
    db.session.commit()
    return notification