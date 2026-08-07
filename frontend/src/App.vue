<script setup>
import { computed, onMounted, ref } from 'vue'

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
const filter = ref('OLL')
const search = ref('')
const showPassword = ref(false)
const auth = ref({ username: '', email: '', password: '' })
const heroColors = ['red', 'yellow', 'red', 'blue', 'yellow', 'green', 'orange', 'blue', 'green']
const profileTab = ref('achievements')
const activityDays = [true, true, false, true, true, true, true, true, false, true, true, true, true, false]
const friends = [
  { name: 'Mikhail K.', initials: 'MK', color: '#003DAA', streak: 14, oll: 32, pll: 12 },
  { name: 'Sofia L.', initials: 'SL', color: '#C41E3A', streak: 7, oll: 57, pll: 19 },
  { name: 'Dmitri V.', initials: 'DV', color: '#009B48', streak: 3, oll: 10, pll: 5 },
]

const api = async (url, options = {}) => {
  const response = await fetch(`/api${url}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (response.status === 204) return null
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Не удалось выполнить запрос.')
  return body
}

const route = () => window.location.hash.replace(/^#/, '') || '/'
const navigate = (path) => { window.location.hash = path }
const initials = computed(() => user.value?.username?.slice(0, 2).toUpperCase() || 'CL')
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
  while (learnedDates.has(date.toDateString())) {
    count += 1
    date.setDate(date.getDate() - 1)
  }
  return count
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
  else navigate('/')

  if (['learning', 'algorithms', 'detail', 'profile'].includes(page.value) && !user.value) {
    notice.value = 'Войдите, чтобы открыть обучение.'
    navigate('/auth')
  }
  if (page.value === 'learning' && user.value) {
    if (!dataLoaded.value || !currentAlgorithm.value) refreshData()
    else currentAlgorithm.value = nextAlgorithm.value || algorithms.value[0] || null
  }
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

async function loadAlgorithm(id) {
  if (!user.value) return
  loading.value = true
  try { currentAlgorithm.value = await api(`/algorithms/${id}`) }
  catch (err) { error.value = err.message; navigate('/algorithms') }
  finally { loading.value = false }
}

async function submitAuth() {
  error.value = ''
  loading.value = true
  try {
    const payload = authMode.value === 'register'
      ? { username: auth.value.username, email: auth.value.email, password: auth.value.password }
      : { email: auth.value.email, password: auth.value.password }
    const result = await api(`/auth/${authMode.value === 'register' ? 'register' : 'login'}`, { method: 'POST', body: JSON.stringify(payload) })
    user.value = result.user
    await refreshData()
    navigate('/learning')
  } catch (err) { error.value = err.message }
  finally { loading.value = false }
}

async function logout(request = true) {
  if (request) { try { await api('/auth/logout', { method: 'POST' }) } catch { /* local state is still cleared */ } }
  user.value = null; algorithms.value = []; progress.value = null; currentAlgorithm.value = null; dataLoaded.value = false
  navigate('/')
}

async function markLearned() {
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

onMounted(async () => {
  window.addEventListener('hashchange', consumeRoute)
  try { user.value = await api('/auth/me'); await refreshData() } catch { user.value = null }
  consumeRoute()
})
</script>

<template>
  <div>
    <div v-if="notice" class="toast toast--notice" @click="notice = ''">{{ notice }}</div>
    <div v-if="error" class="toast toast--error" @click="error = ''">{{ error }}</div>

    <template v-if="page === 'landing'">
      <header class="topbar landing-topbar">
        <a class="brand" href="#/"><span class="cube-logo"><i/><i/><i/><i/><i/><i/></span>CubeLearn</a>
        <nav><a href="#/algorithms">Алгоритмы</a><a href="#/auth" class="button button--outline">Войти</a><a href="#/auth" class="button">Начать →</a></nav>
      </header>
      <main class="landing">
        <section class="hero">
          <div>
            <span class="eyebrow">🏆 OLL &amp; PLL мастер-класс</span>
            <h1>Собирай <em>кубик</em> <strong>Рубика</strong> как профи</h1>
            <p>Изучай OLL и PLL алгоритмы с визуальными диаграммами, видеоуроками и системой отслеживания прогресса.</p>
            <div class="hero-actions"><a href="#/auth" class="button button--large">Начать бесплатно →</a><a href="#/auth" class="button button--muted button--large">Смотреть демо</a></div>
          </div>
          <div class="hero-cube-wrap"><div class="hero-cube"> <i v-for="(color, index) in heroColors" :key="index" :class="color"/></div><b class="cube-note cube-note--top">PLL ready ✓</b><b class="cube-note cube-note--bottom">OLL ×57</b></div>
        </section>
        <section class="stat-banner"><div><b>57</b><span>OLL случаев</span></div><div><b>21</b><span>PLL случаев</span></div><div><b>10K+</b><span>учеников</span></div><div><b>98%</b><span>довольны</span></div></section>
        <section class="marketing-section"><h2>Всё, что нужно для мастерства</h2><div class="feature-grid">
          <article class="feature yellow"><span/> <h3>57 OLL алгоритмов</h3><p>Все случаи ориентации последнего слоя с визуальными диаграммами и пошаговым разбором.</p></article>
          <article class="feature blue"><span/> <h3>21 PLL алгоритм</h3><p>Каждая перестановка последнего слоя с понятной формулой и видеоразбором.</p></article>
          <article class="feature red"><span/> <h3>Дневной стрик</h3><p>Отслеживай прогресс и зарабатывай достижения.</p></article>
          <article class="feature green"><span/> <h3>Структурное обучение</h3><p>Алгоритмы идут по порядку: от первых шагов до уверенного CFOP.</p></article>
        </div></section>
        <section class="how"><h2>Как это работает</h2><div class="steps"><article><b>01</b><h3>Зарегистрируйся</h3><p>Создай аккаунт за 30 секунд</p></article><article><b>02</b><h3>Выбери алгоритм</h3><p>OLL или PLL — начни с простых</p></article><article><b>03</b><h3>Тренируйся</h3><p>Диаграмма, видео и практика</p></article></div></section>
        <section class="cta"><h2>Готов стать мастером?</h2><p>Присоединяйся к спидкуберам, которые уже изучают OLL и PLL.</p><a href="#/auth" class="button button--large">Начать бесплатно →</a></section>
      </main>
      <footer>© 2026 CubeLearn. Все права защищены.</footer>
    </template>

    <section v-else-if="page === 'auth'" class="auth-page">
      <div class="auth-card"><aside class="auth-aside"><a class="brand"><span class="cube-logo"><i/><i/><i/><i/><i/><i/></span>CubeLearn</a><div><h1>Стань мастером кубика Рубика</h1><p>Изучай OLL и PLL алгоритмы с профессиональными диаграммами и видеоуроками.</p></div><div class="tiny-cube"><i v-for="n in 9" :key="n"/></div></aside>
        <form class="auth-form" @submit.prevent="submitAuth"><div class="auth-tabs"><button type="button" :class="{active: authMode === 'login'}" @click="authMode = 'login'">Войти</button><button type="button" :class="{active: authMode === 'register'}" @click="authMode = 'register'">Регистрация</button></div><h2>{{ authMode === 'login' ? 'С возвращением!' : 'Создать аккаунт' }}</h2>
          <label v-if="authMode === 'register'">Имя пользователя<input v-model.trim="auth.username" minlength="3" maxlength="50" required placeholder="Alex Petrov" /></label>
          <label>Email<input v-model.trim="auth.email" type="email" required placeholder="alex@example.com" /></label>
          <label>Пароль<div class="password-field"><input v-model="auth.password" :type="showPassword ? 'text' : 'password'" minlength="8" required placeholder="Минимум 8 символов"/><button type="button" @click="showPassword = !showPassword">{{ showPassword ? 'Скрыть' : 'Показать' }}</button></div></label>
          <button class="button auth-submit" :disabled="loading">{{ loading ? 'Подождите…' : authMode === 'login' ? 'Войти в аккаунт' : 'Создать аккаунт' }}</button>
          <p>{{ authMode === 'login' ? 'Нет аккаунта?' : 'Уже есть аккаунт?' }} <button type="button" class="text-button" @click="authMode = authMode === 'login' ? 'register' : 'login'">{{ authMode === 'login' ? 'Зарегистрируйся' : 'Войди' }}</button></p><a href="#/" class="back-link">← На главную</a>
        </form>
      </div>
    </section>

    <div v-else class="app-shell">
      <aside class="sidebar"><a href="#/learning" class="brand sidebar-brand"><span class="cube-logo"><i/><i/><i/><i/><i/><i/></span>CubeLearn</a><nav class="side-nav"><a :class="{active: page === 'learning' || page === 'detail'}" href="#/learning">⌑ <span>Обучение</span></a><button @click="notice = 'Тренировка появится в следующей версии.'">◷ <span>Тренировка</span></button><a :class="{active: page === 'algorithms'}" href="#/algorithms">▦ <span>Алгоритмы</span></a><a :class="{active: page === 'profile'}" href="#/profile">♙ <span>Профиль</span></a><button @click="notice = 'Настройки будут доступны в следующей версии.'">⚙ <span>Настройки</span></button></nav><div class="sidebar-user"><b>{{ initials }}</b><span>{{ user?.username }}</span></div></aside>
      <div class="workspace"><header class="topbar app-topbar"><a class="brand" href="#/learning"><span class="cube-logo"><i/><i/><i/><i/><i/><i/></span>CubeLearn</a><div><a href="#/profile" class="avatar">{{ initials }}</a><button class="button button--dark" @click="logout()">Выйти</button></div></header>
        <main class="app-main">
          <section v-if="page === 'learning'" class="page-container">
            <div v-if="loading || !dataLoaded" class="empty"><h1>Загружаем алгоритмы…</h1><p>Получаем ваш прогресс и следующий алгоритм.</p></div>
            <div v-else-if="!algorithms.length" class="empty"><h1>Каталог пока пуст</h1><p>В базе нет алгоритмов. Запустите seed-парсер бэкенда и обновите страницу.</p><a href="#/algorithms" class="button">Открыть каталог</a></div>
            <div v-else-if="!currentAlgorithm" class="empty"><h1>Все алгоритмы изучены! 🎉</h1><p>Отличная работа — загляните в каталог для повторения.</p><a href="#/algorithms" class="button">Каталог алгоритмов</a></div>
            <AlgorithmDetail v-else :algorithm="currentAlgorithm" :stats="stats" :loading="loading" @complete="markLearned" @next="openLearning" @catalog="navigate('/algorithms')" />
          </section>
          <section v-else-if="page === 'algorithms'" class="page-container"><div class="page-heading"><div><h1>Алгоритмы</h1><p>Выбери случай и изучай его в удобном темпе.</p></div><button class="button" @click="openLearning">Продолжить обучение →</button></div><div class="catalog-controls"><div class="segmented"><button :class="{active: filter === 'OLL'}" @click="filter = 'OLL'">OLL</button><button :class="{active: filter === 'PLL'}" @click="filter = 'PLL'">PLL</button></div><input v-model="search" placeholder="Поиск алгоритма…" /></div><div v-if="loading" class="empty">Загрузка…</div><div v-else class="algorithm-grid"><button v-for="algorithm in filteredAlgorithms" :key="algorithm.id" class="algorithm-card" :class="algorithm.category.toLowerCase()" @click="navigate(`/algorithms/${algorithm.id}`)"><span class="learned-mark" :class="{learned: algorithm.is_learned}">{{ algorithm.is_learned ? '✓ Изучен' : `${algorithm.category} #${algorithm.algorithm_number}` }}</span><img :src="algorithm.image_url" :alt="algorithm.name" /><h3>{{ algorithm.name }}</h3><code>{{ algorithm.formula }}</code></button></div><div v-if="!loading && !filteredAlgorithms.length" class="empty">Алгоритмы не найдены.</div></section>
          <section v-else-if="page === 'detail'" class="page-container"><div v-if="loading" class="empty">Загрузка…</div><AlgorithmDetail v-else-if="currentAlgorithm" :algorithm="currentAlgorithm" :stats="stats" :loading="loading" @complete="markLearned" @next="openLearning" @catalog="navigate('/algorithms')" /><div v-else class="empty">Алгоритм не найден.</div></section>
          <section v-else-if="page === 'profile'" class="page-container profile profile-design">
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
              <div class="activity-days"><span v-for="(active, index) in activityDays" :key="index" :class="{ active }">{{ active ? '✓' : '' }}</span><div class="activity-legend"><i/> занятие <i class="muted"/> пропуск</div></div>
            </section>
            <div class="profile-tabs"><button :class="{active: profileTab === 'achievements'}" @click="profileTab = 'achievements'">🏅 Достижения</button><button :class="{active: profileTab === 'friends'}" @click="profileTab = 'friends'">👥 Друзья</button></div>
            <div v-if="profileTab === 'achievements'" class="achievement-grid">
              <div class="achievement" :class="{unlocked: stats.learned_total >= 1}">🔥 <span><b>Первый алгоритм</b><small>Изучи свой первый алгоритм</small><em v-if="stats.learned_total >= 1">✓ Получено</em></span></div>
              <div class="achievement" :class="{unlocked: stats.learned_total >= 5}">⚡ <span><b>Быстрый старт</b><small>Изучи 5 алгоритмов</small><em v-if="stats.learned_total >= 5">✓ Получено</em></span></div>
              <div class="achievement" :class="{unlocked: stats.learned_total >= 10}">📚 <span><b>Усердный ученик</b><small>Изучи 10 алгоритмов</small></span></div>
              <div class="achievement" :class="{unlocked: stats.oll_total && stats.oll_learned === stats.oll_total}">🏆 <span><b>Мастер OLL</b><small>Изучи все OLL случаи</small></span></div>
              <div class="achievement" :class="{unlocked: stats.pll_total && stats.pll_learned === stats.pll_total}">💎 <span><b>Чемпион PLL</b><small>Изучи все PLL случаи</small></span></div>
              <div class="achievement">🌟 <span><b>30-дневный стрик</b><small>Занимайся 30 дней подряд</small></span></div>
            </div>
            <div v-else class="friends-list">
              <article v-for="friend in friends" :key="friend.name"><b class="friend-avatar" :style="{ background: friend.color }">{{ friend.initials }}</b><div><strong>{{ friend.name }}</strong><span>OLL: {{ friend.oll }}/57 · PLL: {{ friend.pll }}/21</span></div><p>🔥 <b>{{ friend.streak }}</b><small>стрик</small></p></article>
              <button class="add-friend">+ Добавить друга</button>
            </div>
          </section>
        </main>
      </div>
    </div>
  </div>
</template>

<script>
const ProgressBar = {
  props: ['label', 'done', 'total', 'color'],
  computed: { percentage() { return this.total ? (this.done / this.total) * 100 : 0 } },
  template: `<div class="progress-pair"><div><b>{{ label }}</b><span>{{ done }}/{{ total }}</span></div><div class="progress-track"><i :class="color" :style="{ width: percentage + '%' }"/></div></div>`,
}

const AlgorithmDetail = {
  components: { ProgressBar },
  props: ['algorithm', 'stats', 'loading'],
  emits: ['complete', 'next', 'catalog'],
  computed: { isOll() { return this.algorithm.category === 'OLL' } },
  template: `<div class="detail"><div class="detail-heading"><div><button class="back-link" @click="$emit('catalog')">← К каталогу</button><h1>{{ algorithm.category }} #{{ algorithm.algorithm_number }} — {{ algorithm.name }}</h1><p>{{ stats.learned_total }} из {{ stats.total_algorithms }} изучено</p></div><button class="button button--dark" @click="$emit('next')">Следующий →</button></div><div class="detail-progress"><i :style="{ width: stats.overall_percentage + '%' }"/></div><div class="detail-grid"><section><div class="diagram-card" :class="isOll ? 'oll' : 'pll'"><img :src="algorithm.image_url" :alt="algorithm.name"/><span>{{ algorithm.category }} · вид сверху</span></div><div class="formula-card"><small>АЛГОРИТМ</small><div><code v-for="(move, index) in algorithm.formula.split(' ')" :key="index">{{ move }}</code></div><button v-if="!algorithm.is_learned" class="master-button" :disabled="loading" @click="$emit('complete')">{{ loading ? 'Сохраняем…' : '✓ Отметить как выученный' }}</button><p v-else class="mastered">✓ Алгоритм изучен</p></div></section><section><div class="video-card"><a v-if="algorithm.video_url" :href="algorithm.video_url" target="_blank" rel="noreferrer" class="video-link"><span>▶</span><b>{{ algorithm.name }} — видеоурок</b><small>Открыть видео</small></a><div v-else class="video-placeholder"><span>▶</span><b>{{ algorithm.name }} — видеоурок</b><small>Видео будет добавлено позже</small></div></div><div class="tips"><h2>💡 Советы по запоминанию</h2><p>🎯 Разбей алгоритм на блоки по 3–4 хода.</p><p>🔁 Повтори 10 раз медленно, затем ускоряйся.</p><p>👁️ Запомни визуальный паттерн случая.</p></div></section></div></div>`,
}

export default { components: { AlgorithmDetail, ProgressBar } }
</script>
