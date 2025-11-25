let allItems = [];

async function uploadFile() {
    const fileInput = document.getElementById('pdfUpload');
    const apiKeyInput = document.getElementById('apiKey');
    const file = fileInput.files[0];
    if (!file) return alert('Please select a file');

    const formData = new FormData();
    formData.append('file', file);
    if (apiKeyInput && apiKeyInput.value) {
        formData.append('api_key', apiKeyInput.value);
    }

    document.getElementById('uploadStatus').innerText = 'Uploading and extracting...';

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        document.getElementById('uploadStatus').innerText = 'Extraction complete!';
        // Add new items to local state
        allItems = [...allItems, ...data.items];
        renderTable(data.items, `Extracted from ${file.name}`);
    } catch (e) {
        document.getElementById('uploadStatus').innerText = 'Error: ' + e.message;
    }
}

async function loadItems() {
    const res = await fetch('/api/items');
    const items = await res.json();
    allItems = items;
    renderTable(items, 'All Extracted Items');
}

function renderTable(items, title) {
    const container = document.getElementById('resultsArea');

    let html = `
        <div class="bg-white rounded-lg shadow overflow-hidden mb-8">
            <div class="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                <h3 class="text-lg font-medium text-gray-900">${title}</h3>
                <span class="text-sm text-gray-500">${items.length} items</span>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Product ID</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Product</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Qty</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Unit Price</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
    `;

    if (items.length === 0) {
        html += `<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">No items found.</td></tr>`;
    } else {
        items.forEach(item => {
            html += `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <input type="text" value="${item.product_id || ''}" 
                            onchange="updateItem(${item.id}, 'product_id', this.value)"
                            class="border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm w-full border p-1"
                        />
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <input type="text" value="${item.product_name}" 
                            onchange="updateItem(${item.id}, 'product_name', this.value)"
                            class="border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm w-full border p-1"
                        />
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <input type="number" value="${item.quantity}" 
                            onchange="updateItem(${item.id}, 'quantity', this.value)"
                            class="border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm w-20 border p-1"
                        />
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <input type="number" step="0.01" value="${item.unit_price}" 
                            onchange="updateItem(${item.id}, 'unit_price', this.value)"
                            class="border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm w-24 border p-1"
                        />
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        $${item.total_price.toFixed(2)}
                    </td>
                </tr>
            `;
        });
    }

    html += `</tbody></table></div></div>`;

    // Append instead of replace if we want to show history, but for now replace is cleaner
    container.innerHTML = html;
}

async function updateItem(id, field, value) {
    const item = allItems.find(i => i.id === id);
    if (!item) return;

    item[field] = field === 'product_name' ? value : parseFloat(value);

    if (field === 'quantity' || field === 'unit_price') {
        item.total_price = item.quantity * item.unit_price;
    }

    await fetch(`/api/items/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
    });

    // Optional: visual feedback
}

async function showComparison() {
    const res = await fetch('/api/items');
    const items = await res.json();
    allItems = items;

    const groups = {};
    items.forEach(item => {
        const key = item.product_name.toLowerCase().trim();
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
    });

    const container = document.getElementById('resultsArea');
    let html = `<h2 class="text-2xl font-bold mb-6 text-gray-800">Price Comparison</h2>`;

    if (Object.keys(groups).length === 0) {
        html += `<p class="text-gray-500">No data to compare.</p>`;
    }

    for (const [product, groupItems] of Object.entries(groups)) {
        const bestPrice = Math.min(...groupItems.map(i => i.unit_price));

        html += `
            <div class="bg-white rounded-lg shadow mb-6 p-6 border border-gray-100">
                <h3 class="text-lg font-bold capitalize mb-4 text-gray-800">${product}</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        `;

        groupItems.forEach(item => {
            const isBest = item.unit_price === bestPrice;
            html += `
                <div class="border rounded p-4 relative ${isBest ? 'border-green-500 bg-green-50 ring-1 ring-green-200' : 'border-gray-200 hover:border-indigo-200'}">
                    <div class="text-sm text-gray-500 mb-1 font-medium">${item.supplier_name || 'Unknown Supplier'}</div>
                    <div class="text-2xl font-bold text-gray-900">$${item.unit_price.toFixed(2)}</div>
                    <div class="text-xs text-gray-500">per unit</div>
                    ${isBest ? '<div class="absolute top-4 right-4 text-xs font-bold text-green-700 bg-green-200 px-2 py-1 rounded">BEST PRICE</div>' : ''}
                </div>
            `;
        });

        html += `</div></div>`;
    }

    container.innerHTML = html;
}
