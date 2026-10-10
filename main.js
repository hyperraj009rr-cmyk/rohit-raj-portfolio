document.addEventListener("DOMContentLoaded",()=>{
 const btn=document.querySelector(".menu-toggle"),nav=document.querySelector(".nav-links");
 if(btn&&nav)btn.addEventListener("click",()=>nav.classList.toggle("open"));
 if(!sessionStorage.getItem("rrIntro")&&document.querySelector(".hero")){
  const el=document.createElement("div");el.className="intro";el.innerHTML='<div class="intro-mark">R<span>.</span></div><b>ROHIT RAJ</b><i></i><small>IDEAS INTO REAL THINGS</small>';document.body.appendChild(el);
  setTimeout(()=>{el.classList.add("out");sessionStorage.setItem("rrIntro","1");setTimeout(()=>el.remove(),700)},1250);
 }
 const obs=("IntersectionObserver"in window)?new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add("shown");obs.unobserve(e.target)}}),{threshold:.08}):null;
 document.querySelectorAll(".reveal").forEach(e=>obs?obs.observe(e):e.classList.add("shown"));
 document.querySelectorAll(".flash").forEach(e=>setTimeout(()=>{e.style.opacity=0;setTimeout(()=>e.remove(),350)},4500));
});
