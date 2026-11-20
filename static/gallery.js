(() => {
    "use strict";

    const galeria = document.querySelector(".galeria");
    if (!galeria) {
        return;
    }

    const checkboxes = Array.from(galeria.querySelectorAll(".foto-check"));
    const contador = document.getElementById("contador-seleccionadas");
    const textoContador = document.getElementById("texto-contador");
    const botonTodas = document.getElementById("seleccionar-todas");
    const botonNinguna = document.getElementById("deseleccionar-todas");
    const botonContinuar = document.getElementById("continuar-seleccion");
    const aviso = document.getElementById("aviso-seleccion");
    const resumen = document.getElementById("resumen-seleccion");
    const resumenCantidad = document.getElementById("resumen-cantidad");
    const resumenTexto = document.getElementById("resumen-texto");
    const resumenNombres = document.getElementById("resumen-nombres");
    const botonPdf = document.getElementById("generar-pdf");
    const estadoPdf = document.getElementById("estado-pdf");

    if (
        checkboxes.length === 0 ||
        !contador ||
        !textoContador ||
        !botonTodas ||
        !botonNinguna ||
        !botonContinuar ||
        !aviso ||
        !resumen ||
        !resumenCantidad ||
        !resumenTexto ||
        !resumenNombres ||
        !botonPdf ||
        !estadoPdf
    ) {
        return;
    }

    const seleccionadas = () => checkboxes.filter((checkbox) => checkbox.checked);

    function actualizarContador() {
        const total = seleccionadas().length;
        contador.textContent = String(total);
        textoContador.textContent = total === 1 ? "seleccionada" : "seleccionadas";
        botonTodas.disabled = total === checkboxes.length;
        botonNinguna.disabled = total === 0;
    }

    function prepararBotonPdf() {
        estadoPdf.replaceChildren();
        estadoPdf.classList.remove("is-error");
        botonPdf.disabled = false;
        botonPdf.textContent = "Generar PDF";
    }

    function ocultarMensajes() {
        aviso.hidden = true;
        resumen.hidden = true;
        prepararBotonPdf();
    }

    function actualizarSeleccion() {
        actualizarContador();
        ocultarMensajes();
    }

    checkboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", actualizarSeleccion);
    });

    botonTodas.addEventListener("click", () => {
        checkboxes.forEach((checkbox) => {
            checkbox.checked = true;
        });
        actualizarSeleccion();
    });

    botonNinguna.addEventListener("click", () => {
        checkboxes.forEach((checkbox) => {
            checkbox.checked = false;
        });
        actualizarSeleccion();
    });

    botonContinuar.addEventListener("click", () => {
        const elegidas = seleccionadas();
        if (elegidas.length === 0) {
            resumen.hidden = true;
            aviso.textContent = "Selecciona al menos una fotografía para continuar.";
            aviso.hidden = false;
            aviso.scrollIntoView({ behavior: "smooth", block: "nearest" });
            return;
        }

        resumenNombres.replaceChildren();
        elegidas.forEach((checkbox) => {
            const elemento = document.createElement("li");
            elemento.textContent = checkbox.dataset.nombre || "Fotografía";
            resumenNombres.append(elemento);
        });
        resumenCantidad.textContent = String(elegidas.length);
        resumenTexto.textContent =
            elegidas.length === 1 ? "fotografía seleccionada" : "fotografías seleccionadas";
        prepararBotonPdf();
        aviso.hidden = true;
        resumen.hidden = false;
        resumen.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    botonPdf.addEventListener("click", async () => {
        const elegidas = seleccionadas();
        if (elegidas.length === 0) {
            resumen.hidden = true;
            aviso.textContent = "Selecciona al menos una fotografía para generar el PDF.";
            aviso.hidden = false;
            return;
        }

        const datos = new FormData();
        elegidas.forEach((checkbox) => {
            datos.append("foto_ids", checkbox.value);
        });

        botonPdf.disabled = true;
        botonPdf.textContent = "Generando PDF…";
        estadoPdf.replaceChildren();
        estadoPdf.classList.remove("is-error");

        try {
            const respuesta = await fetch("/generar-pdf", {
                method: "POST",
                body: datos,
            });
            let resultado = {};
            try {
                resultado = await respuesta.json();
            } catch (_error) {
                resultado = {};
            }
            if (!respuesta.ok) {
                throw new Error(resultado.error || "No se pudo generar el PDF.");
            }

            const texto = document.createElement("span");
            const fichas = resultado.fichas;
            const paginas = resultado.paginas;
            texto.textContent =
                `PDF generado: ${resultado.nombre} ` +
                `(${fichas} ${fichas === 1 ? "ficha" : "fichas"}, ` +
                `${paginas} ${paginas === 1 ? "página" : "páginas"}). `;

            const enlace = document.createElement("a");
            enlace.href = resultado.url;
            enlace.target = "_blank";
            enlace.rel = "noopener";
            enlace.className = "download-link";
            enlace.textContent = "Abrir PDF";

            estadoPdf.append(texto, enlace);
            botonPdf.textContent = "Generar otro PDF";
        } catch (error) {
            estadoPdf.classList.add("is-error");
            estadoPdf.textContent = error.message || "No se pudo generar el PDF.";
            botonPdf.textContent = "Generar PDF";
        } finally {
            botonPdf.disabled = false;
        }
    });

    actualizarContador();
})();
