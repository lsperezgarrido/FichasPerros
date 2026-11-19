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
        !resumenNombres
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

    function ocultarMensajes() {
        aviso.hidden = true;
        resumen.hidden = true;
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
        aviso.hidden = true;
        resumen.hidden = false;
        resumen.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    actualizarContador();
})();
