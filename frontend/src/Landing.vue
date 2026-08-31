<template src="./landing-body.html"></template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

const cleanups = []
let styleLink = null

function setBodyOverflow(hidden) {
  document.body.style.overflow = hidden ? 'hidden' : ''
}

onMounted(() => {
  /* ===== Landing stylesheet (only while the landing is visible) ===== */
  styleLink = document.createElement('link')
  styleLink.rel = 'stylesheet'
  styleLink.href = '/landing.css'
  document.head.appendChild(styleLink)
  cleanups.push(() => styleLink && styleLink.remove())

  /* ===== Header: shadow on scroll ===== */
  const header = document.getElementById('header')
  const onScroll = () => {
    if (header) header.classList.toggle('scrolled', window.scrollY > 8)
  }
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  cleanups.push(() => window.removeEventListener('scroll', onScroll))

  /* ===== Mobile menu ===== */
  const navToggle = document.getElementById('navToggle')
  const mobileMenu = document.getElementById('mobileMenu')
  const setMenu = (open) => {
    document.body.classList.toggle('menu-open', open)
    if (navToggle) {
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false')
      navToggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню')
    }
    if (mobileMenu) mobileMenu.setAttribute('aria-hidden', open ? 'false' : 'true')
    setBodyOverflow(open)
  }
  const onToggleClick = () => setMenu(!document.body.classList.contains('menu-open'))
  const onKeydown = (e) => { if (e.key === 'Escape') setMenu(false) }
  if (navToggle && mobileMenu) {
    navToggle.addEventListener('click', onToggleClick)
    document.addEventListener('keydown', onKeydown)
    mobileMenu.querySelectorAll('a').forEach((link) => {
      const onClose = () => setMenu(false)
      link.addEventListener('click', onClose)
      cleanups.push(() => link.removeEventListener('click', onClose))
    })
    cleanups.push(() => {
      navToggle.removeEventListener('click', onToggleClick)
      document.removeEventListener('keydown', onKeydown)
      setMenu(false)
    })
  }

  /* ===== Reveal on scroll ===== */
  const revealEls = Array.from(document.querySelectorAll('.reveal'))
  let revealObserver = null
  if ('IntersectionObserver' in window) {
    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in')
          revealObserver.unobserve(entry.target)
        }
      })
    }, { threshold: 0.12, rootMargin: '0px 0px -36px 0px' })
    revealEls.forEach((el) => revealObserver.observe(el))
    cleanups.push(() => revealObserver.disconnect())
  } else {
    revealEls.forEach((el) => el.classList.add('in'))
  }
  /* ===== Animated counters ===== */
  const animateCounter = (el) => {
    const target = parseFloat(el.getAttribute('data-count')) || 0
    const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10)
    const duration = 1700
    let start = null
    const fmt = (value) => value.toLocaleString('ru-RU', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })
    const step = (ts) => {
      if (!start) start = ts
      const p = Math.min((ts - start) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      el.textContent = fmt(target * eased)
      if (p < 1) el._raf = requestAnimationFrame(step)
    }
    el._raf = requestAnimationFrame(step)
  }
  const counters = Array.from(document.querySelectorAll('[data-count]'))
  let counterObserver = null
  if ('IntersectionObserver' in window) {
    counterObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target)
          counterObserver.unobserve(entry.target)
        }
      })
    }, { threshold: 0.6 })
    counters.forEach((el) => counterObserver.observe(el))
    cleanups.push(() => counterObserver.disconnect())
  } else {
    counters.forEach(animateCounter)
  }
  cleanups.push(() => counters.forEach((el) => el._raf && cancelAnimationFrame(el._raf)))

  /* ===== Accordions (program + FAQ) ===== */
  document.querySelectorAll('[data-acc-group]').forEach((group) => {
    group.querySelectorAll('.acc-head').forEach((head) => {
      const onAccClick = () => {
        const item = head.closest('.acc')
        const wasOpen = item.classList.contains('open')
        group.querySelectorAll('.acc.open').forEach((openItem) => {
          openItem.classList.remove('open')
          const h = openItem.querySelector('.acc-head')
          if (h) h.setAttribute('aria-expanded', 'false')
        })
        if (!wasOpen) {
          item.classList.add('open')
          head.setAttribute('aria-expanded', 'true')
        }
      }
      head.addEventListener('click', onAccClick)
      cleanups.push(() => head.removeEventListener('click', onAccClick))
    })
  })

  /* ===== Active nav link ===== */
  const navLinks = Array.from(document.querySelectorAll('.nav-link'))
  const sections = Array.from(document.querySelectorAll('main section[id]'))
  let navObserver = null
  if ('IntersectionObserver' in window && navLinks.length && sections.length) {
    navObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          navLinks.forEach((link) => {
            link.classList.toggle('active', link.getAttribute('href') === '#' + entry.target.id)
          })
        }
      })
    }, { rootMargin: '-40% 0px -55% 0px' })
    sections.forEach((s) => navObserver.observe(s))
    cleanups.push(() => navObserver.disconnect())
  }
  /* ===== 3D Rubik's cube ===== */
  const cube = document.getElementById('cube')
  const tilt = document.getElementById('cubeTilt')
  const stage = document.getElementById('cubeStage')
  if (cube && tilt && stage) {
    const C = 64
    const GAP = 3
    const O = C + GAP
    const COLORS = [
      { key: 'f', color: 'c-g', on: (x, y, z) => z === 2 },
      { key: 'b', color: 'c-b', on: (x, y, z) => z === 0 },
      { key: 'r', color: 'c-r', on: (x, y, z) => x === 2 },
      { key: 'l', color: 'c-o', on: (x, y, z) => x === 0 },
      { key: 'u', color: 'c-w', on: (x, y, z) => y === 0 },
      { key: 'd', color: 'c-y', on: (x, y, z) => y === 2 },
    ]
    const frag = document.createDocumentFragment()
    for (let x = 0; x < 3; x++) {
      for (let y = 0; y < 3; y++) {
        for (let z = 0; z < 3; z++) {
          if (x === 1 && y === 1 && z === 1) continue
          const cubie = document.createElement('div')
          cubie.className = 'cubie'
          cubie.style.transform = `translate3d(${(x - 1) * O}px, ${(y - 1) * O}px, ${(z - 1) * O}px)`
          COLORS.forEach((side) => {
            const face = document.createElement('div')
            face.className = 'face f-' + side.key
            if (side.on(x, y, z)) {
              const sticker = document.createElement('div')
              sticker.className = 'sticker ' + side.color
              face.appendChild(sticker)
            }
            cubie.appendChild(face)
          })
          frag.appendChild(cubie)
        }
      }
    }
    cube.appendChild(frag)
    cleanups.push(() => { cube.innerHTML = '' })

    /* Mouse parallax (fine pointers only) */
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const finePointer = window.matchMedia('(pointer: fine)').matches
    const hero = document.querySelector('.hero')
    if (!reduceMotion && finePointer && hero) {
      const onMove = (e) => {
        const rect = hero.getBoundingClientRect()
        const nx = (e.clientX - rect.left) / rect.width - 0.5
        const ny = (e.clientY - rect.top) / rect.height - 0.5
        tilt.style.setProperty('--ry', (14 + nx * 16).toFixed(2) + 'deg')
        tilt.style.setProperty('--rx', (-20 - ny * 12).toFixed(2) + 'deg')
      }
      const onLeave = () => {
        tilt.style.setProperty('--ry', '14deg')
        tilt.style.setProperty('--rx', '-20deg')
      }
      hero.addEventListener('mousemove', onMove)
      hero.addEventListener('mouseleave', onLeave)
      cleanups.push(() => {
        hero.removeEventListener('mousemove', onMove)
        hero.removeEventListener('mouseleave', onLeave)
      })
    }
  }

  /* ===== Footer year ===== */
  const year = document.getElementById('year')
  if (year) year.textContent = String(new Date().getFullYear())
})
</script>