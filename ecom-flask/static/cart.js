// ---- LocalStorage cart utilities ----

function getCart(){
  try { return JSON.parse(localStorage.getItem('cart') || '[]'); }
  catch(e){ return []; }
}

function saveCart(cart){
  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartCount();
}

function updateCartCount(){
  const badge = document.getElementById('cart-count-badge');
  if (!badge) return;
  const cart = getCart();
  const count = cart.reduce((s, it) => s + (parseInt(it.qty)||0), 0);
  badge.textContent = count;
}

function addToCart(product, qty=1){
  const cart = getCart();
  const idx = cart.findIndex(it => parseInt(it.id) === parseInt(product.id));
  if (idx >= 0){
    cart[idx].qty = (parseInt(cart[idx].qty)||0) + (parseInt(qty)||1);
  } else {
    cart.push({
      id: parseInt(product.id),
      title: product.title,
      price: parseFloat(product.price),
      image: product.image,
      qty: parseInt(qty)||1
    });
  }
  saveCart(cart);
  // small toast-ish feedback
  try {
    const b = document.createElement('div');
    b.className = 'position-fixed bottom-0 end-0 p-3';
    b.innerHTML = `<div class="toast align-items-center text-bg-success border-0 show" role="alert">
      <div class="d-flex">
        <div class="toast-body"><i class="bi bi-check-circle me-1"></i> Added to cart</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()"></button>
      </div></div>`;
    document.body.appendChild(b);
    setTimeout(()=> b.remove(), 1500);
  } catch(e){}
}

function addToCartFromButton(btn){
  const product = {
    id: parseInt(btn.dataset.id),
    title: btn.dataset.title,
    price: parseFloat(btn.dataset.price),
    image: btn.dataset.image
  };
  addToCart(product, 1);
}

// ---- Cart page rendering ----
function renderCart(){
  const cart = getCart();
  const empty = document.getElementById('cart-empty');
  const filled = document.getElementById('cart-filled');
  const body = document.getElementById('cart-body');
  const totalEl = document.getElementById('cart-total');
  if (!empty || !filled) return;

  if (!cart.length){
    empty.classList.remove('d-none');
    filled.classList.add('d-none');
    updateCartCount();
    return;
  }
  empty.classList.add('d-none');
  filled.classList.remove('d-none');

  let html = '';
  let total = 0;
  cart.forEach(item => {
    const subtotal = item.qty * item.price;
    total += subtotal;
    html += `
      <tr>
        <td>
          <div class="d-flex align-items-center gap-3">
            <img src="${item.image}" alt="${item.title}" style="width:64px;height:64px;object-fit:cover;border-radius:8px;">
            <div>
              <div class="fw-semibold">${item.title}</div>
              <div class="text-muted small">$${item.price.toFixed(2)}</div>
            </div>
          </div>
        </td>
        <td>$${item.price.toFixed(2)}</td>
        <td>
          <div class="input-group" style="max-width:140px;">
            <button class="btn btn-outline-secondary" type="button" onclick="changeQty(${item.id}, -1)">−</button>
            <input class="form-control text-center" type="number" min="1" value="${item.qty}" onchange="setQty(${item.id}, this.value)">
            <button class="btn btn-outline-secondary" type="button" onclick="changeQty(${item.id}, 1)">+</button>
          </div>
        </td>
        <td>$${subtotal.toFixed(2)}</td>
        <td class="text-end">
          <button class="btn btn-outline-danger btn-sm" onclick="removeItem(${item.id})"><i class="bi bi-trash"></i></button>
        </td>
      </tr>`;
  });
  body.innerHTML = html;
  totalEl.textContent = `$${total.toFixed(2)}`;
  updateCartCount();
}

function changeQty(id, delta){
  const cart = getCart();
  const item = cart.find(it => parseInt(it.id) === parseInt(id));
  if (!item) return;
  item.qty = Math.max(1, (parseInt(item.qty)||1) + delta);
  saveCart(cart);
  renderCart();
}

function setQty(id, val){
  const cart = getCart();
  const item = cart.find(it => parseInt(it.id) === parseInt(id));
  if (!item) return;
  const v = Math.max(1, parseInt(val)||1);
  item.qty = v;
  saveCart(cart);
  renderCart();
}

function removeItem(id){
  let cart = getCart();
  cart = cart.filter(it => parseInt(it.id) !== parseInt(id));
  saveCart(cart);
  renderCart();
}
(function(){
  const onReady = () => {
    if (document.getElementById('cart-body')) {
      renderCart();
    }
    updateCartCount();
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }
})();
