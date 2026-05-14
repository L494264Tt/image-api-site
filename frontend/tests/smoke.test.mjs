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
  assert.match(app, /@delete="handleDeleteJob"/)
  assert.match(app, /@delete-images="handleDeleteImages"/)
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
