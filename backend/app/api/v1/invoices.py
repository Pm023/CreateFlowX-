from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.client import Client
from app.models.project import Project
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceOut
from app.crud import invoice as crud_invoice

router = APIRouter()

@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new Invoice record. Enforces that both the client and project
    belong to the authenticated user.
    """
    client = db.query(Client).filter(Client.id == invoice_in.client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or unauthorized."
        )

    project = db.query(Project).filter(Project.id == invoice_in.project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized."
        )

    return crud_invoice.create_invoice(db, obj_in=invoice_in, user_id=current_user.id)

@router.get("/", response_model=List[InvoiceOut])
def read_invoices(
    search: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all invoices belonging to the active user. Supports search by invoice number,
    client, or project, and filtering by status, client, or project.
    """
    return crud_invoice.get_invoices(
        db,
        user_id=current_user.id,
        search=search,
        status=status,
        client_id=client_id,
        project_id=project_id
    )

@router.get("/stats", status_code=status.HTTP_200_OK)
def read_revenue_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves total revenue totals, invoice counts, monthly trends, and charts configurations.
    """
    return crud_invoice.get_revenue_statistics(db, user_id=current_user.id)

@router.get("/{invoice_id}", response_model=InvoiceOut)
def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a single invoice by ID, ensuring the authenticated user owns it.
    """
    # 1. Run dynamic overdue updates
    crud_invoice.check_and_update_overdue(db, user_id=current_user.id)

    invoice = crud_invoice.get_invoice_by_id(db, invoice_id=invoice_id, user_id=current_user.id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found."
        )
    return invoice

@router.put("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates details of an invoice, enforcing strict user ownership and verifying client/project links.
    """
    invoice = crud_invoice.get_invoice_by_id(db, invoice_id=invoice_id, user_id=current_user.id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found."
        )

    if invoice_in.client_id is not None:
        client = db.query(Client).filter(Client.id == invoice_in.client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found or unauthorized."
            )

    if invoice_in.project_id is not None:
        project = db.query(Project).filter(Project.id == invoice_in.project_id, Project.user_id == current_user.id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or unauthorized."
            )

    return crud_invoice.update_invoice(db, db_invoice=invoice, obj_in=invoice_in)

@router.delete("/{invoice_id}", response_model=InvoiceOut)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes an invoice after asserting strict user ownership.
    """
    invoice = crud_invoice.get_invoice_by_id(db, invoice_id=invoice_id, user_id=current_user.id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found."
        )
    return crud_invoice.delete_invoice(db, db_invoice=invoice)
