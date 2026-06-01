import { api } from "../api-client"

export interface HealthStatus {
  online: boolean
  checkedAt: string
}

export const healthService = {
  checkBackendHealth: async (): Promise<HealthStatus> => {
    try {
      const res = await api.health.check()
      return {
        online: !!res,
        checkedAt: new Date().toLocaleTimeString("zh-CN", { hour12: false })
      }
    } catch {
      return {
        online: false,
        checkedAt: new Date().toLocaleTimeString("zh-CN", { hour12: false })
      }
    }
  }
}
