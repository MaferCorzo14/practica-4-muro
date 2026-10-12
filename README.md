# Muro de mensajes en Google Cloud

## 1. Identificación

**Equipo:** Maria Fernanda Corzo Castro.

**Otros integrantes:** completar si corresponde.

**Proyecto de Google Cloud:** `maquinavirtual-507221`.

**Región:** `us-central1`.
**URL del muro:** [https://corzocastro-frontend-26byw3byzq-uc.a.run.app](https://corzocastro-frontend-26byw3byzq-uc.a.run.app)

La URL se obtuvo con Terraform. Hay que comprobar que el servicio siga activo y que cargue el muro el día de la revisión. Para consultar la URL vigente:

```bash
terraform -chdir=infra output -raw url_frontend
```

## 2. Diagrama

```mermaid
flowchart LR
  navegador["Navegador<br/>teléfono o computadora"]
  frontend["Frontend<br/>Cloud Run"]
  backend["Backend / API<br/>Cloud Run"]
  firestore[("Firestore<br/>mensajes y votos")]
  ar[("Artifact Registry<br/>imágenes Docker")]
  sa_front["Cuenta frontend<br/>sin roles de datos"]
  sa_back["Cuenta backend<br/>roles/datastore.user"]
  terraform["Terraform"]

  navegador -->|"GET página"| frontend
  navegador -->|"GET/POST /mensajes y reacciones"| backend
  backend -->|"consulta y actualiza"| firestore

  terraform -. "var.imagen_frontend" .-> ar
  terraform -. "var.imagen_backend" .-> ar
  ar -->|"imagen frontend"| frontend
  ar -->|"imagen backend"| backend
  sa_front -. "template.service_account"| frontend
  sa_back -. "template.service_account"| backend
  sa_back -. "google_project_iam_member.backend_firestore"| firestore
  terraform -. "BACKEND_URL = backend.uri"| frontend
  terraform -. "BASE_DATOS = db.name"| backend
  terraform -. "ORIGEN_PERMITIDO = var.origen_frontend"| backend
  terraform -. "depends_on: APIs y Artifact Registry"| frontend
  terraform -. "depends_on: APIs y Artifact Registry"| backend
```

Terraform pasa la URI del backend al frontend mediante `google_cloud_run_v2_service.backend.uri`. El origen permitido del backend se configura con `var.origen_frontend`, cuyo valor es la URL del frontend. Es una cadena de entrada y no una referencia Terraform al recurso frontend; así se evita el ciclo frontend → backend → frontend. Las cuentas de servicio se conectan a sus servicios mediante `template.service_account`; solo la cuenta del backend recibe `roles/datastore.user`.

## 3. Las siete evidencias

Las capturas existentes están guardadas en `evidencias/`. La fase de preparación tiene tres capturas y las fases de cimientos, estado y reto agrupan más de una evidencia requerida.

### Fase 0. Preparación

- Versiones de Terraform: [terraform-version.png](./evidencias/preparacion/terraform-version.png)
- Versión de Docker: [docker-version.png](./evidencias/preparacion/docker-version.png)
- Configuración activa de `gcloud`: [config-list.png](./evidencias/preparacion/config-list.png)

### Fase 1. Las imágenes

- Caché de capas reutilizada al reconstruir: [capas-reutilizadas.png](./evidencias/imagenes/capas-reutilizadas.png)
- Prueba de frontend con el backend desconectado: [backend-desconectado.png](./evidencias/imagenes/backend-desconectado.png)

### Fase 2. Los cimientos

- Repositorio de imágenes en Artifact Registry: [artifact-registry.png](./evidencias/cimientos/artifact-registry.png)
- Base de Firestore: [firestore.png](./evidencias/cimientos/firestore.png)
- Identidad y permisos: [identidad.png](./evidencias/cimientos/identidad.png)

### Fase 3. El backend

- Publicación de un mensaje mediante la API: [post-mensaje.png](./evidencias/backend/post-mensaje.png)
- Respuesta de listado de mensajes: [mensaje.png](./evidencias/backend/mensaje.png)
- Documento persistido en Firestore: [documento.png](./evidencias/backend/documento.png)

### Fase 4. El frontend, conectado

- Muro publicado en Cloud Run: [muro.jpeg](./evidencias/frontend/muro.jpeg)

### Fase 5. El estado vive afuera

- Respuestas de distintas instancias durante las solicitudes: [instancias.jpeg](./evidencias/estado/instancias.jpeg)
- Resumen de carga de `hey`: [hey.png](./evidencias/estado/hey.png)
- Métrica de instancias del backend: [grafica-instancias.png](./evidencias/estado/grafica-instancias.png)

### Fase 6. Reto: hacerlo tuyo

- Reacciones en el muro: [funcionalidad-muro.jpeg](./evidencias/reto/funcionalidad-muro.jpeg)
- Error CORS al usar otro origen: [CORS-error.png](./evidencias/reto/CORS-error.png)
- Comparación de lecturas/refresco: [lectura.png](./evidencias/reto/lectura.png)
- Destrucción para la reconstrucción desde cero: [destroy.png](./evidencias/reto/destroy.png)
- Error encontrado durante la reconstrucción: [error500.png](./evidencias/reto/error500.png)
- API operativa después de corregir y reconstruir: [solucionado200.png](./evidencias/reto/solucionado200.png)

Antes de la revisión, confirmar que las capturas de `lectura.png` muestren la comparación anterior/después y que la URL pública siga funcionando. Una captura de `destroy.png` documenta la destrucción, pero la evidencia de reconstrucción completa debe mostrar también el `apply` exitoso y el servicio funcionando.

## 4. Comandos

Los comandos siguientes reúnen los usados durante la práctica. Ejecutarlos desde la raíz del repositorio en Cloud Shell, salvo que se indique otra ubicación. `B` y `RUTA` son variables de shell: hay que redefinirlas en cada pestaña nueva.

### Preparación y construcción local

```bash
terraform version
docker version
gcloud config list

docker build -t backend:local backend
docker build -t frontend:local frontend
docker run -d --rm --name front -p 8080:8080 frontend:local
docker stop front
```

### Registro e imágenes

```bash
RUTA=$(terraform -chdir=infra output -raw ruta_registro)
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

docker build -t "$RUTA/backend:v1" backend
docker build -t "$RUTA/frontend:v1" frontend
docker push "$RUTA/backend:v1"
docker push "$RUTA/frontend:v1"

gcloud artifacts docker images list "$RUTA" --include-tags
```

Cloud Build se usó cuando `docker push` falló por conexión rechazada. Las etiquetas finales configuradas para desplegar fueron `backend:v7` y `frontend:v6`:

```bash
gcloud builds submit --project=maquinavirtual-507221 \
  --tag "$RUTA/backend:v7" backend
gcloud builds submit --project=maquinavirtual-507221 \
  --tag "$RUTA/frontend:v6" frontend
```

### Terraform y prueba del backend

```bash
terraform -chdir=infra init
terraform -chdir=infra validate
terraform -chdir=infra apply

B=$(terraform -chdir=infra output -raw url_backend)
curl -s -X POST "$B/mensajes" \
  -H "Content-Type: application/json" \
  -d '{"autor":"Maria Fernanda Corzo Castro","texto":"Hola backend"}'
curl -s "$B/mensajes"

terraform -chdir=infra output -raw url_frontend
```

### Escalado

```bash
B=$(terraform -chdir=infra output -raw url_backend)
for i in $(seq 1 30); do
  curl -s "$B/mensajes" | cut -c1-30
  sleep 1
done

go run github.com/rakyll/hey@latest -z 30s -c 15 "$B/mensajes"
```

Durante esta prueba se registró el resumen de `hey` con 6.699 respuestas HTTP 200 y una tasa aproximada de 222,7 solicitudes por segundo. Cloud Run puede distribuir solicitudes entre varias instancias; no garantiza que cada prueba produzca el mismo número de instancias.

### Reto: CORS, reacciones y lecturas

```bash
gcloud run services logs read corzocastro-backend \
  --region us-central1 \
  --project maquinavirtual-507221 \
  --freshness=5m \
  --limit=40

curl -i -X POST "$B/mensajes/ID_DEL_MENSAJE/reacciones" \
  -H "Content-Type: application/json" \
  -d '{"reaccion":"corazon","visitante_id":"ID_HEXADECIMAL_DE_32_CARACTERES"}'
curl -s "$B/mensajes"

grep -n "setInterval(cargar" frontend/index.html
```

El refresco se cambió de `5000` a `60000` milisegundos. Con 100 pestañas abiertas durante 30 días completos, ignorando la carga inicial:

| Intervalo | Consultas HTTP al mes | Lecturas de documentos estimadas (20 mensajes por respuesta) |
|---|---:|---:|
| Antes: 5 segundos | 51.840.000 | hasta 1.036.800.000 |
| Después: 60 segundos | 4.320.000 | hasta 86.400.000 |

El cambio reduce en aproximadamente 91,7 % las consultas periódicas y las lecturas estimadas. Es una proyección: depende de que las 100 pestañas permanezcan abiertas todo el mes y de que cada consulta devuelva 20 documentos. La captura de Network observa solicitudes del navegador; las lecturas facturables deben contrastarse con las métricas de Firestore.

### Reconstrucción desde cero

`terraform destroy` elimina la base y sus datos, servicios, cuentas y repositorio. Las imágenes también se pierden al borrar Artifact Registry. Se guardaron las evidencias antes de destruir.

```bash
terraform -chdir=infra plan -destroy
terraform -chdir=infra destroy

# Crear el registro primero, ya que debe existir antes de publicar imágenes.
terraform -chdir=infra apply -target=google_artifact_registry_repository.imagenes
RUTA=$(terraform -chdir=infra output -raw ruta_registro)

# Publicar las imágenes en el repositorio recién creado.
gcloud builds submit --project=maquinavirtual-507221 \
  --tag "$RUTA/backend:v7" backend
gcloud builds submit --project=maquinavirtual-507221 \
  --tag "$RUTA/frontend:v6" frontend

# Crear los demás recursos cuando ambas imágenes existan.
terraform -chdir=infra apply

B=$(terraform -chdir=infra output -raw url_backend)
curl -i "$B/mensajes"
terraform -chdir=infra output -raw url_frontend
```

El repositorio se crea antes de subir imágenes; las imágenes se suben antes del `apply` completo, porque Cloud Run necesita que existan al desplegarse. `depends_on` en los dos servicios hace que Terraform cree el registro antes que los servicios y los destruya antes que el registro.

## 5. Las cuatro decisiones del reto

### 5.1 Funcionalidad nueva: reacciones

Cada mensaje admite `👍`, `❤️` y `😂`. El frontend envía el ID del mensaje, el tipo de reacción y un identificador aleatorio persistido en `localStorage` para ese navegador. Firestore guarda un documento de voto por visitante y mensaje; una transacción agrega, cambia o quita el voto y actualiza el contador correspondiente de forma consistente. Un mismo navegador puede tener una reacción por mensaje. No es autenticación: borrar el almacenamiento local o usar otro navegador genera otra identidad.

### 5.2 CORS restringido y eliminación del ciclo

El backend responde con `Access-Control-Allow-Origin` igual a `ORIGEN_PERMITIDO`, cuyo valor Terraform recibe en `var.origen_frontend`. El valor configurado es la URL del frontend de Cloud Run, no `*`. El frontend depende de `google_cloud_run_v2_service.backend.uri` para configurar `BACKEND_URL`; para CORS, el backend recibe una cadena de entrada con la URL del frontend, no una referencia al recurso frontend. Así se evita el ciclo de referencias. Al cambiar o recrear la URL del frontend hay que actualizar `origen_frontend` y volver a aplicar Terraform. CORS limita lectura desde navegadores; no autentica la API ni bloquea `curl`.

### 5.3 Menos lecturas

Se aumentó el intervalo de refresco de 5 a 60 segundos. Para una pestaña son 720 frente a 60 consultas periódicas por hora. Con 20 documentos en cada respuesta, son hasta 14.400 frente a 1.200 lecturas de documentos por hora. El muro tarda más en mostrar mensajes nuevos sin una recarga manual; esa es la concesión de experiencia a cambio de menos lecturas.

### 5.4 Reconstrucción reproducible

Los servicios de Cloud Run tienen `depends_on` sobre Artifact Registry. El proceso se hace en etapas porque Terraform crea el repositorio, pero no sube automáticamente las imágenes: primero se recrea el registro, después se construyen/publican las imágenes y, finalmente, se despliegan base, cuentas y servicios. La base tiene `deletion_policy = "DELETE"`, por lo que la destrucción también elimina Firestore y sus datos.

## 6. Tres preguntas

### ¿Por qué funciona la API con `curl` aunque falten cabeceras CORS, y desde la página no?

CORS es una política aplicada por los navegadores para impedir que una página de un origen lea respuestas de otro origen, salvo que el servidor lo autorice con cabeceras como `Access-Control-Allow-Origin`. `curl` no es un navegador y no implementa esa política: envía la petición y muestra la respuesta directamente. Por eso `curl` puede funcionar cuando el navegador bloquea el acceso de JavaScript a la respuesta. CORS no es un mecanismo de autenticación ni impide llamadas directas desde herramientas o programas.

### Si se quita el rol a la cuenta de servicio del backend, ¿qué deja de funcionar y dónde aparece el error?

El backend perderá acceso a Firestore: listar/publicar mensajes y registrar reacciones fallarán. El navegador puede mostrar un error interno del servidor, normalmente HTTP 500 si la aplicación no traduce la excepción; la causa aparece en los logs de Cloud Run como `PermissionDenied: 403 Missing or insufficient permissions`. Se revisa en **Cloud Run → servicio backend → Logs** o con:

```bash
gcloud run services logs read corzocastro-backend \
  --region us-central1 \
  --project maquinavirtual-507221 \
  --limit=40
```

El rol asignado por Terraform es `roles/datastore.user`, en `google_project_iam_member.backend_firestore`.

### ¿Cuánto cuesta un mes sin visitas y con 100 personas abiertas todo el día, antes y después del cambio?

Sin visitas, Cloud Run está configurado para escalar a cero y no procesa solicitudes; por tanto, no hay lecturas de Firestore provocadas por el muro ni consumo de cómputo de peticiones. Eso no garantiza una factura total de cero: imágenes guardadas en Artifact Registry, datos almacenados y otros recursos pueden generar cargos de almacenamiento. Para 100 pestañas abiertas 24/7 durante 30 días y 20 mensajes por lectura, el modelo estima 1.036.800.000 lecturas de documentos con refresco de 5 s frente a 86.400.000 con 60 s. Como referencia ilustrativa, a USD 0,03 por 100.000 lecturas regionales, eso equivale a unos USD 311,04 frente a USD 25,92 antes de aplicar cuotas gratuitas; si se aplica una cuota de 50.000 lecturas gratuitas por día durante 30 días, serían aproximadamente USD 310,59 y USD 25,47 solo por lecturas. No incluye Cloud Run, almacenamiento, red, ni variaciones de precio o cuotas compartidas. El precio y el costo real deben verificarse para la edición/región del proyecto en [precios de Firestore](https://cloud.google.com/firestore/pricing) y en **Facturación → Informes**.
