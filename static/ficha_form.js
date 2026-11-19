(() => {
    "use strict";

    const input = document.getElementById("fotografias");
    const preview = document.getElementById("previsualizacion-fotos");
    const formatos = new Set([".jpg", ".jpeg", ".png", ".webp"]);
    let urls = [];

    function limpiarPrevisualizacion() {
        urls.forEach((url) => URL.revokeObjectURL(url));
        urls = [];
        if (preview) {
            preview.replaceChildren();
        }
    }

    if (input && preview) {
        input.addEventListener("change", () => {
            limpiarPrevisualizacion();
            const archivos = Array.from(input.files || []);
            archivos.forEach((archivo) => {
                const nombre = archivo.name.toLowerCase();
                const extension = nombre.slice(nombre.lastIndexOf("."));
                if (!formatos.has(extension)) {
                    return;
                }

                const url = URL.createObjectURL(archivo);
                urls.push(url);

                const figura = document.createElement("figure");
                figura.className = "preview-item";
                const imagen = document.createElement("img");
                imagen.src = url;
                imagen.alt = archivo.name;
                const pie = document.createElement("figcaption");
                pie.textContent = archivo.name;
                figura.append(imagen, pie);
                preview.append(figura);
            });
        });
    }

    const checksQuitar = document.querySelectorAll(".quitar-foto-check");
    checksQuitar.forEach((check) => {
        const tarjeta = check.closest(".foto-card");
        const actualizar = () => {
            if (tarjeta) {
                tarjeta.classList.toggle("is-removed", check.checked);
            }
        };
        check.addEventListener("change", actualizar);
        actualizar();
    });

    window.addEventListener("pagehide", limpiarPrevisualizacion);
})();
