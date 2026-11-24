from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.facturacion import (
    ConfiguracionNegocio,
    ContadorSerie,
    EstadoFactura,
    Factura,
    LineaFactura,
)


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
    def verificar(
        db: Session, numero_serie: str, codigo_verificacion: str
    ) -> Optional[Factura]:
        stmt = (
            select(Factura)
            .options(selectinload(Factura.lineas))
            .where(
                Factura.numero_serie == numero_serie,
                Factura.codigo_verificacion == codigo_verificacion,
            )
        )
        return db.scalars(stmt).first()

    @staticmethod
    def listar(
        db: Session,
        *,
        estado: Optional[EstadoFactura] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        cliente: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Factura]:
        stmt = select(Factura).options(selectinload(Factura.lineas))

        if estado is not None:
            stmt = stmt.where(Factura.estado == estado)
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
        # Regla del modelo: nunca se borra la factura y fecha_anulacion es obligatoria.
        factura.estado = EstadoFactura.ANULADA
        if factura.fecha_anulacion is None:
            factura.fecha_anulacion = datetime.now(timezone.utc)

        if commit:
            db.commit()
            db.refresh(factura)
        else:
            db.flush()
        return factura


class ContadorSerieRepository:
    @staticmethod
    def obtener_siguiente_numero(
        db: Session, anio: int, *, commit: bool = False
    ) -> int:
        stmt = (
            select(ContadorSerie)
            .where(ContadorSerie.anio == anio)
            .with_for_update()
        )
        contador = db.scalars(stmt).first()

        if contador is None:
            contador = ContadorSerie(anio=anio, ultimo_numero=1)
            db.add(contador)
        else:
            contador.ultimo_numero += 1

        if commit:
            db.commit()
            db.refresh(contador)
        else:
            db.flush()

        return contador.ultimo_numero


class ConfiguracionNegocioRepository:
    @staticmethod
    def obtener(db: Session) -> Optional[ConfiguracionNegocio]:
        stmt = select(ConfiguracionNegocio).order_by(ConfiguracionNegocio.id.asc())
        return db.scalars(stmt).first()

    @staticmethod
    def guardar_o_actualizar(
        db: Session, datos: dict, *, commit: bool = True
    ) -> ConfiguracionNegocio:
        config = ConfiguracionNegocioRepository.obtener(db)

        if config is None:
            config = ConfiguracionNegocio(**datos)
            db.add(config)
        else:
            for campo, valor in datos.items():
                setattr(config, campo, valor)

        if commit:
            db.commit()
            db.refresh(config)
        else:
            db.flush()
        return config
