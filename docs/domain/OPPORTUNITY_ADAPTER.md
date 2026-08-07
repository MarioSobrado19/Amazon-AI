# Adaptación del Opportunity Engine al dominio

**Fase:** Domain Adoption 1

## Responsabilidad

El adaptador convierte el diccionario actual en `Product`, `Opportunity` y
`Result`, y puede reconstruir el mismo formato heredado. No contiene pesos,
referencias ni fórmulas; tampoco recalcula ROI, margen, ganancia o Opportunity
Score.

## Identidad

Cuando la entrada ya contiene `product_id` u `opportunity_id`, el adaptador los
respeta. En caso contrario genera UUID versión 5 dentro del namespace URL:

- `Product ID`: nombre normalizado con espacios exteriores eliminados y sin
  distinguir mayúsculas.
- `Opportunity ID`: Product ID, Marketplace opcional, Proveedor opcional y el
  contexto comercial estable formado por compra, venta, envío, tarifa y otros
  costos.

Los valores derivados —costo total, ganancia, margen, ROI, clasificación,
Opportunity Score y su desglose— no forman parte de la identidad. Por eso
enriquecer la misma oportunidad no cambia su ID.

Si la entrada reducida no tiene contexto comercial, el adaptador utiliza ROI,
margen, ganancia y clasificación como respaldo temporal. Esta excepción existe
para conservar compatibilidad con el contrato unitario heredado y deberá
retirarse cuando todas las entradas incluyan contexto comercial completo.

UUID5 hace reproducible una identidad para la misma entrada canónica. Diferentes
marketplaces, proveedores, precios de compra o precios de venta producen IDs de
Opportunity distintos. El namespace y el prefijo separan IDs de Product e IDs de
Opportunity, evitando colisiones accidentales entre tipos.

## Metadatos de Result

Cada `Result` conserva:

- Valor original sin recalcular.
- `EvidenceType.ESTIMATE`.
- Fuente del motor.
- Fecha de evaluación con zona horaria.
- `ConfidenceLevel.MEDIUM`.
- Versión del motor.

El formato heredado no admite estos metadatos. Por compatibilidad no se agregan
campos nuevos al diccionario que reciben Dashboard, Insights, Decision Engine y
UI. Los metadatos permanecen en la entidad mientras se utiliza el dominio.

## Flujo

```text
Diccionario actual
    ↓
Adaptador de entrada
    ↓
Product + Opportunity + Result
    ↓
Opportunity Engine existente
    ↓
Adaptador de compatibilidad
    ↓
Diccionario actual sin cambios
```

