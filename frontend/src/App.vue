<script setup>
import { computed, onMounted, ref } from 'vue'
import Landing from './Landing.vue'


const page = ref('landing')
const authMode = ref('login')
const user = ref(null)
const algorithms = ref([])
const progress = ref(null)
const currentAlgorithm = ref(null)
const loading = ref(false)
const dataLoaded = ref(false)
const error = ref('')
const notice = ref('')
// --- Подтверждение email ---
const verificationSent = ref(false)      // показать панель «письмо отправлено» на странице auth
const pendingEmail = ref('')             // email только что зарегистрированного пользователя
const resending = ref(false)
const resendNotice = ref('')
const showResendHint = ref(false)        // подсказка переотправки при логине с 403
const verificationState = ref('idle')    // idle | verifying | success | error (страница #/verify)
const verificationMessage = ref('')
const filter = ref('OLL')
const search = ref('')
const showPassword = ref(false)
const auth = ref({ username: '', email: '', password: '' })

const apiBaseUrl = import.meta.env.VITE_API_URL.replace(/\/$/, '')

const api = async (url, options = {}) => {
  const response = await fetch(`${apiBaseUrl}/api${url}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (response.status === 204) return null
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Не удалось выполнить запрос.')
  return body
}

const route = () => {
  const { pathname, search, hash } = window.location
  // Legacy-поддержка старых hash-ссылок (#/verify?token=... из писем, закладки)
  if (hash.startsWith('#/')) return hash.slice(1)
  return pathname + search || '/'
}
const navigate = (path) => {
  history.pushState({}, '', path)
  window.scrollTo(0, 0)
  consumeRoute()
}
const initials = computed(() => user.value?.username?.slice(0, 2).toUpperCase() || '?')
const stats = computed(() => progress.value?.statistics || {
  oll_learned: 0, oll_total: 57, pll_learned: 0, pll_total: 21, learned_total: 0, total_algorithms: 78, overall_percentage: 0,
})
const filteredAlgorithms = computed(() => algorithms.value.filter((algorithm) =>
  algorithm.category === filter.value && `${algorithm.name} ${algorithm.algorithm_number} ${algorithm.formula}`.toLowerCase().includes(search.value.toLowerCase()),
))
const nextAlgorithm = computed(() => algorithms.value.find((item) => !item.is_learned) || null)
const streak = computed(() => {
  const learnedDates = new Set((progress.value?.records || []).map((record) => new Date(record.learned_at).toDateString()))
  let count = 0
  const date = new Date()
  date.setHours(0, 0, 0, 0)
  if (!learnedDates.has(date.toDateString())) {
    date.setDate(date.getDate() - 1)
  }
  while (learnedDates.has(date.toDateString())) {
    count += 1
    date.setDate(date.getDate() - 1)
  }
  return count
})
const activityDays = computed(() => {
  const learnedDates = new Set((progress.value?.records || []).map((record) => new Date(record.learned_at).toDateString()))
  const days = []
  const today = new Date()
  for (let i = 13; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    const isLearned = learnedDates.has(d.toDateString())
    const dateStr = d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
    days.push({ dateStr, active: isLearned })
  }
  return days
})

function consumeRoute() {
  const value = route()
  if (value === '/') page.value = 'landing'
  else if (value === '/auth') page.value = 'auth'
  else if (value === '/learning') page.value = 'learning'
  else if (value === '/algorithms') page.value = 'algorithms'
  else if (value.startsWith('/algorithms/')) {
    page.value = 'detail'
    const id = Number(value.split('/').pop())
    if (id) loadAlgorithm(id)
  } else if (value === '/profile') page.value = 'profile'
  else if (value.startsWith('/verify')) {
    page.value = 'verify'
    const token = new URLSearchParams(value.split('?')[1] || '').get('token')
    if (!token) {
      verificationState.value = 'error'
      verificationMessage.value = 'В ссылке отсутствует токен подтверждения.'
    } else if (verificationState.value !== 'success') {
      verifyEmail(token)
    }
  }
  else navigate('/')

  // All pages are accessible without auth.
  // Data loading: if logged in, use full refreshData(); otherwise load public algorithms list.
  if (page.value === 'learning') {
    if (user.value) {
      if (!dataLoaded.value || !currentAlgorithm.value) refreshData()
      else currentAlgorithm.value = nextAlgorithm.value || algorithms.value[0] || null
    } else {
      // Anonymous: load algorithm list if not yet loaded, pick first
      if (!dataLoaded.value) loadPublicAlgorithms().then(() => {
        currentAlgorithm.value = algorithms.value[0] || null
      })
      else currentAlgorithm.value = algorithms.value[0] || null
    }
  }
  if (['algorithms', 'detail'].includes(page.value) && !dataLoaded.value) loadPublicAlgorithms()
}

async function refreshData() {
  if (!user.value) return
  loading.value = true
  try {
    const [list, overview, next] = await Promise.all([api('/algorithms'), api('/progress'), api('/algorithms/next')])
    algorithms.value = list
    progress.value = overview
    dataLoaded.value = true
    if (page.value === 'learning') currentAlgorithm.value = next.algorithm || null
  } catch (err) {
    if (String(err.message).includes('401')) logout(false)
    else error.value = err.message
  } finally {
    dataLoaded.value = true
    loading.value = false
  }
}

async function loadPublicAlgorithms() {
  if (dataLoaded.value) return
  loading.value = true
  try {
    algorithms.value = await api('/algorithms')
    dataLoaded.value = true
  } catch (err) { error.value = err.message }
  finally { loading.value = false }
}

async function loadAlgorithm(id) {
  loading.value = true
  try { currentAlgorithm.value = await api(`/algorithms/${id}`) }
  catch (err) { error.value = err.message; navigate('/algorithms') }
  finally { loading.value = false }
}

function setAuthMode(mode) {
  authMode.value = mode
  verificationSent.value = false
  showResendHint.value = false
}

async function submitAuth() {
  error.value = ''
  resendNotice.value = ''
  showResendHint.value = false
  loading.value = true
  try {
    const payload = authMode.value === 'register'
      ? { username: auth.value.username, email: auth.value.email, password: auth.value.password }
      : { email: auth.value.email, password: auth.value.password }
    const result = await api(`/auth/${authMode.value}`, { method: 'POST', body: JSON.stringify(payload) })
    if (authMode.value === 'register') {
      // Вход выполняется только после перехода по ссылке из письма.
      pendingEmail.value = result.user.email
      verificationSent.value = true
      notice.value = result.message
      return
    }
    user.value = result.user
    dataLoaded.value = false
    await refreshData()
    navigate('/learning')
  } catch (err) {
    error.value = err.message
    if (authMode.value === 'login' && String(err.message).includes('подтвержден')) showResendHint.value = true
  } finally { loading.value = false }
}

async function resendVerification(email) {
  resending.value = true
  resendNotice.value = ''
  error.value = ''
  try {
    const result = await api('/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) })
    resendNotice.value = result.message
  } catch (err) { error.value = err.message }
  finally { resending.value = false }
}

async function verifyEmail(token) {
  verificationState.value = 'verifying'
  try {
    const result = await api('/auth/verify', { method: 'POST', body: JSON.stringify({ token }) })
    user.value = result.user
    dataLoaded.value = false
    await refreshData()
    verificationState.value = 'success'
    notice.value = 'Почта подтверждена. Добро пожаловать в CubeLearn!'
    navigate('/learning')
  } catch (err) {
    verificationState.value = 'error'
    verificationMessage.value = err.message
  }
}

async function logout(request = true) {
  if (request) { try { await api('/auth/logout', { method: 'POST' }) } catch { /* local state is still cleared */ } }
  user.value = null; algorithms.value = []; progress.value = null; currentAlgorithm.value = null; dataLoaded.value = false
  navigate('/')
}

async function markLearned() {
  // Require login to write progress
  if (!user.value) {
    setAuthMode('register')
    notice.value = 'Зарегистрируйтесь, чтобы отмечать выученные алгоритмы.'
    navigate('/auth')
    return
  }
  if (!currentAlgorithm.value || currentAlgorithm.value.is_learned) return
  loading.value = true
  try {
    const result = await api(`/progress/complete/${currentAlgorithm.value.id}`, { method: 'POST' })
    notice.value = result.message
    await refreshData()
    currentAlgorithm.value = result.next_algorithm || currentAlgorithm.value
  } catch (err) { error.value = err.message }
  finally { loading.value = false }
}

function openLearning() {
  currentAlgorithm.value = nextAlgorithm.value || algorithms.value[0] || null
  navigate('/learning')
}

/**
 * Перехват кликов по внутренним ссылкам (<a href="/..."> и legacy <a href="#/...">),
 * чтобы навигация выполнялась через History API без полной перезагрузки страницы.
 * Якоря (#stages) и внешние ссылки обрабатываются браузером как обычно.
 */
function onDocumentClick(event) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  const link = event.target instanceof Element ? event.target.closest('a') : null
  if (!link || link.target === '_blank' || link.hasAttribute('download')) return
  const href = link.getAttribute('href') || ''
  let path = null
  if (href.startsWith('/')) path = href
  else if (href.startsWith('#/')) path = href.slice(1)
  else return
  event.preventDefault()
  navigate(path)
}

onMounted(async () => {
  document.addEventListener('click', onDocumentClick)
  window.addEventListener('popstate', consumeRoute)
  // Нормализуем legacy hash-URL (#/learning -> /learning) без перезагрузки
  if (window.location.hash.startsWith('#/')) history.replaceState({}, '', window.location.hash.slice(1))
  try { user.value = await api('/auth/me'); await refreshData() } catch { user.value = null }
  consumeRoute()
})
</script>

<template>
  <div>
    <div v-if="notice" class="toast toast--notice" @click="notice = ''">{{ notice }}</div>
    <div v-if="error" class="toast toast--error" @click="error = ''">{{ error }}</div>

    <!-- Landing page -->
    <Landing v-if="page === 'landing'" />

    <!-- Auth page -->
    <section v-else-if="page === 'auth'" class="auth-page">
      <div class="auth-card"><aside class="auth-aside"><a class="brand"><svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true"><polygon points="16 2.5 29 10 16 17.5 3 10" fill="#fbbf24"/><polygon points="3 10 16 17.5 16 30 3 22.5" fill="#ef4444"/><polygon points="29 10 16 17.5 16 30 29 22.5" fill="#3b82f6"/></svg>CubeLearn</a><div><h1>Стань мастером кубика Рубика</h1><p>Изучай OLL и PLL алгоритмы с профессиональными диаграммами и видеоуроками.</p></div></aside>
        <template v-if="verificationSent && authMode === 'register'">
          <form class="auth-form" @submit.prevent="resendVerification(pendingEmail)">
            <h2>Почти готово! Проверьте ящик 📬</h2>
            <p>Мы отправили письмо со ссылкой подтверждения на <strong>{{ pendingEmail }}</strong>. Откройте его и перейдите по ссылке — после этого вы сможете войти.</p>
            <p v-if="resendNotice">{{ resendNotice }}</p>
            <button class="button auth-submit" :disabled="resending">{{ resending ? 'Отправляем…' : 'Отправить письмо ещё раз' }}</button>
            <p><button type="button" class="text-button" @click="verificationSent = false"><AppIcon name="arrow-left" :size="14"/> Изменить данные регистрации</button></p><a href="/" class="back-link"><AppIcon name="arrow-left" :size="14"/> На главную</a>
          </form>
        </template>
        <form v-else class="auth-form" @submit.prevent="submitAuth"><div class="auth-tabs"><button type="button" :class="{active: authMode === 'login'}" @click="setAuthMode('login')">Войти</button><button type="button" :class="{active: authMode === 'register'}" @click="setAuthMode('register')">Регистрация</button></div><h2>{{ authMode === 'login' ? 'С возвращением!' : 'Создать аккаунт' }}</h2>
          <label v-if="authMode === 'register'">Имя пользователя<input v-model.trim="auth.username" minlength="3" maxlength="50" required placeholder="Alex Petrov" /></label>
          <label>Email<input v-model.trim="auth.email" type="email" required placeholder="alex@example.com" /></label>
          <label>Пароль<div class="password-field"><input v-model="auth.password" :type="showPassword ? 'text' : 'password'" minlength="8" required placeholder="Минимум 8 символов"/><button type="button" @click="showPassword = !showPassword">{{ showPassword ? 'Скрыть' : 'Показать' }}</button></div></label>
          <button class="button auth-submit" :disabled="loading">{{ loading ? 'Подождите…' : authMode === 'login' ? 'Войти в аккаунт' : 'Создать аккаунт' }}</button>
          <p v-if="showResendHint"><button type="button" class="text-button" @click="resendVerification(auth.email)">{{ resending ? 'Отправляем…' : 'Не пришло письмо? Отправить ещё раз' }}</button></p>
          <p v-if="resendNotice">{{ resendNotice }}</p>
          <p>{{ authMode === 'login' ? 'Нет аккаунта?' : 'Уже есть аккаунт?' }} <button type="button" class="text-button" @click="setAuthMode(authMode === 'login' ? 'register' : 'login')">{{ authMode === 'login' ? 'Зарегистрируйся' : 'Войди' }}</button></p><a href="/" class="back-link"><AppIcon name="arrow-left" :size="14"/> На главную</a>
        </form>
      </div>
    </section>

    <!-- Email verification -->
    <section v-else-if="page === 'verify'" class="auth-page">
      <div class="auth-card"><aside class="auth-aside"><a class="brand"><svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true"><polygon points="16 2.5 29 10 16 17.5 3 10" fill="#fbbf24"/><polygon points="3 10 16 17.5 16 30 3 22.5" fill="#ef4444"/><polygon points="29 10 16 17.5 16 30 29 22.5" fill="#3b82f6"/></svg>CubeLearn</a><div><h1>Подтверждение почты</h1><p>Проверяем вашу ссылку.</p></div></aside>
        <div class="auth-form">
          <template v-if="verificationState === 'verifying'">
            <h2>Подтверждаем почту…</h2>
            <p>Это займёт пару секунд.</p>
          </template>
          <template v-else-if="verificationState === 'success'">
            <h2><AppIcon name="check" :size="18"/> Почта подтверждена</h2>
            <p>Перенаправляем вас в обучение…</p>
          </template>
          <template v-else>
            <h2>Не удалось подтвердить почту</h2>
            <p>{{ verificationMessage || 'Ссылка недействительна или срок её действия истёк.' }}</p>
            <a href="/auth" class="button auth-submit">Войти или зарегистрироваться</a>
          </template>
        </div>
      </div>
    </section>

    <!-- App shell — ALL other pages, for both guests and logged-in users -->
    <div v-else class="app-shell">
      <aside class="sidebar">
        <a href="/learning" class="brand sidebar-brand"><svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true"><polygon points="16 2.5 29 10 16 17.5 3 10" fill="#fbbf24"/><polygon points="3 10 16 17.5 16 30 3 22.5" fill="#ef4444"/><polygon points="29 10 16 17.5 16 30 29 22.5" fill="#3b82f6"/></svg>CubeLearn</a>
        <nav class="side-nav">
          <a :class="{active: page === 'learning' || page === 'detail'}" href="/learning">⌑ <span>Обучение</span></a>
          <button @click="notice = 'Тренировка появится в следующей версии.'"><AppIcon name="timer" :size="18"/> <span>Тренировка</span></button>
          <a :class="{active: page === 'algorithms'}" href="/algorithms"><AppIcon name="grid" :size="18"/> <span>Алгоритмы</span></a>
          <a :class="{active: page === 'profile'}" href="/profile"><AppIcon name="user" :size="18"/> <span>Профиль</span></a>
          <button @click="notice = 'Настройки будут доступны в следующей версии.'"><AppIcon name="settings" :size="18"/> <span>Настройки</span></button>
        </nav>
        <div class="sidebar-user">
          <b>{{ initials }}</b>
          <span>{{ user ? user.username : 'Гость' }}</span>
        </div>
      </aside>
      <div class="workspace">
        <header class="topbar app-topbar">
          <a class="brand" href="/learning"><svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true"><polygon points="16 2.5 29 10 16 17.5 3 10" fill="#fbbf24"/><polygon points="3 10 16 17.5 16 30 3 22.5" fill="#ef4444"/><polygon points="29 10 16 17.5 16 30 29 22.5" fill="#3b82f6"/></svg>CubeLearn</a>
          <div v-if="user">
            <a href="/profile" class="avatar">{{ initials }}</a>
            <button class="button button--dark" @click="logout()"><AppIcon name="log-out" :size="15"/> Выйти</button>
          </div>
          <div v-else>
            <a href="/auth" class="button button--outline">Войти</a>
            <a href="/auth" class="button" @click="setAuthMode('register')">Регистрация</a>
          </div>
        </header>
        <main class="app-main">

          <!-- Learning page -->
          <section v-if="page === 'learning'" class="page-container">
            <div v-if="loading || !dataLoaded" class="empty"><h1>Загружаем алгоритмы…</h1><p>Получаем алгоритмы для изучения.</p></div>
            <div v-else-if="!algorithms.length" class="empty"><h1>Каталог пока пуст</h1><p>В базе нет алгоритмов. Запустите seed-парсер бэкенда и обновите страницу.</p><a href="/algorithms" class="button">Открыть каталог</a></div>
            <div v-else-if="!currentAlgorithm" class="empty"><h1>Все алгоритмы изучены! 🎉</h1><p>Отличная работа — загляните в каталог для повторения.</p><a href="/algorithms" class="button">Каталог алгоритмов</a></div>
            <AlgorithmDetail v-else :algorithm="currentAlgorithm" :stats="stats" :loading="loading" @complete="markLearned" @next="openLearning" @catalog="navigate('/algorithms')" />
          </section>

          <!-- Algorithms catalog -->
          <section v-else-if="page === 'algorithms'" class="page-container">
            <div class="page-heading">
              <div><h1>Алгоритмы</h1><p>Выбери случай и изучай его в удобном темпе.</p></div>
              <button class="button" @click="openLearning">Продолжить обучение <AppIcon name="arrow-right" :size="15"/></button>
            </div>
            <div class="catalog-controls"><div class="segmented"><button :class="{active: filter === 'OLL'}" @click="filter = 'OLL'">OLL</button><button :class="{active: filter === 'PLL'}" @click="filter = 'PLL'">PLL</button></div><input v-model="search" placeholder="Поиск алгоритма…" /></div>
            <div v-if="loading" class="empty">Загрузка…</div>
            <div v-else class="algorithm-grid"><button v-for="algorithm in filteredAlgorithms" :key="algorithm.id" class="algorithm-card" :class="algorithm.category.toLowerCase()" @click="navigate(`/algorithms/${algorithm.id}`)"><span class="learned-mark" :class="{learned: algorithm.is_learned}"><AppIcon v-if="algorithm.is_learned" name="check" :size="12"/> {{ algorithm.is_learned ? 'Изучен' : `${algorithm.category} #${algorithm.algorithm_number}` }}</span><CubeDiagram :algorithm="algorithm"/><h3>{{ algorithm.name }}</h3><code>{{ algorithm.formula }}</code></button></div>
            <div v-if="!loading && !filteredAlgorithms.length" class="empty">Алгоритмы не найдены.</div>
          </section>

          <!-- Algorithm detail -->
          <section v-else-if="page === 'detail'" class="page-container">
            <div v-if="loading" class="empty">Загрузка…</div>
            <AlgorithmDetail v-else-if="currentAlgorithm" :algorithm="currentAlgorithm" :stats="stats" :loading="loading" @complete="markLearned" @next="openLearning" @catalog="navigate('/algorithms')" />
            <div v-else class="empty">Алгоритм не найден.</div>
          </section>

          <!-- Profile page -->
          <section v-else-if="page === 'profile'" class="page-container profile profile-design">
            <!-- Guest profile: CTA to register -->
            <div v-if="!user" class="guest-profile-cta">
              <div class="guest-profile-icon"><AppIcon name="user" :size="34"/></div>
              <h1>Вы просматриваете как гость</h1>
              <p>Зарегистрируйтесь, чтобы отслеживать прогресс, зарабатывать достижения и сохранять изученные алгоритмы.</p>
              <div class="guest-profile-actions">
                <a href="/auth" class="button button--large" @click="setAuthMode('register')">Создать аккаунт <AppIcon name="arrow-right" :size="15"/></a>
                <a href="/auth" class="button button--outline button--large">Уже есть аккаунт? Войти</a>
              </div>
              <div class="guest-features">
                <div class="guest-feature"><span>📊</span><b>Прогресс</b><small>Отмечай выученные алгоритмы</small></div>
                <div class="guest-feature"><span>🔥</span><b>Стрик</b><small>Ежедневные занятия</small></div>
                <div class="guest-feature"><span>🏅</span><b>Достижения</b><small>Разблокируй награды</small></div>
              </div>
            </div>
            <!-- Authenticated profile -->
            <template v-else>
              <div class="profile-card design-profile-card">
                <div class="profile-avatar">{{ initials }}</div>
                <div class="profile-name">
                  <h1>{{ user?.username }}</h1>
                  <p>Спидкубер · с нами с {{ user?.created_at ? new Date(user.created_at).toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' }) : 'сегодня' }}</p>
                  <div class="progress-pairs"><ProgressBar label="OLL" :done="stats.oll_learned" :total="stats.oll_total" color="yellow"/><ProgressBar label="PLL" :done="stats.pll_learned" :total="stats.pll_total" color="blue"/></div>
                </div>
                <div class="streak-card"><span>🔥</span><b>{{ streak }}</b><small>дней подряд</small></div>
              </div>
              <section class="activity-card panel">
                <h2>Активность (последние 14 дней)</h2>
                <div class="activity-days"><span v-for="(day, index) in activityDays" :key="index" :class="{ active: day.active }" :title="`${day.dateStr}: ${day.active ? 'Были занятия' : 'Пропуск'}`"><AppIcon v-if="day.active" name="check" :size="13"/></span><div class="activity-legend"><i/> занятие <i class="muted"/> пропуск</div></div>
              </section>
              <section class="achievements-section panel">
                <h2 class="achievements-title">🏅 Достижения</h2>
                <div class="achievement-grid">
                  <div class="achievement" :class="{unlocked: stats.learned_total >= 1}">🔥 <span><b>Первый алгоритм</b><small>Изучи свой первый алгоритм</small><em v-if="stats.learned_total >= 1"><AppIcon name="check" :size="12"/> Получено</em></span></div>
                  <div class="achievement" :class="{unlocked: stats.learned_total >= 5}">⚡ <span><b>Быстрый старт</b><small>Изучи 5 алгоритмов</small><em v-if="stats.learned_total >= 5"><AppIcon name="check" :size="12"/> Получено</em></span></div>
                  <div class="achievement" :class="{unlocked: stats.learned_total >= 10}">📚 <span><b>Усердный ученик</b><small>Изучи 10 алгоритмов</small><em v-if="stats.learned_total >= 10"><AppIcon name="check" :size="12"/> Получено</em></span></div>
                  <div class="achievement" :class="{unlocked: stats.oll_total && stats.oll_learned === stats.oll_total}">🏆 <span><b>Мастер OLL</b><small>Изучи все OLL случаи</small><em v-if="stats.oll_total && stats.oll_learned === stats.oll_total"><AppIcon name="check" :size="12"/> Получено</em></span></div>
                  <div class="achievement" :class="{unlocked: stats.pll_total && stats.pll_learned === stats.pll_total}">💎 <span><b>Чемпион PLL</b><small>Изучи все PLL случаи</small><em v-if="stats.pll_total && stats.pll_learned === stats.pll_total"><AppIcon name="check" :size="12"/> Получено</em></span></div>
                  <div class="achievement" :class="{unlocked: streak >= 30}">🌟 <span><b>30-дневный стрик</b><small>Занимайся 30 дней подряд</small><em v-if="streak >= 30"><AppIcon name="check" :size="12"/> Получено</em></span></div>
                </div>
              </section>
            </template>
          </section>

        </main>
      </div>
    </div>
  </div>
</template>

<script>
import situations from './situations.json'

const STICKER_COLORS = Object.freeze({
  Y: '#FFFF00',
  N: '#8D8D8D',
  G: '#11AA00',
  R: '#D00000',
  B: '#2040D0',
  O: '#EE8800',
})

const ICONS = {
  book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  timer: '<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  settings: '<line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="2" x2="6" y1="14" y2="14"/><line x1="10" x2="14" y1="8" y2="8"/><line x1="18" x2="22" y1="16" y2="16"/>',
  bulb: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  gem: '<path d="M6 3h12l4 6-10 13L2 9Z"/><path d="M11 3 8 9l4 13 4-13-3-6"/><path d="M2 9h20"/>',
  star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  chart: '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
  award: '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  'arrow-right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  'arrow-left': '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
}

const AppIcon = {
  props: { name: { type: String, required: true }, size: { type: [Number, String], default: 18 } },
  computed: { html() { return ICONS[this.name] || '' } },
  template: '<svg class="icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="html"></svg>',
}
const CubeDiagram = {
  props: ['algorithm'],
  computed: {
    state() {
      const number = String(this.algorithm.algorithm_number).padStart(2, '0')
      return situations[`${this.algorithm.category.toLowerCase()}-${number}`]
    },
  },
  methods: {
    color(value) { return STICKER_COLORS[value] || STICKER_COLORS.N },
    column(index) { return 106 + (index % 3) * 136 },
    row(index) { return 86 + Math.floor(index / 3) * 136 },
    sideRow(index) { return 86 + index * 136 },
  },
  template: `<svg v-if="state" class="cube-diagram" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 637 563" role="img" :aria-label="algorithm.name">
    <rect x="99" y="21" width="409" height="59" fill="#000"/>
    <rect x="41" y="79" width="525" height="409" fill="#000"/>
    <rect x="99" y="488" width="409" height="59" fill="#000"/>
    <rect v-for="(value, index) in state.U" :key="'u' + index" :x="column(index)" :y="row(index)" width="123" height="123" rx="16" ry="16" :fill="color(value)"/>
    <rect v-for="(value, index) in state.B" :key="'b' + index" :x="column(index)" y="28" width="123" height="45" rx="8" ry="8" :fill="color(value)"/>
    <rect v-for="(value, index) in state.F" :key="'f' + index" :x="column(index)" y="494" width="123" height="45" rx="8" ry="8" :fill="color(value)"/>
    <rect v-for="(value, index) in state.L" :key="'l' + index" x="48" :y="sideRow(index)" width="45" height="123" rx="8" ry="8" :fill="color(value)"/>
    <rect v-for="(value, index) in state.R" :key="'r' + index" x="514" :y="sideRow(index)" width="45" height="123" rx="8" ry="8" :fill="color(value)"/>
  </svg>`,
}

const ProgressBar = {
  props: ['label', 'done', 'total', 'color'],
  computed: { percentage() { return this.total ? (this.done / this.total) * 100 : 0 } },
  template: `<div class="progress-pair"><div><b>{{ label }}</b><span>{{ done }}/{{ total }}</span></div><div class="progress-track"><i :class="color" :style="{ width: percentage + '%' }"/></div></div>`,
}

const AlgorithmDetail = {
  components: { ProgressBar, CubeDiagram, AppIcon },
  props: ['algorithm', 'stats', 'loading'],
  emits: ['complete', 'next', 'catalog'],
  computed: {
    isOll() { return this.algorithm.category === 'OLL' },
    embedUrl() {
      const videoUrl = this.algorithm?.video_url
      if (!videoUrl) return null
      try {
        const url = new URL(videoUrl)
        const host = url.hostname.replace(/^www\./, '').toLowerCase()
        const pathParts = url.pathname.split('/').filter(Boolean)
        let videoId = null
        if (host === 'youtu.be') videoId = pathParts[0]
        else if (host === 'youtube.com' || host.endsWith('.youtube.com')) {
          if (pathParts[0] === 'watch') videoId = url.searchParams.get('v')
          else if (['embed', 'shorts', 'live'].includes(pathParts[0])) videoId = pathParts[1]
        }
        return /^[\w-]{11}$/.test(videoId || '')
          ? `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`
          : null
      } catch { return null }
    },
  },
  template: `<div class="detail"><div class="detail-heading"><div><button class="back-link" @click="$emit('catalog')"><AppIcon name="arrow-left" :size="14"/> К каталогу</button><h1>{{ algorithm.category }} #{{ algorithm.algorithm_number }} — {{ algorithm.name }}</h1><p>{{ stats.learned_total }} из {{ stats.total_algorithms }} изучено</p></div><button class="button button--dark" @click="$emit('next')">Следующий <AppIcon name="arrow-right" :size="15"/></button></div><div class="detail-progress"><i :style="{ width: stats.overall_percentage + '%' }"/></div><div class="detail-grid"><section><div class="diagram-card" :class="isOll ? 'oll' : 'pll'"><CubeDiagram :algorithm="algorithm"/><span>{{ algorithm.category }} · вид сверху</span></div><div class="formula-card"><small>АЛГОРИТМ</small><div><code v-for="(move, index) in algorithm.formula.split(' ')" :key="index">{{ move }}</code></div><button v-if="!algorithm.is_learned" class="master-button" :disabled="loading" @click="$emit('complete')"><AppIcon v-if="!loading" name="check" :size="16"/> {{ loading ? 'Сохраняем…' : 'Отметить как выученный' }}</button><p v-else class="mastered"><AppIcon name="check" :size="15"/> Алгоритм изучен</p></div></section><section><div class="video-card"><iframe v-if="embedUrl" class="video-player" :src="embedUrl" :title="algorithm.name + ' — видеоурок'" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"/><a v-else-if="algorithm.video_url" :href="algorithm.video_url" target="_blank" rel="noreferrer" class="video-link"><span class="video-glyph"><AppIcon name="play" :size="20"/></span><b>{{ algorithm.name }} — видеоурок</b><small>Открыть видео</small></a><div v-else class="video-placeholder"><span class="video-glyph"><AppIcon name="play" :size="20"/></span><b>{{ algorithm.name }} — видеоурок</b><small>Видео будет добавлено позже</small></div></div><div class="tips"><h2>💡 Советы по запоминанию</h2><p>🎯 Разбей алгоритм на блоки по 3–4 хода.</p><p>🔁 Повтори 10 раз медленно, затем ускоряйся.</p><p>👁️ Запомни визуальный паттерн случая.</p></div></section></div></div>`,
}

export default { components: { AlgorithmDetail, CubeDiagram, ProgressBar, AppIcon } }
</script>
