/* Copiloto — comportamento das paginas publicadas.
   Sem biblioteca, sem rede. Tudo aqui e' enfeite: se este arquivo nao carregar,
   a pagina continua completa e legivel — por isso a classe .js so' entra agora,
   e o CSS so' esconde o .revelar quando ela existe.
   Respeita prefers-reduced-motion: quem pediu menos movimento nao ganha nenhum. */
(function () {
  "use strict";
  var raiz = document.documentElement;
  var quieto = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!quieto) raiz.classList.add("js");

  function pronto(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  pronto(function () {
    // ---------------------------------------------------- entrada de secao
    var alvos = document.querySelectorAll(".revelar");
    if (alvos.length && !quieto && "IntersectionObserver" in window) {
      var olho = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("visivel");
            olho.unobserve(e.target);
          }
        });
      }, { rootMargin: "0px 0px -12% 0px", threshold: 0.08 });
      alvos.forEach(function (el) { olho.observe(el); });
    } else {
      alvos.forEach(function (el) { el.classList.add("visivel"); });
    }

    // -------------------------------------------------------- contadores
    // <p class="numero" data-contar="3000" data-prefixo="+">0</p>
    document.querySelectorAll("[data-contar]").forEach(function (el) {
      var fim = parseFloat(el.getAttribute("data-contar"));
      if (isNaN(fim)) return;
      var pre = el.getAttribute("data-prefixo") || "";
      var pos = el.getAttribute("data-sufixo") || "";
      var escreve = function (v) { el.textContent = pre + Math.round(v).toLocaleString("pt-BR") + pos; };
      if (quieto || !("IntersectionObserver" in window)) { escreve(fim); return; }
      escreve(0);
      var obs = new IntersectionObserver(function (ent) {
        if (!ent[0].isIntersecting) return;
        obs.disconnect();
        var t0 = null, dur = 1400;
        requestAnimationFrame(function passo(t) {
          if (t0 === null) t0 = t;
          var p = Math.min((t - t0) / dur, 1);
          escreve(fim * (1 - Math.pow(1 - p, 3)));   // desacelera no fim
          if (p < 1) requestAnimationFrame(passo);
        });
      }, { threshold: 0.4 });
      obs.observe(el);
    });

    // ---------------------------------------------------------- carrossel
    // As setas sao criadas aqui: sem JS o carrossel ainda rola com o dedo.
    document.querySelectorAll(".carrossel").forEach(function (trilho) {
      var caixa = trilho.closest(".carrossel-caixa");
      if (!caixa || caixa.querySelector(".carrossel-seta")) return;

      function seta(classe, rotulo, texto, dir) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "carrossel-seta " + classe;
        b.setAttribute("aria-label", rotulo);
        b.textContent = texto;
        b.addEventListener("click", function () {
          var passo = trilho.firstElementChild ? trilho.firstElementChild.offsetWidth + 16 : 320;
          trilho.scrollBy({ left: dir * passo, behavior: quieto ? "auto" : "smooth" });
        });
        caixa.appendChild(b);
        return b;
      }
      var ant = seta("ant", "Anterior", "‹", -1);
      var prox = seta("prox", "Proximo", "›", 1);

      function atualiza() {
        var max = trilho.scrollWidth - trilho.clientWidth - 2;
        ant.hidden = trilho.scrollLeft <= 2;
        prox.hidden = trilho.scrollLeft >= max || max <= 0;
      }
      trilho.addEventListener("scroll", atualiza, { passive: true });
      window.addEventListener("resize", atualiza);
      atualiza();
    });

    // ------------------------------------------- FAQ: so' um aberto por vez
    var faqs = document.querySelectorAll("details.faq");
    faqs.forEach(function (d) {
      d.addEventListener("toggle", function () {
        if (!d.open) return;
        faqs.forEach(function (o) { if (o !== d && o.open) o.open = false; });
      });
    });

    // ------------------------------- rolagem suave nos links de ancora (#)
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(function (a) {
      a.addEventListener("click", function (ev) {
        var alvo = document.querySelector(a.getAttribute("href"));
        if (!alvo) return;
        ev.preventDefault();
        alvo.scrollIntoView({ behavior: quieto ? "auto" : "smooth", block: "start" });
      });
    });
  });
})();
