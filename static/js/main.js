const menuToggle = document.querySelector('.menu-toggle');
const menu = document.querySelector('#main-menu');

if (menuToggle && menu) {
    menuToggle.addEventListener('click', () => {
        const isOpen = menu.classList.toggle('is-open');
        menuToggle.setAttribute('aria-expanded', String(isOpen));
    });
}
