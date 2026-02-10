from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, schemas
from datetime import date, datetime
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

PDF_DIR = "deliveries_pdf"
os.makedirs(PDF_DIR, exist_ok=True)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.dni == user.dni).first()
    if db_user:
        raise HTTPException(status_code=400, detail="DNI already registered")
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/api/users/{dni}", response_model=schemas.User)
def read_user(dni: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.dni == dni).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def determine_items(contract_type: str):
    items = []
    if contract_type == "Regular Otro sindicato":
        items = [
            {"name": "Juego de Uniforme (Chaqueta, Pantalon, Polo, Polera)", "qty": 2},
            {"name": "Jabones de tocador", "qty": 24},
            {"name": "Toallas", "qty": 2}
        ]
    elif contract_type == "Regular PYA":
        items = [
            {"name": "Juego de Uniforme (Chaqueta, Pantalon, Polo, Polera)", "qty": 3},
            {"name": "Jabones Bolivar", "qty": 24},
            {"name": "Jabones de tocador", "qty": 22},
            {"name": "Toallas", "qty": 2}
        ]
    elif contract_type == "Temporal":
        items = [
            {"name": "Juego de Uniforme (Chaqueta, Pantalon, Polo, Polera)", "qty": 3},
            {"name": "Par de zapatos", "qty": 1},
            {"name": "Candado", "qty": 1},
            {"name": "Casillero", "qty": 1},
             {"name": "Jabones Bolivar", "qty": 2}
        ]
    return items



def generate_pdf(delivery_id, user, items, delivery_date):
    filename = f"delivery_{delivery_id}.pdf"
    filepath = os.path.join(PDF_DIR, filename)
    
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # --- Header ---
    # Logo
    logo_path = r"c:\Users\sodexo\Laptop Sodexo Sincronizada\OneDrive\Documentos\Sodexo\Laptop Sodexo\Documentos\Nueva carpeta\roperia-system\frontend\public\logo.png"
    
    if os.path.exists(logo_path):
        try:
            # Method 1: Robust ImageReader via Utils
            from reportlab.lib.utils import ImageReader
            logo = ImageReader(logo_path)
            
            # width=120, preserve aspect ratio
            iw, ih = logo.getSize()
            aspect = ih / float(iw)
            draw_width = 120
            draw_height = draw_width * aspect
            
            c.drawImage(logo, 40, height - 50 - draw_height, width=draw_width, height=draw_height, mask='auto', preserveAspectRatio=True)
            
        except Exception as e:
            # Fallback: Create generic text if image fails entirely
            print(f"Error drawing logo: {e}")
            c.drawString(40, height - 100, "SODEXO")
        
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 120, "ACTA DE ENTREGA DE UNIFORMES Y EPP")
    
    # Metadata
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 60, f"Acta N°: {delivery_id:06d}")
    c.drawRightString(width - 50, height - 75, f"Fecha: {delivery_date.strftime('%Y-%m-%d')}")
    
    # --- User Info Box ---
    y_info = height - 180
    c.setLineWidth(1)
    c.setStrokeColor(colors.lightgrey)
    c.rect(50, y_info - 60, width - 100, 70, fill=0)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y_info - 20, "DATOS DEL TRABAJADOR:")
    
    c.setFont("Helvetica", 10)
    c.drawString(60, y_info - 40, f"Nombre Completo: {user.name} {user.surname}")
    c.drawString(300, y_info - 40, f"DNI: {user.dni}")
    c.drawString(60, y_info - 55, f"Contratación: {user.contract_type}    Talla: {user.size if hasattr(user, 'size') else '-'}")

    # --- Items Table ---
    y_table = y_info - 100
    
    # Prepare Data
    data = [["Item / Descripción", "Cantidad"]]
    for item in items:
        data.append([item['name'], str(item['qty'])])

    # Table Config
    table = Table(data, colWidths=[350, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Draw Table
    w, h = table.wrap(width, height)
    table.drawOn(c, 80, y_table - h)
    
    # --- Footer / Signatures ---
    y_sig = 150
    
    c.setFont("Helvetica", 9)
    c.drawString(50, y_sig + 60, "Declaro haber recibido a mi entera satisfacción los bienes arriba descritos.")
    
    c.line(100, y_sig, 250, y_sig)
    c.drawCentredString(175, y_sig - 15, "ENTREGADO POR")
    c.drawCentredString(175, y_sig - 30, "LOGÍSTICA / ROPERÍA")
    
    c.line(350, y_sig, 500, y_sig)
    c.drawCentredString(425, y_sig - 15, "RECIBIDO POR")
    c.drawCentredString(425, y_sig - 30, f"{user.name} {user.surname}")
    c.drawCentredString(425, y_sig - 45, f"DNI: {user.dni}")
    
    c.save()
    return filepath

@app.post("/api/deliveries")
def create_delivery(delivery: schemas.DeliveryCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.dni == delivery.dni).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Use items provided in request, convert Pydantic models to dicts
    items_list = [item.dict() for item in delivery.items]
    
    try:
        new_delivery = models.Delivery(
            dni=delivery.dni,
            date=delivery.date,
            items_json=json.dumps(items_list),
            pdf_path=""
        )
        db.add(new_delivery)
        db.commit()
        db.refresh(new_delivery)
        
        # Generate PDF with provided items and date
        pdf_path = generate_pdf(new_delivery.id, user, items_list, delivery.date)
        new_delivery.pdf_path = pdf_path
        db.commit()
        
        return {"message": "Delivery created", "delivery_id": new_delivery.id, "items": items_list, "pdf_url": f"/api/deliveries/{new_delivery.id}/pdf"}
    except Exception as e:
        import traceback
        import traceback
        with open("error_log.txt", "w") as f:
            f.write(traceback.format_exc())
            f.write("\n")
            f.write(str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/deliveries/{delivery_id}/pdf")
def get_pdf(delivery_id: int, db: Session = Depends(get_db)):
    delivery = db.query(models.Delivery).filter(models.Delivery.id == delivery_id).first()
    if not delivery or not os.path.exists(delivery.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(delivery.pdf_path, media_type="application/pdf", filename=os.path.basename(delivery.pdf_path))

@app.post("/api/laundry", response_model=schemas.Laundry)
def create_laundry(laundry: schemas.LaundryCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.dni == laundry.dni).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.contract_type != "Regular Otro sindicato":
        raise HTTPException(status_code=400, detail="Este usuario no esta habilitado para este servicio")

    items_list = [item.dict() for item in laundry.items]

    new_laundry = models.Laundry(
        dni=laundry.dni,
        date=datetime.now(),
        items_json=json.dumps(items_list)
    )
    db.add(new_laundry)
    db.commit()
    db.refresh(new_laundry)
    
    return new_laundry

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    users_count = db.query(models.User).count()
    deliveries_count = db.query(models.Delivery).count()
    # Calculate active laundry users (users with pending items)
    # This logic mimics get_laundry but just returns the count
    laundry_entries = db.query(models.Laundry).all()
    laundry_returns = db.query(models.LaundryReturn).all()
    
    user_items = {} # { dni: { "ItemName": sent_qty } }
    
    for entry in laundry_entries:
        if entry.dni not in user_items: user_items[entry.dni] = {}
        items = json.loads(entry.items_json)
        for item in items:
            user_items[entry.dni][item['name']] = user_items[entry.dni].get(item['name'], 0) + item['qty']
            
    for entry in laundry_returns:
        if entry.dni in user_items:
            items = json.loads(entry.items_json)
            for item in items:
                user_items[entry.dni][item['name']] = user_items[entry.dni].get(item['name'], 0) - item['qty']

    active_laundry_users = 0
    for dni, items in user_items.items():
        # Check if any item has pending qty > 0
        if any(qty > 0 for qty in items.values()):
            active_laundry_users += 1

    laundry_total_count = db.query(models.Laundry).count()

    return {
        "users_count": users_count,
        "deliveries_count": deliveries_count,
        "laundry_total_count": laundry_total_count,
        "laundry_active_count": active_laundry_users
    }

@app.get("/api/laundry", response_model=list[schemas.LaundryPendingUser])
def get_laundry(db: Session = Depends(get_db)):
    # Fetch all Laundry and LaundryReturns
    laundry_entries = db.query(models.Laundry).all()
    laundry_returns = db.query(models.LaundryReturn).all()
    
    # Structure: { dni: { "user": UserObject, "items": { "ItemName": { "sent": 0, "returned": 0 } } } }
    user_data = {}

    # Process Sent Items
    for entry in laundry_entries:
        if entry.dni not in user_data:
            user = db.query(models.User).filter(models.User.dni == entry.dni).first()
            if not user: continue
            user_data[entry.dni] = {"user": user, "items": {}}
            
        items = json.loads(entry.items_json)
        for item in items:
            name = item['name']
            qty = item['qty']
            if name not in user_data[entry.dni]["items"]:
                user_data[entry.dni]["items"][name] = {"sent": 0, "returned": 0}
            user_data[entry.dni]["items"][name]["sent"] += qty

    # Process Returned Items
    for entry in laundry_returns:
        if entry.dni in user_data: # only care if user has sent something
             items = json.loads(entry.items_json)
             for item in items:
                name = item['name']
                qty = item['qty']
                if name in user_data[entry.dni]["items"]:
                     user_data[entry.dni]["items"][name]["returned"] += qty

    # Build Result List
    result_list = []
    for dni, data in user_data.items():
        pending_items = []
        for name, counts in data["items"].items():
            pending_qty = counts["sent"] - counts["returned"]
            if pending_qty > 0:
                pending_items.append({"name": name, "qty": pending_qty})
        
        if pending_items:
            result_list.append({
                "dni": dni,
                "user_name": data["user"].name,
                "user_surname": data["user"].surname,
                "pending_items": pending_items
            })
            
    return result_list

@app.get("/api/laundry/{dni}/status")
def get_laundry_status(dni: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.dni == dni).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all items sent to laundry
    laundry_entries = db.query(models.Laundry).filter(models.Laundry.dni == dni).all()
    
    # Get all items returned from laundry
    laundry_returns = db.query(models.LaundryReturn).filter(models.LaundryReturn.dni == dni).all()
    
    item_totals = {}

    # Sum sent items
    for entry in laundry_entries:
        items = json.loads(entry.items_json)
        for item in items:
            name = item['name']
            qty = item['qty']
            if name not in item_totals:
                item_totals[name] = {"sent": 0, "returned": 0}
            item_totals[name]["sent"] += qty
            
    # Sum returned items
    for entry in laundry_returns:
        items = json.loads(entry.items_json)
        for item in items:
            name = item['name']
            qty = item['qty']
            if name not in item_totals:
                item_totals[name] = {"sent": 0, "returned": 0}
            item_totals[name]["returned"] += qty
            
    # Calculate pending
    status_list = []
    for name, counts in item_totals.items():
        pending = counts["sent"] - counts["returned"]
        status_list.append({
            "name": name,
            "sent": counts["sent"],
            "returned": counts["returned"],
            "pending": pending
        })
        
    return status_list

@app.post("/api/laundry/return", response_model=schemas.LaundryReturn)
def create_laundry_return(return_data: schemas.LaundryReturnCreate, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(models.User).filter(models.User.dni == return_data.dni).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    items_list = [item.dict() for item in return_data.items]
    
    new_return = models.LaundryReturn(
        dni=return_data.dni,
        date=datetime.now(),
        items_json=json.dumps(items_list)
    )
    
    db.add(new_return)
    db.commit()
    db.refresh(new_return)
    
    return new_return

@app.get("/api/laundry/report")
def get_laundry_report(
    dni: str = None, 
    month: int = None, 
    year: int = None, 
    db: Session = Depends(get_db)
):
    # Fetch ALL history to perform consistent FIFO matching
    # If we filtered DB query by date, we might miss the Send for a current Return, or vice versa.
    # Optimization: If DNI is provided, only fetch for that DNI.
    laundry_query = db.query(models.Laundry)
    return_query = db.query(models.LaundryReturn)

    if dni:
        laundry_query = laundry_query.filter(models.Laundry.dni.contains(dni))
        return_query = return_query.filter(models.LaundryReturn.dni.contains(dni))

    # Sort sends by date to ensure FIFO baseline
    laundry_records = laundry_query.order_by(models.Laundry.date).all()
    # Sort returns by date
    return_records = return_query.order_by(models.LaundryReturn.date).all()
    
    # ---------------------------------------------------------
    # FIFO Matching Logic
    # ---------------------------------------------------------
    # Structure: { dni: { 'ItemName': [ { 'record': laundry_obj, 'qty': 2, 'returned': 0, 'return_dates': [] } ] } }
    
    user_inventory = {}

    # 1. Populate Inventory with Sends
    processed_sends = [] 

    for rec in laundry_records:
        if rec.dni not in user_inventory:
            user_inventory[rec.dni] = {}
        
        items = json.loads(rec.items_json)
        for item in items:
            name = item['name']
            qty = item['qty']
            if qty <= 0: continue
            
            if name not in user_inventory[rec.dni]:
                user_inventory[rec.dni][name] = []
            
            # Create a tracker object
            tracker = {
                'id': rec.id,
                'dni': rec.dni,
                'name': name,
                'qty': qty,
                'returned': 0,
                'return_dates': [],
                'send_date': rec.date,
                'fully_returned': False
            }
            user_inventory[rec.dni][name].append(tracker)
            processed_sends.append(tracker)

    # 2. Process Returns against Inventory
    for ret in return_records:
        if ret.dni not in user_inventory:
            continue # Returned something but never sent? (Or DB consistency issue), ignore
            
        ret_items = json.loads(ret.items_json)
        for r_item in ret_items:
            r_name = r_item['name']
            r_qty = r_item['qty']
            if r_qty <= 0: continue
            
            # Find sends to deduct from (FIFO)
            if r_name in user_inventory[ret.dni]:
                # Iterate through the user's sent batches for this item
                for tracker in user_inventory[ret.dni][r_name]:
                    if tracker['fully_returned']:
                        continue
                    
                    needed = r_qty
                    available = tracker['qty'] - tracker['returned']
                    
                    if available > 0:
                        take = min(needed, available)
                        tracker['returned'] += take
                        tracker['return_dates'].append(ret.date)
                        r_qty -= take
                        
                        if tracker['returned'] >= tracker['qty']:
                            tracker['fully_returned'] = True
                            
                        if r_qty <= 0:
                            break # Fulfilled this return item

    # 3. Build Filtered Report (Grouped by Request)
    report_data = []
    
    # helper to group trackers by request id
    requests_map = {} # { id: { 'record': rec, 'trackers': [] } }
    
    for tracker in processed_sends:
        rid = tracker['id']
        if rid not in requests_map:
            # Re-fetch or store record reference would be better, but we have fields in tracker
            requests_map[rid] = {
                'dni': tracker['dni'],
                'send_date': tracker['send_date'],
                'trackers': []
            }
        requests_map[rid]['trackers'].append(tracker)

    # Now iterate requests
    for rid, data in requests_map.items():
        # Apply Filters (on Send Date)
        if year and data['send_date'].year != year: continue
        if month and data['send_date'].month != month: continue

        user = db.query(models.User).filter(models.User.dni == data['dni']).first()
        user_name = f"{user.name} {user.surname}" if user else "Desconocido"

        # Aggregate items text and status
        items_summary = []
        all_return_dates = []
        total_qty = 0
        total_returned = 0
        
        for t in data['trackers']:
            items_summary.append(f"{t['qty']} {t['name']}")
            total_qty += t['qty']
            total_returned += t['returned']
            if t['return_dates']:
                all_return_dates.extend(t['return_dates'])
        
        items_str = ", ".join(items_summary)
        
        # Determine Status and Date
        status = "Pendiente"
        return_date_str = "-"
        
        if total_returned >= total_qty:
            status = "Entregado"
            # User wants date of the LAST item returned
            if all_return_dates:
                last_date = max(all_return_dates)
                return_date_str = last_date.isoformat()
        elif total_returned > 0:
            status = "Parcial"
            if all_return_dates:
                 last_date = max(all_return_dates)
                 return_date_str = f"Parcial ({last_date.strftime('%d/%m')})"
        
        report_data.append({
            "id": f"REQ-{rid}", # Unique ID for table row
            "user": user_name,
            "dni": data['dni'],
            "items": items_str,
            "request_date": data['send_date'].isoformat(),
            "return_date": return_date_str,
            "status": status,
            "sort_date": data['send_date']
        })

    # Sort final list
    report_data.sort(key=lambda x: x['sort_date'], reverse=True)

    return report_data

@app.get("/api/delivery/report")
def get_delivery_report(
    dni: str = None, 
    month: int = None, 
    year: int = None, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Delivery)

    if dni:
        query = query.filter(models.Delivery.dni.contains(dni))
    
    records = query.all()
    report_data = []

    for rec in records:
        if year and rec.date.year != year: continue
        if month and rec.date.month != month: continue

        user = db.query(models.User).filter(models.User.dni == rec.dni).first()
        if not user: continue # Should not happen ideally but good safeguard

        items = json.loads(rec.items_json)
        # Filter items with qty > 0 if needed, usually all are valid in delivery
        items_str = ", ".join([f"{i['qty']} {i['name']}" for i in items])

        report_data.append({
            "id": rec.id,
            "user": f"{user.name} {user.surname}",
            "dni": rec.dni,
            "contract_type": user.contract_type,
            "items": items_str,
            "date": rec.date.isoformat(),
            "sort_date": rec.date
        })

    report_data.sort(key=lambda x: x['sort_date'], reverse=True)
    return report_data
