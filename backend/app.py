# API para el muro de mensajes: listar y publicar, guardando en Firestore.
import os, uuid
from flask import Flask, request, jsonify
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client(database=os.environ.get("BASE_DATOS", "(default)"))
INSTANCIA = uuid.uuid4().hex[:6]


@app.after_request
def permitir_navegador(respuesta):
    respuesta.headers["Access-Control-Allow-Origin"] = os.environ.get("ORIGEN_PERMITIDO", "*")
    respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type"
    respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return respuesta


@app.get("/")
def salud():
    return "ok"


@app.get("/mensajes")
def listar():
    consulta = (db.collection("mensajes")
                  .order_by("creado", direction=firestore.Query.DESCENDING)
                  .limit(20))
    mensajes = []
    for documento in consulta.stream():
        datos = documento.to_dict()
        reacciones = datos.get("reacciones") or {}
        mensajes.append({
            "id": documento.id,
            "autor": datos.get("autor"),
            "texto": datos.get("texto"),
            "reacciones": {
                tipo: reacciones.get(tipo, 0)
                for tipo in ("me_gusta", "corazon", "risa")
            },
        })
    return jsonify(instancia=INSTANCIA, mensajes=mensajes)


@app.post("/mensajes")
def crear():
    datos = request.get_json(silent=True) or {}
    autor = str(datos.get("autor", "")).strip()[:40]
    texto = str(datos.get("texto", "")).strip()[:280]
    if not autor or not texto:
        return jsonify(error="faltan autor o texto"), 400
    db.collection("mensajes").add({
        "autor": autor,
        "texto": texto,
        "creado": firestore.SERVER_TIMESTAMP,
        "reacciones": {
            "me_gusta": 0,
            "corazon": 0,
            "risa": 0,
        },
    })
    return jsonify(ok=True, instancia=INSTANCIA), 201


@app.post("/mensajes/<mensaje_id>/reacciones")
def reaccionar(mensaje_id):
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="se requiere una reaccion"), 400

    reaccion = datos.get("reaccion")
    if not isinstance(reaccion, str) or reaccion not in {"me_gusta", "corazon", "risa"}:
        return jsonify(error="reaccion no valida"), 400

    referencia = db.collection("mensajes").document(mensaje_id)
    if not referencia.get().exists:
        return jsonify(error="mensaje no encontrado"), 404

    referencia.update({
        f"reacciones.{reaccion}": firestore.Increment(1),
    })
    return jsonify(ok=True, instancia=INSTANCIA), 200
