import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import assert from 'node:assert/strict'

const projectRoot = new URL('../', import.meta.url)

async function readProjectFile(path) {
  return readFile(new URL(path, projectRoot), 'utf8')
}

test('production build emits the application shell', async () => {
  const html = await readProjectFile('dist/index.html')

  assert.match(html, /<div id="app"><\/div>/)
  assert.match(html, /type="module" crossorigin src="\/assets\/index-[^"]+\.js"/)
  assert.match(html, /rel="stylesheet" crossorigin href="\/assets\/index-[^"]+\.css"/)
})

test('workspace source keeps the primary surfaces wired', async () => {
  const app = await readProjectFile('src/App.vue')

  assert.match(app, /<WorkspaceTabs/)
  assert.match(app, /<ImageGenerationForm/)
  assert.match(app, /<TaskCenter/)
  assert.match(app, /<HistoryGallery/)
  assert.match(app, /<ConfirmDialog/)
  assert.match(app, /<ToastStack/)
  assert.match(app, /@delete="confirmDeleteJob"/)
  assert.match(app, /@delete-images="confirmDeleteImages"/)
})

test('generation form exposes dynamic model and parameter controls', async () => {
  const form = await readProjectFile('src/components/ImageGenerationForm.vue')

  assert.match(form, /v-model="form\.model"/)
  assert.match(form, /v-for="model in modelOptions"/)
  assert.match(form, /v-model="form\.size"/)
  assert.match(form, /v-model="form\.quality"/)
  assert.match(form, /v-model="form\.background"/)
  assert.match(form, /v-model="form\.inputFidelity"/)
})

test('destructive actions are guarded by confirmation copy', async () => {
  const app = await readProjectFile('src/App.vue')

  assert.match(app, /confirmDeleteImages/)
  assert.match(app, /confirmDeleteJob/)
  assert.match(app, /确认删除/)
  assert.match(app, /删除后会从当前列表隐藏/)
})

test('history filters keep advanced controls collapsible', async () => {
  const history = await readProjectFile('src/components/HistoryGallery.vue')

  assert.match(history, /showAdvancedFilters/)
  assert.match(history, /更多筛选/)
  assert.match(history, /清空筛选/)
  assert.match(history, /history-filter-chips/)
})

test('frontend has a real browser smoke test entrypoint', async () => {
  const packageJson = await readProjectFile('package.json')
  const config = await readProjectFile('playwright.config.ts')
  const spec = await readProjectFile('tests/app.e2e.spec.ts')

  assert.match(packageJson, /"test:e2e"/)
  assert.match(config, /@playwright\/test/)
  assert.match(spec, /top navigation stays usable while scrolling/)
  assert.match(spec, /recent generation task exposes guarded delete/)
})

test('deploy script retries health checks during container startup', async () => {
  const script = await readProjectFile('../scripts/deploy-server.sh')

  assert.match(script, /wait_for_http/)
  assert.match(script, /HEALTH_RETRIES/)
  assert.match(script, /Health check passed/)
})
