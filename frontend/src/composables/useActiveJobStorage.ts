const ACTIVE_JOB_STORAGE_KEY = 'image-api-site-active-job-id'

export function useActiveJobStorage() {
  function persistActiveJob(jobId: number): void {
    globalThis.localStorage?.setItem(ACTIVE_JOB_STORAGE_KEY, String(jobId))
  }

  function getPersistedActiveJob(): number | null {
    const value = globalThis.localStorage?.getItem(ACTIVE_JOB_STORAGE_KEY)
    const jobId = value ? Number.parseInt(value, 10) : NaN
    return Number.isFinite(jobId) ? jobId : null
  }

  function clearPersistedActiveJob(): void {
    globalThis.localStorage?.removeItem(ACTIVE_JOB_STORAGE_KEY)
  }

  return {
    persistActiveJob,
    getPersistedActiveJob,
    clearPersistedActiveJob,
  }
}
