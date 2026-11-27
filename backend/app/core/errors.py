from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

from app.repositories.catalogo import IntegridadError
from app.services.ciclo_vida import FacturaYaAnuladaError
CODIGOS = {
    401: "UNAUTHORIZED",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}


def respuesta_error(status_code, detail, code, headers=None):
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
        headers=headers,
    )


def manejar_http_error(request, exc: StarletteHTTPException):
    code = CODIGOS.get(exc.status_code, "ERROR")
    return respuesta_error(exc.status_code, str(exc.detail), code, exc.headers)
def manejar_conflicto(request, exc):
    return respuesta_error(409, str(exc), "CONFLICT")


def manejar_valor_invalido(request, exc):
    return respuesta_error(422, str(exc), "VALIDATION_ERROR")


def manejar_no_encontrado(request, exc):
    return respuesta_error(404, str(exc) or "No encontrado.", "NOT_FOUND")


def manejar_validacion(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Datos de entrada inválidos.",
            "code": "VALIDATION_ERROR",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


def registrar_manejadores(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, manejar_http_error)
    app.add_exception_handler(RequestValidationError, manejar_validacion)
    app.add_exception_handler(IntegridadError, manejar_conflicto)
    app.add_exception_handler(FacturaYaAnuladaError, manejar_conflicto)
    app.add_exception_handler(ValueError, manejar_valor_invalido)
    app.add_exception_handler(LookupError, manejar_no_encontrado)