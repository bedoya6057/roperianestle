from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, schemas
from datetime import date, datetime
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

# Configuración de directorios para PDFs
PDF_DIR = "deliveries_pdf"
os.makedirs(PDF_DIR, exist_ok=True)

# Inicialización de Base de Datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DEL FRONTEND ---
# 1. Montar archivos estáticos (JS, CSS, Imágenes)
# Esto permite que el navegador encuentre los recursos dentro de la carpeta /frontend
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# 2. Ruta raíz para cargar el index.html automáticamente
@app.get("/")
async def read_index():
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Si no existe index.html, redirige a la documentación para evitar el error "Not Found"
    return RedirectResponse(url="/docs")

# --- DEPENDENCIAS ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- RUTAS DE LA API ---

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
    # Nota: He mantenido tu lógica de logo, pero recuerda que en Render 
    # la ruta debe ser relativa al servidor, ej: "frontend/logo.png"
    logo_path = "frontend/logo.png" 
    
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            iw, ih = logo.getSize()
            aspect = ih / float(iw)
            draw_width = 120
            draw_height = draw_width * aspect
            c.drawImage(logo, 40, height - 50 - draw_height, width=draw_width, height=draw_height, mask='auto', preserveAspectRatio=True)
        except Exception as e:
            c.drawString(40, height - 100, "SODEXO")
        
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 120, "ACTA DE ENTREGA DE UNIFORMES Y EPP")
    
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 60, f"Acta N°: {delivery_id:06d}")
    c.drawRightString(width - 50, height - 75, f"Fecha: {delivery_date.strftime('%Y-%m-%d')}")
    
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

    y_table = y_info - 100
    data = [["Item / Descripción", "Cantidad"]]
    for item in items:
        data.append([item['name'], str(item['qty'])])

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
    
    w, h = table.wrap(width, height)
    table.drawOn(c, 80, y_table - h)
    
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
        
        pdf_path = generate_pdf(new_delivery.id, user, items_list, delivery.date)
        new_delivery.pdf_path = pdf_path
        db.commit()
        
        return {"message": "Delivery created", "delivery_id": new_delivery.id, "items": items_list, "pdf_url": f"/api/deliveries/{new_delivery.id}/pdf"}
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            f.write(traceback.format_exc())
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
    laundry_entries = db.query(models.Laundry).all()
    laundry_returns = db.query(models.LaundryReturn).all()
    
    user_items = {} 
    
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

    active_laundry_users = sum(1 for items in user_items.values() if any(qty > 0 for qty in items.values()))
    laundry_total_count = db.query(models.Laundry).count()

    return {
        "users_count": users_count,
        "deliveries_count": deliveries_count,
        "laundry_total_count": laundry_total_count,
        "laundry_active_count": active_laundry_users
    }

@app.get("/api/laundry", response_model=list[schemas.LaundryPendingUser])
def get_laundry(db: Session = Depends(get_db)):
    laundry_entries = db.query(models.Laundry).all()
    laundry_returns = db.query(models.LaundryReturn).all()
    
    user_data = {}

    for entry in laundry_entries:
        if entry.dni not in user_data:
            user = db.query(models.User).filter(models.User.dni == entry.dni).first()
            if not user: continue
            user_data[entry.dni] = {"user": user, "items": {}}
        items = json.loads(entry.items_json)
        for item in items:
            name = item['name']
            if name not in user_data[entry.dni]["items"]:
                user_data[entry.dni]["items"][name] = {"sent": 0, "returned": 0}
            user_data[entry.dni]["items"][name]["sent"] += item['qty']

    for entry in laundry_returns:
        if entry.dni in user_data:
             items = json.loads(entry.items_json)
             for item in items:
                name = item['name']
                if name in user_data[entry.dni]["items"]:
                     user_data[entry.dni]["items"][name]["returned"] += item['qty']

    result_list = []
    for dni, data in user_data.items():
        pending_items = [{"name": n, "qty": c["sent"] - c["returned"]} for n, c in data["items"].items() if (c["sent"] - c["returned"]) > 0]
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
    if not user: raise HTTPException(status_code=404, detail="User not found")
    laundry_entries = db.query(models.Laundry).filter(models.Laundry.dni == dni).all()
    laundry_returns = db.query(models.LaundryReturn).filter(models.LaundryReturn.dni == dni).all()
    item_totals = {}
    for entry in laundry_entries:
        for item in json.loads(entry.items_json):
            name = item['name']
            if name not in item_totals: item_totals[name] = {"sent": 0, "returned": 0}
            item_totals[name]["sent"] += item['qty']
    for entry in laundry_returns:
        for item in json.loads(entry.items_json):
            name = item['name']
            if name not in item_totals: item_totals[name] = {"sent": 0, "returned": 0}
            item_totals[name]["returned"] += item['qty']
    return [{"name": n, "sent": c["sent"], "returned": c["returned"], "pending": c["sent"] - c["returned"]} for n, c in item_totals.items()]

@app.post("/api/laundry/return", response_model=schemas.LaundryReturn)
def create_laundry_return(return_data: schemas.LaundryReturnCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.dni == return_data.dni).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    items_list = [item.dict() for item in return_data.items]
    new_return = models.LaundryReturn(dni=return_data.dni, date=datetime.now(), items_json=json.dumps(items_list))
    db.add(new_return)
    db.commit()
    db.refresh(new_return)
    return new_return

@app.get("/api/laundry/report")
def get_laundry_report(dni: str = None, month: int = None, year: int = None, db: Session = Depends(get_db)):
    laundry_query = db.query(models.Laundry)
    return_query = db.query(models.LaundryReturn)
    if dni:
        laundry_query = laundry_query.filter(models.Laundry.dni.contains(dni))
        return_query = return_query.filter(models.LaundryReturn.dni.contains(dni))
    laundry_records = laundry_query.order_by(models.Laundry.date).all()
    return_records = return_query.order_by(models.LaundryReturn.date).all()
    
    user_inventory = {}
    processed_sends = [] 

    for rec in laundry_records:
        if rec.dni not in user_inventory: user_inventory[rec.dni] = {}
        for item in json.loads(rec.items_json):
            name = item['name']
            if item['qty'] <= 0: continue
            if name not in user_inventory[rec.dni]: user_inventory[rec.dni][name] = []
            tracker = {'id': rec.id, 'dni': rec.dni, 'name': name, 'qty': item['qty'], 'returned': 0, 'return_dates': [], 'send_date': rec.date, 'fully_returned': False}
            user_inventory[rec.dni][name].append(tracker)
            processed_sends.append(tracker)

    for ret in return_records:
        if ret.dni not in user_inventory: continue
        for r_item in json.loads(ret.items_json):
            r_name, r_qty = r_item['name'], r_item['qty']
            if r_name in user_inventory[ret.dni]:
                for tracker in user_inventory[ret.dni][r_name]:
                    if tracker['fully_returned']: continue
                    available = tracker['qty'] - tracker['returned']
                    if available > 0:
                        take = min(r_qty, available)
                        tracker['returned'] += take
                        tracker['return_dates'].append(ret.date)
                        r_qty -= take
                        if tracker['returned'] >= tracker['qty']: tracker['fully_returned'] = True
                        if r_qty <= 0: break

    report_data = []
    requests_map = {} 
    for tracker in processed_sends:
        rid = tracker['id']
        if rid not in requests_map: requests_map[rid] = {'dni': tracker['dni'], 'send_date': tracker['send_date'], 'trackers': []}
        requests_map[rid]['trackers'].append(tracker)

    for rid, data in requests_map.items():
        if year and data['send_date'].year != year: continue
        if month and data['send_date'].month != month: continue
        user = db.query(models.User).filter(models.User.dni == data['dni']).first()
        user_name = f"{user.name} {user.surname}" if user else "Desconocido"
        
        all_return_dates = []
        total_qty = total_returned = 0
        items_summary = []
        for t in data['trackers']:
            items_summary.append(f"{t['qty']} {t['name']}")
            total_qty += t['qty']
            total_returned += t['returned']
            all_return_dates.extend(t['return_dates'])
        
        status = "Pendiente"
        return_date_str = "-"
        if total_returned >= total_qty:
            status = "Entregado"
            if all_return_dates: return_date_str = max(all_return_dates).isoformat()
        elif total_returned > 0:
            status = "Parcial"
            if all_return_dates: return_date_str = f"Parcial ({max(all_return_dates).strftime('%d/%m')})"
        
        report_data.append({"id": f"REQ-{rid}", "user": user_name, "dni": data['dni'], "items": ", ".join(items_summary), "request_date": data['send_date'].isoformat(), "return_date": return_date_str, "status": status, "sort_date": data['send_date']})

    report_data.sort(key=lambda x: x['sort_date'], reverse=True)
    return report_data

@app.get("/api/delivery/report")
def get_delivery_report(dni: str = None, month: int = None, year: int = None, db: Session = Depends(get_db)):
    query = db.query(models.Delivery)
    if dni: query = query.filter(models.Delivery.dni.contains(dni))
    records = query.all()
    report_data = []
    for rec in records:
        if year and rec.date.year != year: continue
        if month and rec.date.month != month: continue
        user = db.query(models.User).filter(models.User.dni == rec.dni).first()
        if not user: continue
        items_str = ", ".join([f"{i['qty']} {i['name']}" for i in json.loads(rec.items_json)])
        report_data.append({"id": rec.id, "user": f"{user.name} {user.surname}", "dni": rec.dni, "contract_type": user.contract_type, "items": items_str, "date": rec.date.isoformat(), "sort_date": rec.date})
    report_data.sort(key=lambda x: x['sort_date'], reverse=True)
    return report_data