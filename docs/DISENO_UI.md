# Diseño de la interfaz del diagramador

Dos decisiones, una sobre otra:

- **2026-11-07 (primera pasada):** la interfaz tenía **tres colores de acento compitiendo** (pizarra oscura, cian/verde azulado y morado), **emojis como íconos** y las mismas 10 a 15 clases de Tailwind repetidas en cada botón. Se unificó con un sistema pequeño y sin cambiar ninguna lógica.
- **2026-11-08 (segunda pasada, a pedido del equipo):** el panel de actividad y el de participantes ocupaban un lugar fijo y crecían sin límite con la sala; invitar a alguien era un botón perdido en el panel lateral; y el fondo blanco con morado se sentía plano. Se pasó a un **tema oscuro por defecto (con tema claro a elección)**, una **barra superior como la de draw.io** con un botón **Compartir**, y la actividad y los participantes como **desplegables**.

## Reglas

| Tema | Regla |
|---|---|
| Color | Los colores viven como **variables** (`--c-*`) en `styles.css` y cambian con el tema. Las plantillas **nunca nombran un color concreto**, nombran para qué sirve: `bg-panel`, `bg-raised`, `text-fg`, `text-fg-muted`, `border-line`, `bg-accent`, `text-accent-text`... Una sola marca (**azul**); **rojo** solo para peligro y errores, **verde** solo para «correcto». |
| Temas | **Oscuro por defecto**; claro con el botón del sol o la luna (barra superior del editor y portada). Se guarda en el navegador (`diagramador-tema`). Un script de `index.html` lo pone antes del primer dibujo para que no parpadee. `ThemeService` lo cambia (`data-theme` en `<html>`). |
| Lienzo | Fondo oscuro con las clases UML **claras**, como tarjetas. Las líneas, puntas y etiquetas de las relaciones se aclaran **solo con CSS** en el tema oscuro (`styles.css`); la imagen exportada se arma aparte con los colores originales sobre fondo claro, y el XMI no se toca. |
| Íconos | **SVG en línea** con `stroke="currentColor"`, nunca emojis. Las flechas de la paleta también usan `currentColor` para verse en los dos temas. |
| Botones | Una acción principal por bloque (`btn btn-primary`); lo demás, `btn btn-secondary` o `btn btn-ghost`. |
| Contraste | El texto blanco sobre el azul de los botones cumple 4,5:1; el texto tenue (`fg-faint`) solo se usa en datos secundarios (horas, ayudas). |
| Accesibilidad | Foco visible en todo (`:focus-visible`), `aria-label` en los botones con solo ícono, `aria-expanded` en los desplegables, `role="dialog"` con `aria-modal` y título en «Compartir», cierre con Escape. |
| Textos y pruebas | Las pruebas dependen de textos y de `data-testid`, no de colores ni de clases. |

## Componentes compartidos (`front_generador_bd/src/styles.css`)

Se definen una sola vez con `@apply` de Tailwind y las plantillas solo los nombran:

- `btn` + `btn-primary` / `btn-secondary` / `btn-ghost` / `btn-danger` / `btn-danger-soft`, con `btn-sm` y `btn-block`.
- `icon-btn` (botón cuadrado con ícono, para grupos como el zoom).
- `card` (superficie con borde y sombra suave), `panel-title`, `popover` (menú desplegable anclado a un botón de la barra superior).
- `field` (campos de texto y áreas de texto).
- `section-toggle` (encabezado plegable), `palette-tile` (ficha de la paleta), `badge`, `badge-brand`, `badge-ok`.
- `avatar` (círculo con la inicial de una persona; su color sale del nombre, ver `participants-panel/avatar.ts`).

## Cómo quedó el editor

- **Barra superior** (en lugar de las tarjetas flotantes): botón para ocultar o mostrar el panel de herramientas, zoom, Importar/Exportar XMI y, a la derecha, **Actividad**, las **personas conectadas** (círculos con su inicial), **Ayuda**, el **tema** y **Compartir**.
- **Actividad** es un desplegable: lista con desplazamiento (no crece con la sala) y, si llegó algo mientras estaba cerrado, el botón muestra un número (hasta «9+»).
- **Participantes** son círculos en la barra (se ven hasta tres y el resto como «+N»); al tocarlos se abre la lista con rol, «(Tú)», el estado de la IA y el botón **Expulsar** para el Host.
- **Compartir** (como en draw.io) abre una ventana con: el **enlace de invitación** (`/diagram/<código>`: quien lo abre solo escribe su nombre), **Copiar código de sala**, y el **enlace para seguir desde el celular** (solo lectura; en iPhone, agregarlo a Inicio para recibir avisos). Reemplaza a los botones sueltos del panel lateral.
- Un solo menú abierto a la vez; se cierran al tocar fuera o con Escape.
- Lienzo vacío: una pista centrada («Arrastra una «Clase UML» desde la paleta…»).
- **Panel lateral, chat de la IA, ayuda, portada y vista del celular:** mismos componentes con los colores nuevos.

## Lo que no se tocó

- Las formas del lienzo (clases y relaciones de JointJS): llevan la lógica de selección y de exportación a imagen; solo se aclaran por CSS las líneas en el tema oscuro.
- Ninguna lógica de colaboración, de la IA ni de los generadores. Cambió el **lugar** de dos acciones (copiar el código y el enlace del celular: del panel lateral a «Compartir»), con los mismos textos de botón.
