(function () {
  'use strict';

  // ---- Hero slideshow (homepage only) ----
  function initHero() {
    var hero = document.querySelector('[data-hero]');
    if (!hero) return;
    var slides = Array.prototype.slice.call(hero.querySelectorAll('.hero-slide'));
    var dots = Array.prototype.slice.call(hero.querySelectorAll('.hero-dot'));
    if (slides.length < 2) return;
    var index = 0;

    function show(i) {
      index = (i + slides.length) % slides.length;
      slides.forEach(function (s, n) { s.classList.toggle('is-active', n === index); });
      dots.forEach(function (d, n) { d.classList.toggle('is-active', n === index); });
    }

    dots.forEach(function (d, n) {
      d.addEventListener('click', function () {
        show(n);
        resetTimer();
      });
    });

    var timer;
    function resetTimer() {
      clearInterval(timer);
      timer = setInterval(function () { show(index + 1); }, 4000);
    }
    resetTimer();
  }

  // ---- Lightbox (album pages) ----
  function initLightbox() {
    var items = Array.prototype.slice.call(document.querySelectorAll('.js-lightbox-item'));
    var lightbox = document.querySelector('.lightbox');
    if (!items.length || !lightbox) return;

    var img = lightbox.querySelector('.lightbox-photo img');
    var caption = lightbox.querySelector('.lightbox-caption');
    var counter = lightbox.querySelector('.lightbox-counter');
    var closeBtn = lightbox.querySelector('.lightbox-close');
    var prevBtn = lightbox.querySelector('.lightbox-prev');
    var nextBtn = lightbox.querySelector('.lightbox-next');
    var current = 0;

    function open(i) {
      current = i;
      render();
      lightbox.classList.add('is-open');
    }

    function render() {
      var item = items[current];
      img.src = item.getAttribute('data-full') || item.querySelector('img').src;
      img.alt = item.getAttribute('data-caption') || '';
      var cap = item.getAttribute('data-caption');
      if (cap) {
        caption.textContent = cap;
        caption.style.display = '';
      } else {
        caption.textContent = '';
        caption.style.display = 'none';
      }
      counter.textContent = (current + 1) + ' / ' + items.length;
    }

    function close() { lightbox.classList.remove('is-open'); }
    function step(delta) { open((current + delta + items.length) % items.length); }

    items.forEach(function (item, i) {
      item.addEventListener('click', function () { open(i); });
    });

    lightbox.addEventListener('click', close);
    lightbox.querySelector('.lightbox-body').addEventListener('click', function (e) { e.stopPropagation(); });
    closeBtn.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    prevBtn.addEventListener('click', function (e) { e.stopPropagation(); step(-1); });
    nextBtn.addEventListener('click', function (e) { e.stopPropagation(); step(1); });

    document.addEventListener('keydown', function (e) {
      if (!lightbox.classList.contains('is-open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') step(-1);
      if (e.key === 'ArrowRight') step(1);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initHero();
    initLightbox();
  });
})();
