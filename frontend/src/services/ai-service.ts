import { api } from "@/lib/api";

export type AITaskValue = "transcription" | "extraction" | "summarization" | "chat" | "embedding";

export interface AIProviderSpec {
  slug: string;
  display_name: string;
  default_base_url: string;
  capabilities: string[];
}

export interface AIModelRow {
  id: number;
  provider: string;
  model_id: string;
  display_name: string;
  capabilities: string[];
  context_window: number;
  input_price_per_million: string;
  output_price_per_million: string;
  active: boolean;
}

export interface AIProviderConfigRow {
  id: number;
  provider: string;
  display_name: string;
  base_url: string;
  extra_config: Record<string, unknown>;
  active: boolean;
  api_key_masked: string;
  created_at: string;
  updated_at: string;
}

export interface AITaskBindingRow {
  id: number;
  task: AITaskValue;
  provider: string;
  model_id: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateProviderConfigInput {
  provider: string;
  display_name?: string;
  base_url?: string;
  extra_config?: Record<string, unknown>;
  api_key?: string;
  active?: boolean;
}

export interface CreateTaskBindingInput {
  task: AITaskValue;
  provider: string;
  model_id: string;
  active?: boolean;
}

function unwrap<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : data.results;
}

export const aiService = {
  async listProviders() {
    const response = await api.get<AIProviderSpec[]>("/ai/providers/");
    return response.data;
  },

  async listModels(params: { provider?: string; capability?: string } = {}) {
    const response = await api.get<AIModelRow[] | { results: AIModelRow[] }>("/ai/models/", {
      params,
    });
    return unwrap(response.data);
  },

  async listProviderConfigs() {
    const response = await api.get<AIProviderConfigRow[] | { results: AIProviderConfigRow[] }>(
      "/ai/provider-configs/"
    );
    return unwrap(response.data);
  },

  async createProviderConfig(payload: CreateProviderConfigInput) {
    const response = await api.post<AIProviderConfigRow>("/ai/provider-configs/", payload);
    return response.data;
  },

  async updateProviderConfig(id: number, payload: Partial<CreateProviderConfigInput>) {
    const response = await api.patch<AIProviderConfigRow>(`/ai/provider-configs/${id}/`, payload);
    return response.data;
  },

  async deleteProviderConfig(id: number) {
    await api.delete(`/ai/provider-configs/${id}/`);
  },

  async listTaskBindings() {
    const response = await api.get<AITaskBindingRow[] | { results: AITaskBindingRow[] }>(
      "/ai/task-bindings/"
    );
    return unwrap(response.data);
  },

  async createTaskBinding(payload: CreateTaskBindingInput) {
    const response = await api.post<AITaskBindingRow>("/ai/task-bindings/", payload);
    return response.data;
  },

  async updateTaskBinding(id: number, payload: Partial<CreateTaskBindingInput>) {
    const response = await api.patch<AITaskBindingRow>(`/ai/task-bindings/${id}/`, payload);
    return response.data;
  },

  async deleteTaskBinding(id: number) {
    await api.delete(`/ai/task-bindings/${id}/`);
  },
};
