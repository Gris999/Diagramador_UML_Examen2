# Diseño de la interfaz del diagramador

Decisión del 2026-11-07: la interfaz tenía **tres colores de acento compitiendo** (pizarra oscura, cian/verde azulado y morado), **emojis como íconos** (📦 🤖 📱 ❓) y las mismas 10 a 15 clases de Tailwind repetidas en cada botón de las plantillas. Se unificó con un sistema pequeño y sin cambiar ninguna lógica.

## Reglas

| Tema | Regla |
|---|---|
| Color | Una sola paleta: **morado de marca** (`purple-600`/`700`) para la acción principal y los acentos, **grises neutros** (`slate`) para superficies y texto. El **rojo** solo para acciones destructivas o errores; el **verde**, solo para "correcto". |
| Íconos | **SVG en línea** con `stroke="currentColor"`, nunca emojis. Así cambian de color con el texto y se ven igual en todos los sistemas. |
| Botones | Una acción principal por bloque (`btn btn-primary`); lo demás, `btn btn-secondary`. Las secciones plegables del panel lateral son encabezados discretos (`section-toggle`), no botones grandes. |
| Accesibilidad | Foco visible morado en todo (`:focus-visible`), `aria-label` en los botones que solo tienen ícono, `aria-labelledby` en las tarjetas de la portada. |
| Textos y pruebas | Las pruebas dependen de textos y de `data-testid`, no de colores ni de clases: se pueden cambiar estilos sin tocarlas. |

## Componentes compartidos (`front_generador_bd/src/styles.css`)

Se definen una sola vez con `@apply` de Tailwind y las plantillas solo los nombran:

- `btn` + `btn-primary` / `btn-secondary` / `btn-ghost` / `btn-danger` / `btn-danger-soft`, con `btn-sm` y `btn-block`.
- `icon-btn` (botón cuadrado con ícono, para grupos como el zoom).
- `card` (superficie blanca con borde y sombra suave), `panel-title`.
- `field` (campos de texto y áreas de texto).
- `section-toggle` (encabezado plegable), `palette-tile` (ficha de la paleta de elementos), `badge` y `badge-brand`.

Para agregar un botón nuevo: `class="btn btn-secondary btn-sm"` más un ícono SVG; no hace falta escribir colores ni sombras.

## Qué cambió

- **Portada:** marca (ícono de dos clases UML), "Diagramador UML", tres etiquetas con lo que ofrece, tarjetas con ícono en círculo, fondo con degradado suave.
- **Barra del editor:** zoom como un grupo de tres botones, "Importar/Exportar XMI" y "Ayuda" como botones secundarios con ícono, fondo blanco con borde.
- **Panel lateral:** cabecera con la marca, secciones plegables discretas, fichas de la paleta alineadas, exportaciones como lista de botones iguales y **una** acción principal («Descargar proyecto completo»).
- **Paneles** de actividad, participantes, chat de la IA y ayuda: mismas tarjetas, mismos botones, ícono de IA en lugar del emoji.
- **Vista móvil de seguimiento:** misma paleta (cabecera morada) e íconos de campana en lugar de emojis.
- Título de la pestaña: «Diagramador UML» (antes «FrontGeneradorBd»), idioma `es`.

## Lo que no se tocó

- Las formas del lienzo (clases y relaciones de JointJS): llevan la lógica de selección y de exportación a imagen. Su azul de selección sigue siendo el de siempre.
- Ningún texto, ningún `data-testid` y ninguna lógica de los componentes. Las 312 pruebas de Angular y `ng build` pasan.
