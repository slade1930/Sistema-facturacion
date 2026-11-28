from datetime import date
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.facturacion import (
    ConfiguracionNegocio,
    EstadoFactura,
    Factura,
    LineaFactura,
)
from app.schemas.facturacion import (
    ConfiguracionNegocioBase,
    ConfiguracionNegocioUpdate,
)
from app.services.ciclo_vida import anular_factura
from app.services.serie import siguiente_numero_factura
from app.services.verificacion import validar_codigo_verificacion


class FacturaRepository:
    @staticmethod
    def crear(
        db: Session,
        factura: Factura,
        lineas: Optional[list[LineaFactura]] = None,
        *,
        commit: bool = True,
    ) -> Factura:
        if lineas is not None:
            for idx, linea in enumerate(lineas, start=1):
                if linea.orden is None:
                    linea.orden = idx
            factura.lineas = lineas

        db.add(factura)
        if commit:
            db.commit()
            db.refresh(factura)
        else:
            db.flush()
        return factura

    @staticmethod
    def obtener_por_id(db: Session, factura_id: int) -> Optional[Factura]:
        stmt = (
            select(Factura)
            .options(selectinload(Factura.lineas))
            .where(Factura.id == factura_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def obtener_por_numero_serie(
        db: Session, numero_serie: str
    ) -> Optional[Factura]:
        stmt = (
            select(Factura)
            .options(selectinload(Factura.lineas))
            .where(Factura.numero_serie == numero_serie)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def existe_numero_serie(
        db: Session, numero_serie: str, excluir_id: Optional[int] = None
    ) -> bool:
        """¿Existe otra factura con esa serie? Sirve para marcar duplicados."""
        stmt = select(Factura.id).where(Factura.numero_serie == numero_serie)
        if excluir_id is not None:
            stmt = stmt.where(Factura.id != excluir_id)
        return db.scalars(stmt.limit(1)).first() is not None

    @staticmethod
    def verificar(
        db: Session, numero_serie: str, codigo_verificacion: str
    ) -> Optional[Factura]:
        factura = FacturaRepository.obtener_por_numero_serie(db, numero_serie)
        if factura is None:
            return None

        es_valido = validar_codigo_verificacion(
            codigo_verificacion,
            factura.numero_serie,
            factura.total,
            factura.cliente_ruc or "",
        )
        if not es_valido:
            return None

        return factura

    @staticmethod
    def listar(
        db: Session,
        *,
        estado: Optional[EstadoFactura] = None,
        en_revision: Optional[bool] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        cliente: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        cliente_id: Optional[int] = None,
    ) -> list[Factura]:
        stmt = select(Factura).options(selectinload(Factura.lineas))
        if cliente_id is not None:
            stmt = stmt.where(Factura.cliente_id == cliente_id)

        if estado is not None:
            stmt = stmt.where(Factura.estado == estado)
        if en_revision is not None:
            stmt = stmt.where(Factura.en_revision == en_revision)
        if fecha_desde is not None:
            stmt = stmt.where(Factura.fecha >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(Factura.fecha <= fecha_hasta)
        if cliente:
            stmt = stmt.where(Factura.cliente_nombre.ilike(f"%{cliente.strip()}%"))

        stmt = (
            stmt.order_by(Factura.fecha_creacion.desc(), Factura.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def anular(
        db: Session, factura: Factura, *, commit: bool = True
    ) -> Factura:
        # Delega en ciclo_vida.anular_factura (lanza FacturaYaAnuladaError si ya está anulada).
        anular_factura(factura)

        if commit:
            db.commit()
            db.refresh(factura)
        else:
            db.flush()
        return factura


class ContadorSerieRepository:
    @staticmethod
    def obtener_siguiente_numero(db: Session, anio: int) -> str:
        # Delega en app.services.serie (usa upsert atómico + FOR UPDATE y flush).
        return siguiente_numero_factura(db, anio)


class ConfiguracionNegocioRepository:
    @staticmethod
    def obtener(db: Session) -> Optional[ConfiguracionNegocio]:
        stmt = select(ConfiguracionNegocio).order_by(ConfiguracionNegocio.id.asc())
        return db.scalars(stmt).first()

    @staticmethod
    def guardar_o_actualizar(
        db: Session,
        datos: Union[ConfiguracionNegocioUpdate, ConfiguracionNegocioBase],
        *,
        commit: bool = True,
    ) -> ConfiguracionNegocio:
        payload = datos.model_dump(exclude_unset=True)
        config = ConfiguracionNegocioRepository.obtener(db)

        if config is None:
            if not payload.get("empresa_nombre") or not payload.get("empresa_ruc"):
                raise ValueError(
                    "Para crear la configuración inicial se requieren "
                    "empresa_nombre y empresa_ruc."
                )
            config = ConfiguracionNegocio(**payload)
            db.add(config)
        else:
            for campo, valor in payload.items():
                setattr(config, campo, valor)

        if commit:
            db.commit()
            db.refresh(config)
        else:
            db.flush()
        return config
