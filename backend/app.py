# API para el muro de mensajes: listar y publicar, guardando en Firestore.
import os, uuid
import re
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
        return jsonify(error="se requiere una reaccion y un id de navegador"), 400

    reaccion = datos.get("reaccion")
    if not isinstance(reaccion, str) or reaccion not in {"me_gusta", "corazon", "risa"}:
        return jsonify(error="reaccion no valida"), 400

    visitante_id = datos.get("visitante_id")
    if not isinstance(visitante_id, str) or not re.fullmatch(r"[0-9a-f]{32}", visitante_id):
        return jsonify(error="id de navegador no valido"), 400

    mensaje_ref = db.collection("mensajes").document(mensaje_id)
    voto_ref = mensaje_ref.collection("votos").document(visitante_id)
    transaction = db.transaction()

    @firestore.transactional
    def actualizar_voto(tx):
        mensaje = next(tx.get(mensaje_ref))
        voto = next(tx.get(voto_ref))
        if not mensaje.exists:
            return "no_encontrado"

        reaccion_anterior = voto.get("reaccion") if voto.exists else None
        cambios = {}
        if reaccion_anterior == reaccion:
            cambios[f"reacciones.{reaccion}"] = firestore.Increment(-1)
            tx.delete(voto_ref)
            accion = "quitada"
        else:
            if reaccion_anterior in {"me_gusta", "corazon", "risa"}:
                cambios[f"reacciones.{reaccion_anterior}"] = firestore.Increment(-1)
            cambios[f"reacciones.{reaccion}"] = firestore.Increment(1)
            tx.set(voto_ref, {"reaccion": reaccion})
            accion = "agregada" if reaccion_anterior is None else "cambiada"
        tx.update(mensaje_ref, cambios)
        return accion

    accion = actualizar_voto(transaction)
    if accion == "no_encontrado":
        return jsonify(error="mensaje no encontrado"), 404

    return jsonify(ok=True, accion=accion, instancia=INSTANCIA), 200
