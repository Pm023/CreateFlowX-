from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate

def get_client_by_id(db: Session, client_id: int, user_id: int) -> Optional[Client]:
    """
    Fetches a client by ID, restricted by user_id to enforce multi-tenant isolation.
    """
    return db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()

def get_clients(db: Session, user_id: int, search: Optional[str] = None) -> List[Client]:
    """
    Retrieves all clients belonging to a user, with optional search query filtering.
    """
    query = db.query(Client).filter(Client.user_id == user_id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Client.client_name.ilike(search_filter),
                Client.company_name.ilike(search_filter),
                Client.notes.ilike(search_filter)
            )
        )
        
    return query.order_by(Client.client_name.asc()).all()

def create_client(db: Session, obj_in: ClientCreate, user_id: int) -> Client:
    """
    Creates a new client record tied to the active user.
    """
    db_obj = Client(
        user_id=user_id,
        client_name=obj_in.client_name.strip(),
        company_name=obj_in.company_name.strip() if obj_in.company_name else None,
        notes=obj_in.notes.strip() if obj_in.notes else None
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Dispatch client_added notification/activity
    from app.services.dispatcher import dispatcher
    dispatcher.dispatch(
        db=db,
        user_id=user_id,
        notification_type="client_added",
        title="Client Added",
        message=f"Client \"{db_obj.client_name}\" was successfully added."
    )

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user_id,
        action_type="create",
        entity_type="client",
        entity_id=db_obj.id,
        title="Client Created",
        description=f"Client '{db_obj.client_name}' was created."
    )

    return db_obj


def update_client(db: Session, db_client: Client, obj_in: ClientUpdate) -> Client:
    """
    Updates client details.
    """
    update_data = obj_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if isinstance(value, str):
            setattr(db_client, field, value.strip())
        else:
            setattr(db_client, field, value)
            
    db.commit()
    db.refresh(db_client)

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=db_client.user_id,
        action_type="update",
        entity_type="client",
        entity_id=db_client.id,
        title="Client Updated",
        description=f"Client '{db_client.client_name}' was updated."
    )

    return db_client

def delete_client(db: Session, db_client: Client) -> Client:
    """
    Deletes the client from the database.
    """
    user_id = db_client.user_id
    client_id = db_client.id
    client_name = db_client.client_name

    db.delete(db_client)
    db.commit()

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user_id,
        action_type="delete",
        entity_type="client",
        entity_id=client_id,
        title="Client Deleted",
        description=f"Client '{client_name}' was deleted."
    )

    return db_client
