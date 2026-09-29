const API_BASE_URL = 'http://localhost:8000/api/v1';

document.addEventListener("DOMContentLoaded", () => {
    loadUserProducts();

    const productForm = document.getElementById("product-form");
    if (productForm) {
        productForm.addEventListener("submit", handleCreateProduct);
    }
});

function getAuthToken() {
    return localStorage.getItem("access_token") || localStorage.getItem("valora_access_token");
}

async function loadUserProducts() {
    const tableBody = document.getElementById("products-table-body");
    const token = getAuthToken();

    if (!tableBody) {
        return;
    }

    if (!token) {
        renderTableMessage(tableBody, "Sesión no válida. Por favor inicie sesión.", "feedback error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/products?limit=20`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("Sesión expirada o token inválido.");
            }
            throw await getResponseError(response, "Error al obtener la lista de productos.");
        }

        const products = await response.json();
        renderProductsTable(products);

    } catch (error) {
        console.error("Error cargando productos:", error);
        renderTableMessage(tableBody, error.message, "feedback error");
    }
}

function renderTableMessage(tableBody, message, className = "") {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = message;
    if (className) {
        cell.className = className;
    }
    row.appendChild(cell);
    tableBody.replaceChildren(row);
}

async function getResponseError(response, fallbackMessage) {
    let errData;
    try {
        errData = await response.json();
    } catch {
        return new Error(fallbackMessage);
    }

    const detail = errData?.detail;
    const message = Array.isArray(detail)
        ? detail.map(item => item.msg).filter(Boolean).join(", ")
        : detail;
    return new Error(message || fallbackMessage);
}

function renderProductsTable(products) {
    const tableBody = document.getElementById("products-table-body");
    if (!tableBody) {
        return;
    }
    tableBody.replaceChildren();

    if (!Array.isArray(products) || products.length === 0) {
        renderTableMessage(tableBody, "No hay productos registrados actualmente.");
        return;
    }

    products.forEach(prod => {
        const row = document.createElement("tr");

        const urlCell = document.createElement("td");
        const link = document.createElement("a");
        const productUrl = String(prod.url || "");
        try {
            const parsedUrl = new URL(productUrl);
            if (parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:") {
                link.href = parsedUrl.href;
                link.textContent = productUrl;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.style.color = "#60a5fa";
                urlCell.appendChild(link);
            } else {
                urlCell.textContent = productUrl;
            }
        } catch {
            urlCell.textContent = productUrl;
        }

        const priceCell = document.createElement("td");
        priceCell.textContent = prod.current_price !== null && prod.current_price !== undefined
            ? `$${Number(prod.current_price).toFixed(2)}`
            : "Pendiente de extracción";

        const targetCell = document.createElement("td");
        const targetPrice = prod.alert?.target_price ?? prod.target_price;
        targetCell.textContent = targetPrice !== null && targetPrice !== undefined
            ? `$${Number(targetPrice).toFixed(2)}`
            : "N/A";

        const dateCell = document.createElement("td");
        dateCell.textContent = prod.created_at ? new Date(prod.created_at).toLocaleString() : "N/A";

        row.appendChild(urlCell);
        row.appendChild(priceCell);
        row.appendChild(targetCell);
        row.appendChild(dateCell);

        tableBody.appendChild(row);
    });
}

async function handleCreateProduct(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const urlInput = document.getElementById("product_url");
    const targetPriceInput = document.getElementById("target_price");
    const feedback = document.getElementById("form-feedback");
    const submitBtn = document.getElementById("submit-btn");
    const token = getAuthToken();

    feedback.textContent = "";
    feedback.className = "";
    submitBtn.disabled = true;
    submitBtn.textContent = "Guardando...";

    try {
        if (!token) {
            throw new Error("Sesión no válida. Por favor inicie sesión.");
        }

        const payload = {
            product_url: urlInput.value.trim()
        };
        const targetPrice = targetPriceInput?.value.trim();
        if (targetPrice) {
            payload.target_price = Number(targetPrice);
        }

        const response = await fetch(`${API_BASE_URL}/products`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw await getResponseError(response, "No se pudo registrar el producto.");
        }

        feedback.textContent = "¡Producto registrado exitosamente y encolado para análisis!";
        feedback.className = "feedback success";
        form.reset();
        await loadUserProducts();

    } catch (error) {
        console.error("Error al registrar producto:", error);
        feedback.textContent = error.message;
        feedback.className = "feedback error";
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Guardar y Monitorear";
    }
}