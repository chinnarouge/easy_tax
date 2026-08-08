const API_BASE = 'http://localhost:8000/api/v1';

let authToken: string | null = null;

export function setToken(token: string | null) {
  authToken = token;
}

export function getToken(): string | null {
  return authToken;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || res.statusText);
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json();
  }
  return res.blob() as unknown as T;
}

export const api = {
  register: (email: string, password: string, fullName: string) =>
    request<{ user_id: string; email: string; token: string }>('POST', '/auth/register', {
      email,
      password,
      full_name: fullName,
    }),

  login: (email: string, password: string) =>
    request<{ user_id: string; email: string; token: string }>('POST', '/auth/login', { email, password }),

  me: () => request<{ user_id: string; email: string; full_name: string }>('GET', '/auth/me'),

  submitOnboarding: (profile: Record<string, unknown>) =>
    request<{ required_anlagen: string[]; suggested_next_steps: string[] }>('POST', '/onboarding/profile', profile),

  createTaxReturn: (taxYear: number, profile: Record<string, unknown>) =>
    request<{
      tax_return_id: string;
      tax_year: number;
      status: string;
      required_anlagen: string[];
      completion: number;
    }>('POST', '/tax-returns', { tax_year: taxYear, profile }),

  listTaxReturns: () =>
    request<{ tax_returns: Array<{ tax_return_id: string; tax_year: number; status: string; completion: number }> }>(
      'GET',
      '/tax-returns',
    ),

  getTaxReturn: (id: string) =>
    request<{
      tax_return_id: string;
      tax_year: number;
      status: string;
      required_anlagen: string[];
      sections: Record<string, Record<string, unknown>>;
      completion: number;
    }>('GET', `/tax-returns/${id}`),

  updateSection: (id: string, section: string, values: Record<string, unknown>) =>
    request<{ tax_return_id: string; section: string; completion: number; sections: Record<string, unknown> }>(
      'PATCH',
      `/tax-returns/${id}/section/${section}`,
      { values },
    ),

  getDeductionSuggestions: (id: string) =>
    request<{
      tax_return_id: string;
      suggestions: Array<{
        title: string;
        amount_eur: number | null;
        form: string;
        line: string;
        reason: string;
        field_id: string;
      }>;
    }>('GET', `/tax-returns/${id}/deduction-suggestions`),

  getElsterFields: () => request<Array<Record<string, string>>>('GET', '/elster/fields'),

  getElsterField: (fieldId: string) => request<Record<string, string>>('GET', `/elster/field/${fieldId}`),

  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const headers: Record<string, string> = {};
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail || res.statusText);
    }
    return res.json() as Promise<{
      document_id: string;
      file_name: string;
      content_type: string;
      classification: string;
      extracted_fields: Record<string, unknown>;
      confidence: number;
      created_at: string;
    }>;
  },

  listDocuments: () =>
    request<{
      documents: Array<{
        document_id: string;
        file_name: string;
        content_type: string;
        classification: string;
        extracted_fields: Record<string, unknown>;
        confidence: number;
        created_at: string;
      }>;
    }>('GET', '/documents'),

  estimateTax: (taxableIncome: number, filingType: string, churchTaxRate: number) =>
    request<{
      taxable_income: number;
      filing_type: string;
      income_tax: number;
      solidarity_surcharge: number;
      church_tax: number;
      total_tax: number;
      effective_rate: number;
      tax_year: number;
    }>('POST', '/calculator/estimate', {
      taxable_income: taxableIncome,
      filing_type: filingType,
      church_tax_rate: churchTaxRate,
    }),

  exportCsv: (id: string) => `${API_BASE}/tax-returns/${id}/export/csv`,
  exportPdfUrl: (id: string) => `${API_BASE}/tax-returns/${id}/export/pdf`,

  getLlmProviders: () =>
    request<{
      providers: Record<
        string,
        { name: string; models: string[]; default_model: string }
      >;
    }>('GET', '/llm/providers'),

  saveLlmSettings: (provider: string, apiKey: string, modelName: string) =>
    request<{ provider: string; model_name: string; active: boolean; key_preview: string }>(
      'POST',
      '/llm/settings',
      { provider, api_key: apiKey, model_name: modelName },
    ),

  getLlmSettings: () =>
    request<{ configured: boolean; provider?: string; model_name?: string; active?: boolean; key_preview?: string }>(
      'GET',
      '/llm/settings',
    ),

  deleteLlmSettings: () => request<{ deleted: boolean }>('DELETE', '/llm/settings'),

  getExpenseCategories: () =>
    request<{
      categories: Record<
        string,
        { label_de: string; label_en: string; form: string; line: string; hint: string }
      >;
    }>('GET', '/expense-categories'),

  addExpense: (taxReturnId: string, expense: { category: string; description: string; amount_eur: number; date: string; receipt_document_id?: string }) =>
    request<{
      expense_id: string;
      category: string;
      category_label: string;
      description: string;
      amount_eur: number;
      date: string;
      form: string;
      line: string;
      receipt_document_id: string | null;
    }>('POST', `/tax-returns/${taxReturnId}/expenses`, expense),

  listExpenses: (taxReturnId: string) =>
    request<{
      expenses: Array<{
        expense_id: string;
        category: string;
        category_label: string;
        description: string;
        amount_eur: number;
        date: string;
        form: string;
        line: string;
        receipt_document_id: string | null;
      }>;
      totals_by_category: Record<string, number>;
      grand_total: number;
    }>('GET', `/tax-returns/${taxReturnId}/expenses`),

  deleteExpense: (taxReturnId: string, expenseId: string) =>
    request<{ deleted: boolean }>('DELETE', `/tax-returns/${taxReturnId}/expenses/${expenseId}`),
};
