-- Base de pruebas del portal: una cuenta de administrador y una de empresa.
-- Las contraseñas NO están en el repositorio: acá solo se versionan los hashes.
-- Se puede cargar las veces que haga falta sin duplicar filas.
--
--   docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     < backend/tests/fixtures/usuarios_prueba.sql

BEGIN;

INSERT INTO public.cliente_b2b (id, nombre_empresa, ruc, email_contacto, telefono, direccion, fecha_registro, activo, sucursal, sector) VALUES
    ('127', 'Empresa Prueba Orquidea', 'RUC-PRUEBA-EMPRESA', 'prueba@ejemplo.local', '60000000', 'Avenida Prueba 1', '2026-11-28 06:00:33.864986+00', 't', 'Central', 'tecnologia')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.cuenta (id, nombre_usuario, password_hash, rol, cliente_id, activo, debe_cambiar_clave, creada_en, ultimo_acceso) VALUES
    ('88', 'admin_prueba', 'pbkdf2_sha256$600000$07oPT7R44gbylpNAvs9nuA==$G1+9/AC4aliE54r7p0FsPfKdrSSzshuFawgdTwDWFX0=', 'admin', NULL, 't', 'f', '2026-11-28 06:00:23.575246+00', '2026-11-28 06:58:17.953575+00'),
    ('89', 'empresa prueba orquidea', 'pbkdf2_sha256$600000$6sBbO/Qbuc9VAa6JdQZT7g==$LcV4hBryKSq8nexuAbDeW+HldPN6j4HE1IelVIlb2vA=', 'empresa', '127', 't', 'f', '2026-11-28 06:00:33.864986+00', '2026-11-28 06:58:18.074842+00')
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('public.cliente_b2b', 'id'),
    GREATEST(COALESCE((SELECT MAX(id) FROM public.cliente_b2b), 1), 127)
);
SELECT setval(
    pg_get_serial_sequence('public.cuenta', 'id'),
    GREATEST(COALESCE((SELECT MAX(id) FROM public.cuenta), 1), 89)
);

COMMIT;
