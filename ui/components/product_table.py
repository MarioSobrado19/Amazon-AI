"""Tabla reutilizable de productos importados."""

from ui.view_models import preparar_filas


def mostrar_productos(st, productos):
    st.dataframe(
        preparar_filas(productos),
        width="stretch",
        hide_index=True,
    )
