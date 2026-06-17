from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.client import ClientCreate, ClientUpdate, ClientOut
from app.crud import client as crud_client

router = APIRouter()

@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new Client record mapped to the current authenticated User.
    """
    return crud_client.create_client(db, obj_in=client_in, user_id=current_user.id)

@router.get("/", response_model=List[ClientOut])
def read_clients(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all Client records belonging to the authenticated User.
    Supports optional case-insensitive search filtering.
    """
    return crud_client.get_clients(db, user_id=current_user.id, search=search)

@router.get("/{client_id}", response_model=ClientOut)
def read_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a specific Client record by its ID.
    Asserts ownership before returning, throwing a 404 if not found or unauthorized.
    """
    client = crud_client.get_client_by_id(db, client_id=client_id, user_id=current_user.id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found."
        )
    return client

@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates details of a specific Client record.
    Asserts ownership before applying edits, throwing a 404 if unauthorized.
    """
    client = crud_client.get_client_by_id(db, client_id=client_id, user_id=current_user.id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found."
        )
    return crud_client.update_client(db, db_client=client, obj_in=client_in)

@router.delete("/{client_id}", response_model=ClientOut)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a specific Client record.
    Asserts ownership before deleting, throwing a 404 if unauthorized.
    """
    client = crud_client.get_client_by_id(db, client_id=client_id, user_id=current_user.id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found."
        )
    return crud_client.delete_client(db, db_client=client)
