const API_BASE_URL = '/api/v1';

document.addEventListener('DOMContentLoaded', () => {
    loadProducts();

    const productForm = document.getElementById('productForm');
    if (productForm) {
        productForm.addEventListener('submit', handleCreateProduct);
    }
});

function getAuthToken() {
    return localStorage.getItem('access_token');
}

async function loadProducts() {
    const tableBody = document.getElementById('productsTableBody');
    const token = getAuthToken();

    if (!token) {
        tableBody.innerHTML = '<tr><td colspan="4">Error: Sesión no válida. Inicia sesión.</td></tr>';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/products`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Sesión expirada. Por favor vuelve a ingresar.');
            }
            throw new Error('No se pudo cargar la lista de productos.');
        }

        const products = await response.json();
        renderProductsTable(products);

    } catch (error) {
        tableBody.innerHTML = '';
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 4;
        cell.className = 'error-msg';
        cell.textContent = error.message;
        row.appendChild(cell);
        tableBody.appendChild(row);
    }
}

// Renderizado seguro previniendo inyecciones XSS
function renderProductsTable(products) {
    const tableBody = document.getElementById('productsTableBody');
    tableBody.innerHTML = '';

    if (!products || products.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4">No tienes productos en seguimiento aún.</td>';
        tableBody.appendChild(row);
        return;
    }

    products.forEach(product => {
        const row = document.createElement('tr');

        // Célula URL (Construcción segura de DOM)
        const urlCell = document.createElement('td');
        const link = document.createElement('a');
        link.href = product.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = product.url;
        link.style.color = '#60a5fa';
        urlCell.appendChild(link);

        // Célula Precio Actual
        const priceCell = document.createElement('td');
        priceCell.textContent = product.current_price !== null && product.current_price !== undefined
            ? `$${Number(product.current_price).toFixed(2)}`
            : 'Pendiente';

        // Célula Precio Objetivo
        const targetCell = document.createElement('td');
        targetCell.textContent = product.alert && product.alert.target_price !== undefined
            ? `$${Number(product.alert.target_price).toFixed(2)}`
            : 'N/A';

        // Célula Estado
        const statusCell = document.createElement('td');
        statusCell.textContent = product.alert && product.alert.is_active ? 'Activa' : 'Inactiva';

        row.appendChild(urlCell);
        row.appendChild(priceCell);
        row.appendChild(targetCell);
        row.appendChild(statusCell);

        tableBody.appendChild(row);
    });
}

async function handleCreateProduct(event) {
    event.preventDefault();

    const feedbackEl = document.getElementById('feedbackMessage');
    const urlInput = document.getElementById('productUrl');
    const priceInput = document.getElementById('targetPrice');
    const token = getAuthToken();

    feedbackEl.textContent = '';
    feedbackEl.className = '';

    if (!token) {
        feedbackEl.textContent = 'Error: Usuario no autenticado.';
        feedbackEl.className = 'error-msg';
        return;
    }

    const payload = {
        url: urlInput.value.trim(),
        target_price: parseFloat(priceInput.value)
    };

    try {
        const response = await fetch(`${API_BASE_URL}/products`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            let errorMsg = 'Error al registrar el producto.';
            if (data.detail) {
                errorMsg = Array.isArray(data.detail) ? data.detail[0].msg : data.detail;
            }
            throw new Error(errorMsg);
        }

        feedbackEl.textContent = '¡Producto registrado con éxito!';
        feedbackEl.className = 'success-msg';

        event.target.reset();
        await loadProducts();

    } catch (error) {
        feedbackEl.textContent = error.message;
        feedbackEl.className = 'error-msg';
    }
}