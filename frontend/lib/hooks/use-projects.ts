"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"

export function useProjects() {
  return useQuery({ queryKey: ["projects"], queryFn: api.projects.list, staleTime: 30000 })
}

export function useProject(id: string) {
  return useQuery({ queryKey: ["projects", id], queryFn: () => api.projects.get(id), enabled: !!id })
}

export function useProjectConfig(id: string) {
  return useQuery({ queryKey: ["projects", id, "config"], queryFn: () => api.projects.config(id), enabled: !!id })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: api.projects.create, onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }) })
}

export function useDeleteProject() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: api.projects.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }) })
}

export function useUpdateProjectConfig(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => api.projects.updateConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects", id, "config"] })
  })
}

export function useChapters(projectId: string) {
  return useQuery({ queryKey: ["chapters", projectId], queryFn: () => api.chapters.list(projectId), enabled: !!projectId })
}

export function useChapter(projectId: string, num: number) {
  return useQuery({
    queryKey: ["chapters", projectId, num],
    queryFn: () => api.chapters.get(projectId, num),
    enabled: !!projectId && num > 0
  })
}
