# Reverse Economics v1

El método se ejecuta por candidato y escenario. Nunca completa una variable
material con un valor implícito. Cada input se etiqueta DATA, ESTIMATE o
ASSUMPTION con fuente, fecha, freshness, verificación y rango cuando aplique.

## Variables mensuales

- `P`: precio realizado por unidad, después de descuentos.
- `LC`: landed cost por unidad (producto, transporte, aranceles y recepción).
- `MF`: fees variables de marketplace/pago por unidad.
- `FF`: fulfillment y logística variables por unidad.
- `RR`: devoluciones, reembolsos y merma esperados por unidad; solo con DATA o
  escenario explícito.
- `AD`: publicidad variable por unidad; solo cuando sea aplicable y sustentada.
- `OV`: otros costes variables por unidad.
- `FC`: costes fijos mensuales aplicables.
- `C = P - LC - MF - FF - RR - AD - OV`: contribución por unidad.

Si falta cualquiera de `P`, `LC`, `MF` o `FF`, o una variable material aplicable,
`C` queda `NO_DATA` y no se publican unidades necesarias.

## Cálculo hacia atrás

Para un objetivo de utilidad neta mensual `T`:

- unidades requeridas: `ceil((T + FC) / C)`, únicamente si `C > 0`;
- ventas brutas requeridas: `unidades × P`;
- break-even operativo: `ceil(FC / C)`, si `FC > 0`, o primera unidad con
  contribución positiva si `FC = 0`;
- sensibilidad: recalcular con escenarios documentados de menor precio, mayor
  landed cost, mayores fees/devoluciones/publicidad y menor sell-through.

Los escenarios obligatorios son break-even, USD 1,000, USD 3,000 y USD 5,000
netos al mes. USD 5,000 es un escenario de escalabilidad, no una promesa.

## Capital de trabajo y operación

Por escenario se documentan, sin deducirlos de forma implícita:

1. unidades/mes y unidades/día;
2. lead time y ciclo de reposición;
3. inventario de ciclo y safety stock, si hay base para calcularlos;
4. MOQ y desembolso de reposición;
5. efectivo atrapado durante compra, tránsito, recepción, venta y payout;
6. capital de trabajo pico aproximado y si excede USD 750;
7. almacenamiento, preparación, soporte, devoluciones y horas humanas;
8. demanda comercial que tendría que observarse para sostener el volumen.

Una aproximación de capital de trabajo solo puede publicarse si declara fórmula,
periodo y variables. No se confunde flujo de caja con utilidad.

## Salida mínima

Cada resultado incluye inputs clasificados, fórmula, resultado, rango de
sensibilidad, missing data, conflictos y fecha. Cuando hay datos insuficientes,
la salida correcta es `NOT CALCULABLE — material input missing`, seguida del
`ResearchNeed`; jamás cero, una media arbitraria o un número “conservador” sin
procedencia.
