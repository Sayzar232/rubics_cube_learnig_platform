import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const __dirname = dirname(fileURLToPath(import.meta.url))

/**
 * Подставляет статическую разметку лендинга (src/landing-body.html) в index.html
 * вместо плейсхолдера <!--LANDING_CONTENT-->, чтобы поисковые роботы видели
 * контент без исполнения JS. При монтировании Vue заменяет контент разметкой Landing.vue.
 */
function injectLanding() {
  return {
    name: 'inject-landing',
    transformIndexHtml(html) {
      const landing = readFileSync(join(__dirname, 'src', 'landing-body.html'), 'utf8').replace(/^\uFEFF/, '')
      return html.replace('<!--LANDING_CONTENT-->', () => landing)
    },
  }
}

/**
 * Кладёт данные диаграмм в сборку: dist/data/situations.json.
 * Бэкенд рендерит те же SVG на сервере (backend/app/services/diagram_service.py),
 * а в Docker-образ попадает только frontend/dist, без frontend/src.
 */
function emitSituations() {
  return {
    name: 'emit-situations',
    generateBundle() {
      const source = readFileSync(join(__dirname, 'src', 'situations.json'), 'utf8').replace(/^\uFEFF/, '')
      this.emitFile({ type: 'asset', fileName: 'data/situations.json', source })
    },
  }
}

export default defineConfig({
  plugins: [vue(), injectLanding(), emitSituations()],
  resolve: {
    alias: {
      vue: 'vue/dist/vue.esm-bundler.js',
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
