import { expect, test } from '@playwright/test'

async function mockSignedInApp(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('image-api-site-access-token', 'e2e-token')
  })

  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok' } })
  })
  await page.route('**/api/config', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Canvas Relay',
        model_options: ['gpt-image-2'],
        default_model: 'gpt-image-2',
        size_options: ['auto', '1024x1024'],
        quality_options: ['auto', 'high'],
        style_options: ['vivid', 'natural'],
        background_options: ['auto', 'transparent'],
        input_fidelity_options: ['auto', 'high'],
        max_images: 1,
        model_capabilities: [
          {
            id: 'gpt-image-2',
            label: 'gpt-image-2',
            sizes: ['auto', '1024x1024'],
            qualities: ['auto', 'high'],
            backgrounds: ['auto', 'transparent'],
            supports_text_to_image: true,
            supports_image_to_image: true,
            supports_image_input: true,
            default_endpoint: 'responses',
            input_fidelities: ['auto', 'high'],
            supports_transparent_background: true,
            estimated_seconds: 90,
          },
        ],
      },
    })
  })
  await page.route('**/api/models', async (route) => {
    await route.fulfill({ json: { data: [{ id: 'gpt-image-2' }] } })
  })
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ json: { id: 1, username: 'admin', role: 'admin', is_active: true, created_at: '2026-05-17T00:00:00Z' } })
  })
  await page.route('**/api/admin/users', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        json: [
          {
            id: 1,
            username: 'admin',
            role: 'admin',
            is_active: true,
            created_at: '2026-05-17T00:00:00Z',
            updated_at: '2026-05-17T00:00:00Z',
            last_login_at: '2026-05-17T01:00:00Z',
          },
        ],
      })
      return
    }
    await route.fulfill({ status: 201, json: {} })
  })
  await page.route('**/api/prompt-templates', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/images/history**', async (route) => {
    await route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 24 } })
  })
  await page.route('**/api/images/generation-jobs?**', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 42,
          status: 'failed',
          progress_message: '生成失败',
          error_message: '测试额度不足',
          error_code: 'insufficient_quota',
          error_category: 'billing',
          attempt_count: 2,
          max_attempts: 2,
          requested_model: 'gpt-image-2',
          effective_model: 'gpt-image-2',
          endpoint_type: 'responses',
          created_at: '2026-05-17T00:00:00Z',
          completed_at: '2026-05-17T00:00:05Z',
        },
      ],
    })
  })
  await page.route('**/api/images/generation-jobs/42', async (route) => {
    await route.fulfill({ status: 204, body: '' })
  })
  await page.route('**/api/images/generation-jobs/42/retry', async (route) => {
    await route.fulfill({
      status: 202,
      json: {
        id: 43,
        status: 'queued',
        progress_message: '已加入生成队列',
        attempt_count: 0,
        max_attempts: 2,
        requested_model: 'gpt-image-2',
        created_at: '2026-05-17T00:01:00Z',
      },
    })
  })
}

test('top navigation stays usable while scrolling', async ({ page }) => {
  await mockSignedInApp(page)
  await page.goto('/')

  await expect(page.getByRole('navigation', { name: '工作台导航' }).getByRole('button', { name: /生成/ })).toBeVisible()
  await expect(page.getByRole('navigation', { name: '工作台导航' }).getByRole('button', { name: /历史/ })).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await expect(page.getByRole('navigation', { name: '工作台导航' }).getByRole('button', { name: /生成/ })).toBeVisible()
})

test('recent generation task exposes guarded delete', async ({ page }) => {
  await mockSignedInApp(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '最近生成任务' })).toBeVisible()
  await page.getByRole('button', { name: '删除记录' }).click()
  await expect(page.getByRole('dialog', { name: '确认删除生成任务' })).toBeVisible()
  await expect(page.getByText('确认删除后会从当前列表隐藏')).toBeVisible()
  await page.getByRole('button', { name: '确认删除' }).click()
  await expect(page.getByText('生成任务记录已删除。')).toBeVisible()
})

test('history filters expose advanced controls without crowding the default row', async ({ page }) => {
  await mockSignedInApp(page)
  await page.goto('/')

  await page.getByRole('navigation', { name: '工作台导航' }).getByRole('button', { name: /历史/ }).click()
  await expect(page.getByPlaceholder('搜索提示词')).toBeVisible()
  await expect(page.getByPlaceholder('标签')).toBeHidden()
  await page.getByRole('button', { name: '更多筛选' }).click()
  await expect(page.getByPlaceholder('标签')).toBeVisible()
  await page.getByPlaceholder('标签').fill('产品图')
  await expect(page.getByRole('button', { name: /标签: 产品图/ })).toBeVisible()
})

test('admin panel shows users and system status', async ({ page }) => {
  await mockSignedInApp(page)
  await page.goto('/')

  await page.getByRole('navigation', { name: '工作台导航' }).getByRole('button', { name: /管理/ }).click()
  const adminPanel = page.getByLabel('用户管理', { exact: true })
  await expect(page.getByRole('heading', { name: '用户管理' })).toBeVisible()
  await expect(page.getByLabel('系统状态')).toContainText('默认模型')
  await expect(adminPanel.getByText('admin', { exact: true })).toBeVisible()
})

test('task detail and bulk actions are available', async ({ page }) => {
  await mockSignedInApp(page)
  await page.goto('/')

  await page.getByRole('button', { name: '详情' }).click()
  const detailDialog = page.getByRole('dialog', { name: /#42/ })
  await expect(detailDialog).toBeVisible()
  await expect(detailDialog.getByText('insufficient_quota')).toBeVisible()
  await page.getByRole('button', { name: '关闭' }).click()

  await page.getByRole('button', { name: '批量操作' }).click()
  await page.getByLabel('选择').check()
  await page.getByRole('button', { name: '批量重试' }).click()
  await expect(page.getByText('已重新提交生成任务。')).toBeVisible()
})

test('visual regression snapshots for key states', async ({ page }, testInfo) => {
  await mockSignedInApp(page)
  await page.goto('/')

  await expect(page).toHaveScreenshot(`signed-in-${testInfo.project.name}.png`, { fullPage: false })
  await page.getByRole('button', { name: '详情' }).click()
  await expect(page).toHaveScreenshot(`task-detail-${testInfo.project.name}.png`, { fullPage: false })
  await page.getByRole('button', { name: '关闭' }).click()
  await page.getByRole('navigation', { name: '工作台导航' }).getByRole('button', { name: /历史/ }).click()
  await page.getByRole('button', { name: '更多筛选' }).click()
  await expect(page).toHaveScreenshot(`history-filters-${testInfo.project.name}.png`, { fullPage: false })
})
