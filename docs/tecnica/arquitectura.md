# Arquitectura del Sistema

El proyecto utiliza una arquitectura por capas, donde cada capa se comunica con la siguiente para mantener el código organizado.

## Capas del Sistema
1. **Pantalla (planeada, NiceGUI):** formularios y vistas para el usuario (`ui/`, hoy vacío). Por ahora se usa Swagger UI.
2. **API (FastAPI):** Recibe las peticiones HTTP. (`backend/app/api/`)
3. **Esquemas (Pydantic):** Valida los datos de entrada y salida. (`backend/app/schemas/`)
4. **Servicios:** Lógica de negocio (cálculos de ITBMS, numeración). (`backend/app/services/`)
5. **Repositorios:** Consultas y guardado en la base de datos. (`backend/app/repositories/`)
6. **Modelos (SQLAlchemy):** Representación de las tablas. (`backend/app/models/`)
7. **Base de Datos (PostgreSQL):** Almacenamiento físico.

## ¿Cómo viaja una factura?
1. Por ahora el usuario carga los datos desde Swagger UI (la pantalla NiceGUI está planeada).
2. Se envía la petición al **Endpoint** de la API.
3. El Endpoint valida los datos con los **Esquemas**.
4. El Endpoint llama al **Servicio** para calcular el ITBMS y generar el número FAC-AAAA-0001.
5. El Servicio usa el **Repositorio** para guardar.
6. El Repositorio usa el **Modelo** para insertar en **PostgreSQL**.

